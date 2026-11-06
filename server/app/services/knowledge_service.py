import hashlib
import io
import json
import os
import re
import uuid
import xml.etree.ElementTree as ET
import zipfile
from datetime import datetime, timedelta
from typing import Any, Dict, List, Optional, Tuple

from sqlalchemy.orm import Session

from app.models.adaptive_learning import KnowledgeChunk, KnowledgeDocument
from app.services.memory_service import (
    compute_semantic_embedding,
    hybrid_text_similarity,
    normalize_text,
)


def extract_text_from_docx_bytes(raw_bytes: bytes) -> str:
    """
    Extracts text from a .docx file using Python's standard library zipfile + ElementTree
    by parsing word/document.xml paragraphs.
    """
    try:
        with zipfile.ZipFile(io.BytesIO(raw_bytes)) as zf:
            if "word/document.xml" not in zf.namelist():
                return ""
            xml_bytes = zf.read("word/document.xml")
            root = ET.fromstring(xml_bytes)
            paragraphs = []
            for elem in root.iter():
                if elem.tag.endswith("}p") or elem.tag == "p":
                    texts = [
                        t.text
                        for t in elem.iter()
                        if (t.tag.endswith("}t") or t.tag == "t") and t.text
                    ]
                    if texts:
                        paragraphs.append("".join(texts).strip())
            return "\n\n".join(p for p in paragraphs if p)
    except Exception as e:
        raise ValueError(f"Failed to parse DOCX content: {e}")


def extract_text_from_pdf_bytes(raw_bytes: bytes) -> str:
    """
    Extracts text from PDF bytes using pypdf/PyPDF2 if installed, or falls back to
    standard PDF text stream extraction (BT...ET / parenthesized text objects & FlateDecode streams).
    """
    # 1. Try pypdf / PyPDF2 if available
    for mod_name in ("pypdf", "PyPDF2"):
        try:
            mod = __import__(mod_name)
            reader = mod.PdfReader(io.BytesIO(raw_bytes))
            pages = [page.extract_text() or "" for page in reader.pages]
            joined = "\n\n".join(p.strip() for p in pages if p.strip())
            if joined:
                return joined
        except Exception:
            pass

    # 2. Built-in stream & PDF text object parser (supports uncompressed and zlib FlateDecode streams)
    import zlib

    extracted_parts: List[str] = []

    def _parse_pdf_text_tokens(text_block: str):
        # Extract strings inside (...) followed by Tj or inside [...] TJ
        for match in re.finditer(r"\(([^()\\]*(?:\\.[^()\\]*)*)\)", text_block):
            token = match.group(1)
            token = (
                token.replace(r"\n", "\n")
                .replace(r"\r", "\r")
                .replace(r"\t", " ")
                .replace(r"\(", "(")
                .replace(r"\)", ")")
                .replace(r"\\", "\\")
            )
            if token.strip():
                extracted_parts.append(token.strip())

    raw_latin = raw_bytes.decode("latin-1", errors="ignore")
    # Decompress streams if present
    for stream_match in re.finditer(rb"stream[\r\n]+(.*?)[\r\n]+endstream", raw_bytes, re.DOTALL):
        stream_data = stream_match.group(1)
        try:
            decompressed = zlib.decompress(stream_data).decode("utf-8", errors="ignore")
            _parse_pdf_text_tokens(decompressed)
        except Exception:
            pass

    if not extracted_parts:
        _parse_pdf_text_tokens(raw_latin)

    if extracted_parts:
        return " ".join(extracted_parts)

    # 3. Fallback: UTF-8 printable strings if plain-text wrapped
    utf8_fallback = raw_bytes.decode("utf-8", errors="ignore")
    clean_lines = [line.strip() for line in utf8_fallback.splitlines() if len(line.strip()) > 3 and not line.strip().startswith("%PDF")]
    return "\n".join(clean_lines)


def extract_text_from_file(filename: str, raw_bytes: bytes) -> Tuple[str, str]:
    """
    Determines file type (TXT, MD, JSON, DOCX, PDF) and extracts clean UTF-8 text.
    Returns (file_type, extracted_text).
    """
    ext = os.path.splitext(filename or "")[1].lower()
    if ext == ".docx":
        return "DOCX", extract_text_from_docx_bytes(raw_bytes)
    if ext == ".pdf":
        return "PDF", extract_text_from_pdf_bytes(raw_bytes)
    if ext == ".json":
        text = raw_bytes.decode("utf-8", errors="replace")
        try:
            parsed = json.loads(text)
            return "JSON", json.dumps(parsed, ensure_ascii=False, indent=2)
        except Exception:
            return "JSON", text
    if ext in (".md", ".markdown"):
        return "MD", raw_bytes.decode("utf-8", errors="replace")
    return "TXT", raw_bytes.decode("utf-8", errors="replace")


def chunk_document_text(text: str, chunk_size: int = 600, overlap: int = 100) -> List[Dict[str, Any]]:
    """
    Splits document text into structured, overlapping semantic chunks while preserving
    paragraph boundaries and headings.
    """
    clean = (text or "").strip()
    if not clean:
        return []

    paragraphs = [p.strip() for p in re.split(r"\n\s*\n", clean) if p.strip()]
    chunks: List[Dict[str, Any]] = []
    current_buf = ""
    current_heading = "Section 1"
    chunk_idx = 0

    for para in paragraphs:
        # Detect Markdown or numbered heading
        first_line = para.splitlines()[0].strip()
        if first_line.startswith("#") or (len(first_line) < 80 and first_line.endswith(":")):
            current_heading = first_line.lstrip("#").strip()

        if len(current_buf) + len(para) + 2 <= chunk_size:
            current_buf = f"{current_buf}\n\n{para}".strip() if current_buf else para
        else:
            if current_buf:
                words = re.findall(r"[\w\u0600-\u06FF]{3,}", normalize_text(current_buf))
                chunks.append({
                    "chunk_index": chunk_idx,
                    "heading": current_heading,
                    "content": current_buf,
                    "keywords": list(dict.fromkeys(words[:15])),
                })
                chunk_idx += 1
                overlap_tail = current_buf[-overlap:] if overlap > 0 and len(current_buf) > overlap else ""
                current_buf = f"{overlap_tail}\n{para}".strip()
            else:
                # Single paragraph larger than chunk_size
                for start in range(0, len(para), max(100, chunk_size - overlap)):
                    piece = para[start : start + chunk_size].strip()
                    if piece:
                        words = re.findall(r"[\w\u0600-\u06FF]{3,}", normalize_text(piece))
                        chunks.append({
                            "chunk_index": chunk_idx,
                            "heading": current_heading,
                            "content": piece,
                            "keywords": list(dict.fromkeys(words[:15])),
                        })
                        chunk_idx += 1
                current_buf = ""

    if current_buf:
        words = re.findall(r"[\w\u0600-\u06FF]{3,}", normalize_text(current_buf))
        chunks.append({
            "chunk_index": chunk_idx,
            "heading": current_heading,
            "content": current_buf,
            "keywords": list(dict.fromkeys(words[:15])),
        })

    return chunks


def detect_cross_source_conflicts(db: Session, new_text: str, new_source: str) -> List[Dict[str, Any]]:
    """
    Compares statements in `new_text` against existing chunks from other sources to detect
    contradictory numeric claims or explicit negations on the same topic.
    """
    conflicts: List[Dict[str, Any]] = []
    existing_chunks = db.query(KnowledgeChunk).order_by(KnowledgeChunk.id.desc()).limit(150).all()
    if not existing_chunks:
        return conflicts

    new_vec = compute_semantic_embedding(new_text)
    new_numbers = set(re.findall(r"\b\d+(?:\.\d+)?\b", new_text))
    negation_tokens = {"لا", "ليس", "ليست", "غير", "ممنوع", "خطأ", "not", "never", "false", "disabled", "offline"}
    new_words = set(re.findall(r"[\w\u0600-\u06FF]+", normalize_text(new_text)))
    new_has_neg = bool(new_words & negation_tokens)

    for ch in existing_chunks:
        try:
            ch_vec = json.loads(ch.embedding_json) if ch.embedding_json else None
        except Exception:
            ch_vec = None
        sim = hybrid_text_similarity(new_text, ch.content, new_vec, ch_vec)
        if sim < 0.42:
            continue

        ch_numbers = set(re.findall(r"\b\d+(?:\.\d+)?\b", ch.content))
        ch_words = set(re.findall(r"[\w\u0600-\u06FF]+", normalize_text(ch.content)))
        ch_has_neg = bool(ch_words & negation_tokens)

        # Conflict condition 1: High topic similarity but conflicting numbers
        if new_numbers and ch_numbers and new_numbers != ch_numbers:
            conflicts.append({
                "conflict_type": "NUMERIC_DISCREPANCY",
                "existing_doc_uid": ch.doc_uid,
                "existing_chunk_uid": ch.chunk_uid,
                "similarity": sim,
                "new_numbers": sorted(new_numbers),
                "existing_numbers": sorted(ch_numbers),
                "existing_excerpt": ch.content[:180],
                "new_source": new_source,
            })
        # Conflict condition 2: High topic similarity (>= 0.55) with opposite polarity/negation
        elif sim >= 0.55 and (new_has_neg != ch_has_neg):
            conflicts.append({
                "conflict_type": "POLARITY_CONTRADICTION",
                "existing_doc_uid": ch.doc_uid,
                "existing_chunk_uid": ch.chunk_uid,
                "similarity": sim,
                "existing_excerpt": ch.content[:180],
                "new_source": new_source,
            })

    return conflicts[:10]


def ingest_document(
    db: Session,
    filename: str,
    raw_bytes: bytes,
    title: Optional[str] = None,
    source_reference: str = "uploaded_file",
    trust_level: float = 0.9,
    ttl_days: Optional[int] = None,
    chunk_size: int = 600,
) -> Dict[str, Any]:
    """
    Ingests a document (TXT, PDF, DOCX, MD, JSON), extracts text, detects conflicts,
    chunks the content, computes semantic embeddings, and persists source metadata.
    """
    file_type, extracted_text = extract_text_from_file(filename, raw_bytes)
    clean_text = (extracted_text or "").strip()
    if not clean_text:
        raise ValueError(f"No readable text could be extracted from '{filename}'.")

    c_hash = hashlib.sha256(clean_text.encode("utf-8")).hexdigest()
    existing_doc = db.query(KnowledgeDocument).filter(KnowledgeDocument.content_hash == c_hash).first()
    if existing_doc:
        doc_dict = serialize_document(existing_doc)
        return {
            "success": True,
            "deduplicated": True,
            "document": doc_dict,
            "conflicts_detected": doc_dict["conflicts"],
            "message": "Document with identical content is already indexed.",
        }

    conflicts = detect_cross_source_conflicts(db, clean_text[:2000], source_reference or filename)
    chunks_data = chunk_document_text(clean_text, chunk_size=chunk_size)

    doc_uid = f"doc_{uuid.uuid4().hex[:12]}"
    expires_at = datetime.utcnow() + timedelta(days=ttl_days) if ttl_days else None

    doc_record = KnowledgeDocument(
        doc_uid=doc_uid,
        title=(title or filename or "Untitled Document").strip(),
        filename=filename,
        file_type=file_type,
        source_reference=source_reference or filename,
        trust_level=float(trust_level),
        total_chunks=len(chunks_data),
        total_chars=len(clean_text),
        content_hash=c_hash,
        conflicts_json=json.dumps(conflicts, ensure_ascii=False),
        expires_at=expires_at,
        is_expired=False,
    )
    db.add(doc_record)

    created_chunks: List[KnowledgeChunk] = []
    for ch in chunks_data:
        emb = compute_semantic_embedding(f"{doc_record.title} {ch['heading']} {ch['content']}")
        chunk_rec = KnowledgeChunk(
            chunk_uid=f"chk_{uuid.uuid4().hex[:12]}",
            doc_uid=doc_uid,
            chunk_index=ch["chunk_index"],
            heading=ch["heading"],
            content=ch["content"],
            embedding_json=json.dumps(emb),
            keywords_json=json.dumps(ch["keywords"], ensure_ascii=False),
        )
        db.add(chunk_rec)
        created_chunks.append(chunk_rec)

    db.commit()
    db.refresh(doc_record)

    return {
        "success": True,
        "deduplicated": False,
        "document": serialize_document(doc_record),
        "chunks_created": len(created_chunks),
        "conflicts_detected": conflicts,
        "message": f"Successfully ingested '{doc_record.title}' ({file_type}) into {len(created_chunks)} indexed knowledge chunks.",
    }


def search_knowledge_chunks(
    db: Session,
    query: str,
    top_k: int = 5,
    include_expired: bool = False,
    min_similarity: float = 0.15,
) -> List[Dict[str, Any]]:
    """
    Searches indexed knowledge chunks and returns ranked passages with full source citations
    and freshness status.
    """
    if not query or not query.strip():
        return []

    now = datetime.utcnow()
    docs = {d.doc_uid: d for d in db.query(KnowledgeDocument).all()}
    chunks = db.query(KnowledgeChunk).all()

    query_vec = compute_semantic_embedding(query)
    scored: List[Tuple[float, KnowledgeChunk, Optional[KnowledgeDocument]]] = []

    for ch in chunks:
        doc = docs.get(ch.doc_uid)
        if doc:
            is_exp = bool(doc.is_expired or (doc.expires_at and doc.expires_at < now))
            if is_exp and not include_expired:
                continue

        try:
            ch_vec = json.loads(ch.embedding_json) if ch.embedding_json else None
        except Exception:
            ch_vec = None

        sim = hybrid_text_similarity(query, f"{ch.heading} {ch.content}", query_vec, ch_vec)
        if normalize_text(query) in normalize_text(ch.content):
            sim = max(sim, 0.88)
        if sim >= min_similarity:
            scored.append((sim, ch, doc))

    scored.sort(key=lambda x: x[0], reverse=True)
    results = []
    for sim, ch, doc in scored[:top_k]:
        is_exp = bool(doc and (doc.is_expired or (doc.expires_at and doc.expires_at < now)))
        results.append({
            "chunk_uid": ch.chunk_uid,
            "doc_uid": ch.doc_uid,
            "document_title": doc.title if doc else "Unknown Document",
            "filename": doc.filename if doc else "",
            "file_type": doc.file_type if doc else "TXT",
            "source_reference": doc.source_reference if doc else "unknown",
            "trust_level": doc.trust_level if doc else 0.5,
            "chunk_index": ch.chunk_index,
            "heading": ch.heading,
            "content": ch.content,
            "similarity": round(sim, 4),
            "is_expired": is_exp,
            "citation": f"[Source: {doc.title if doc else ch.doc_uid} ({doc.file_type if doc else 'DOC'}) | Section: {ch.heading} | Chunk #{ch.chunk_index + 1}]",
        })
    return results


def serialize_document(doc: KnowledgeDocument) -> Dict[str, Any]:
    now = datetime.utcnow()
    is_exp = bool(doc.is_expired or (doc.expires_at and doc.expires_at < now))
    try:
        conflicts = json.loads(doc.conflicts_json or "[]")
    except Exception:
        conflicts = []
    return {
        "id": doc.id,
        "doc_uid": doc.doc_uid,
        "title": doc.title,
        "filename": doc.filename,
        "file_type": doc.file_type,
        "source_reference": doc.source_reference,
        "trust_level": doc.trust_level,
        "total_chunks": doc.total_chunks,
        "total_chars": doc.total_chars,
        "conflicts": conflicts,
        "conflicts_count": len(conflicts),
        "is_expired": is_exp,
        "expires_at": doc.expires_at.isoformat() if doc.expires_at else None,
        "created_at": doc.created_at.isoformat() if doc.created_at else None,
    }
