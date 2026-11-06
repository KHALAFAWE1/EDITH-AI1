import hashlib
import json
import re
import uuid
from datetime import datetime, timedelta
from typing import Any, Dict, List, Optional, Tuple

import numpy as np
from sqlalchemy.orm import Session

from app.models.adaptive_learning import MemoryRecord

EMBEDDING_DIM = 128

STOP_WORDS = {
    "what", "is", "the", "a", "an", "in", "on", "of", "to", "for", "stored", "regarding",
    "with", "and", "or", "by", "from", "at", "as", "it",
    "ما", "هو", "هي", "في", "من", "عن", "على", "إلى", "حول", "لدى", "ماذا", "هذا", "هذه", "مع"
}

SIDE_VARIANTS = {
    "port": {"starboard", "right"},
    "starboard": {"port", "left"},
    "left": {"right", "starboard"},
    "right": {"left", "port"},
    "dorsal": {"ventral"},
    "ventral": {"dorsal"},
    "aft": {"bow", "forward"},
    "bow": {"aft"},
    "forward": {"aft"},
    "primary": {"secondary", "tertiary"},
    "secondary": {"primary", "tertiary"},
    "tertiary": {"primary", "secondary"},
}

SUBSYSTEM_ALIASES = {
    "propulsion": ["propulsion", "thruster", "thrusters", "engine", "rocket", "thrust"],
    "thermal": ["thermal", "coolant", "cooling", "temperature", "heat"],
    "storage": ["storage", "cryo", "cryogenic", "tank", "containment", "bay"],
    "telecom": ["telecom", "comms", "communication", "communications", "dish", "antenna", "baud", "optical"],
    "guidance": ["guidance", "attitude", "gyroscope", "gyro", "star-tracker", "tracker", "navigation", "sensor", "optics"],
    "power": ["power", "solar", "photovoltaic", "battery", "reactor", "kilowatt", "kilowatts", "kw"]
}

KNOWN_SUBSYSTEMS = list(SUBSYSTEM_ALIASES.keys())


def extract_structured_metadata(
    text: str,
    subject: str = "",
    explicit_metadata: Optional[Dict[str, Any]] = None,
    is_verified_fact: bool = False,
    source_reference: str = ""
) -> Dict[str, Any]:
    """
    Extracts or enriches backward-compatible structured attributes from text and subject:
    subsystem, component_side, models, specifications, units, provenance.
    """
    norm = normalize_text(f"{subject} {text}")
    tokens = set(re.findall(r"[\w-]+", norm))

    # 1. Component Side / Sibling Variant
    found_side = None
    for side in SIDE_VARIANTS:
        if side in tokens or f"{side}-side" in norm or f"{side}side" in norm:
            found_side = side
            break

    # 2. Subsystem
    subsystem = None
    for sub, aliases in SUBSYSTEM_ALIASES.items():
        if sub in tokens or any(alias in tokens for alias in aliases):
            subsystem = sub
            break

    # 3. Model codes (e.g. LG-400, ST-900)
    raw_models = re.findall(r"\b[A-Za-z]{1,5}-\d{2,5}[A-Za-z]?\b", f"{subject} {text}")
    models = list(dict.fromkeys([m.upper() for m in raw_models]))

    # 4. Numeric specifications and units
    num_matches = re.findall(r"\b(\d+(?:\.\d+)?)\s*([a-zA-Z%]+)?\b", f"{subject} {text}")
    specs = []
    units = []
    for val, unit in num_matches:
        specs.append(val)
        if unit and len(unit) <= 8 and unit.lower() not in STOP_WORDS:
            units.append(unit.lower())

    struct_meta = {
        "subject": subject or (explicit_metadata.get("subject") if explicit_metadata else None),
        "subsystem": subsystem or (explicit_metadata.get("subsystem") if explicit_metadata else None),
        "component": (explicit_metadata.get("component") if explicit_metadata else None) or subject or None,
        "component_side": found_side or (explicit_metadata.get("component_side") if explicit_metadata else None),
        "models": models or (explicit_metadata.get("models", []) if explicit_metadata else []),
        "specifications": specs[:10],
        "units": list(dict.fromkeys(units))[:10],
        "verification_status": "VERIFIED" if is_verified_fact else "UNVERIFIED",
        "source_reference": source_reference or (explicit_metadata.get("source_reference") if explicit_metadata else "")
    }

    if explicit_metadata:
        for k, v in explicit_metadata.items():
            if k not in struct_meta or not struct_meta[k]:
                struct_meta[k] = v

    return struct_meta

# Sensitive patterns that must not be stored in memory without explicit consent
# or sent to external cloud providers unredacted.
SENSITIVE_PATTERNS = [
    (r"AIzaSy[A-Za-z0-9_-]{25,}", "GOOGLE_API_KEY"),
    (r"sk-[A-Za-z0-9]{20,}", "OPENAI_API_KEY"),
    (r"(?i)(password|passwd|secret_key|private_key|api_key|كلمة المرور|كلمه السر|الباسورد)\s*[:=]\s*\S+", "CREDENTIAL_SECRET"),
    (r"\b(?:\d[ -]*?){13,16}\b", "PAYMENT_CARD_NUMBER"),
    (r"-----BEGIN (?:RSA |EC |OPENSSH )?PRIVATE KEY-----", "PRIVATE_KEY_BLOCK"),
]


def detect_sensitive_data(text: str) -> Tuple[bool, List[str], str]:
    """
    Checks if text contains sensitive credentials, keys, or secrets.
    Returns (contains_sensitive, matched_types, redacted_text).
    """
    if not text:
        return False, [], ""
    matched_types = []
    redacted = text
    for pattern, label in SENSITIVE_PATTERNS:
        if re.search(pattern, redacted):
            matched_types.append(label)
            redacted = re.sub(pattern, f"[REDACTED_{label}]", redacted)
    return len(matched_types) > 0, matched_types, redacted


def normalize_text(text: str) -> str:
    """Normalizes Arabic and English text for hashing, deduplication, and embedding."""
    if not text:
        return ""
    t = text.strip().lower()
    # Normalize Arabic alef/teh marbuta/yeh variations
    t = re.sub(r"[إأآا]", "ا", t)
    t = re.sub(r"ة", "ه", t)
    t = re.sub(r"ى", "ي", t)
    t = re.sub(r"[\u064B-\u065F]", "", t)  # strip diacritics
    t = re.sub(r"\s+", " ", t)
    return t


def compute_content_hash(text: str) -> str:
    return hashlib.sha256(normalize_text(text).encode("utf-8")).hexdigest()


def compute_semantic_embedding(text: str, dim: int = EMBEDDING_DIM) -> List[float]:
    """
    Computes a deterministic L2-normalized semantic vector (128-D) using
    multilingual word tokens, word bigrams, and character n-grams (3-grams & 4-grams).
    Works 100% offline with zero external dependencies beyond numpy, supporting both
    Arabic and English semantic similarity.
    """
    norm = normalize_text(text)
    if not norm:
        return [0.0] * dim

    vec = np.zeros(dim, dtype=np.float64)
    words = re.findall(r"[\w\u0600-\u06FF]+", norm)

    # 1. Word unigrams (weight 2.5 for keywords, 0.2 for stop words) and stems
    for w in words:
        is_stop = w in STOP_WORDS
        weight = 0.2 if is_stop else 2.5
        h = int(hashlib.md5(f"w:{w}".encode("utf-8")).hexdigest(), 16)
        idx = h % dim
        sign = 1.0 if ((h >> 8) & 1) == 0 else -1.0
        vec[idx] += sign * weight

        if not is_stop:
            # Arabic prefix stripping ("ال", "و", "ب", "ل") for root matching
            stem = re.sub(r"^(وال|بال|كال|فال|ال)", "", w)
            if stem and stem != w and len(stem) >= 2:
                hs = int(hashlib.md5(f"s:{stem}".encode("utf-8")).hexdigest(), 16)
                vec[hs % dim] += (1.0 if ((hs >> 8) & 1) == 0 else -1.0) * 1.8

    # 2. Word bigrams (weight 2.0)
    for i in range(len(words) - 1):
        bg = f"{words[i]}_{words[i + 1]}"
        h = int(hashlib.md5(f"bg:{bg}".encode("utf-8")).hexdigest(), 16)
        idx = h % dim
        sign = 1.0 if ((h >> 8) & 1) == 0 else -1.0
        vec[idx] += sign * 2.0

    # 3. Character 3-grams (weight 0.6)
    compact = re.sub(r"\s+", " ", norm)
    for i in range(max(0, len(compact) - 2)):
        tri = compact[i : i + 3]
        h = int(hashlib.md5(f"c3:{tri}".encode("utf-8")).hexdigest(), 16)
        idx = h % dim
        sign = 1.0 if ((h >> 8) & 1) == 0 else -1.0
        vec[idx] += sign * 0.6

    norm_val = float(np.linalg.norm(vec))
    if norm_val > 1e-9:
        vec = vec / norm_val
    return [round(float(x), 6) for x in vec]


def cosine_similarity(vec_a: List[float], vec_b: List[float]) -> float:
    if not vec_a or not vec_b or len(vec_a) != len(vec_b):
        return 0.0
    a = np.array(vec_a, dtype=np.float64)
    b = np.array(vec_b, dtype=np.float64)
    denom = float(np.linalg.norm(a) * np.linalg.norm(b))
    if denom < 1e-9:
        return 0.0
    sim = float(np.dot(a, b) / denom)
    # Also blend token overlap if available via caller, or return raw cosine in [0, 1]
    return max(0.0, min(1.0, round(sim, 4)))


def hybrid_text_similarity(query: str, candidate: str, query_vec: Optional[List[float]] = None, cand_vec: Optional[List[float]] = None) -> float:
    """
    Combines vector cosine similarity with normalized token Jaccard overlap for
    high-precision multilingual semantic retrieval.
    """
    qv = query_vec or compute_semantic_embedding(query)
    cv = cand_vec or compute_semantic_embedding(candidate)
    cos_sim = cosine_similarity(qv, cv)

    q_words = set(re.findall(r"[\w\u0600-\u06FF]{2,}", normalize_text(query)))
    c_words = set(re.findall(r"[\w\u0600-\u06FF]{2,}", normalize_text(candidate)))
    # Strip Arabic definite article for token overlap
    q_stems = {re.sub(r"^ال", "", w) for w in q_words}
    c_stems = {re.sub(r"^ال", "", w) for w in c_words}

    if q_stems and c_stems:
        inter = len(q_stems & c_stems)
        union = len(q_stems | c_stems)
        jaccard = inter / max(1, union)
        recall = inter / max(1, len(q_stems))
        lexical = 0.5 * jaccard + 0.5 * recall
        return round(min(1.0, 0.55 * cos_sim + 0.45 * lexical), 4)
    return cos_sim


def serialize_memory(
    record: MemoryRecord,
    similarity: Optional[float] = None,
    signals: Optional[List[str]] = None,
    base_similarity: Optional[float] = None
) -> Dict[str, Any]:
    try:
        concepts = json.loads(record.concepts_json or "[]")
    except Exception:
        concepts = []
    try:
        metadata = json.loads(record.metadata_json or "{}")
    except Exception:
        metadata = {}

    data = {
        "id": record.id,
        "memory_uid": record.memory_uid,
        "memory_type": record.memory_type,
        "category": record.category,
        "subject": record.subject,
        "content": record.content,
        "is_verified_fact": bool(record.is_verified_fact),
        "fact_or_inference": record.fact_or_inference or ("FACT" if record.is_verified_fact else "INFERENCE"),
        "source_type": record.source_type,
        "source_reference": record.source_reference,
        "confidence": record.confidence,
        "concepts": concepts,
        "metadata": metadata,
        "user_approved": bool(record.user_approved),
        "contains_sensitive": bool(record.contains_sensitive),
        "session_id": record.session_id,
        "created_at": record.created_at.isoformat() if record.created_at else None,
        "updated_at": record.updated_at.isoformat() if record.updated_at else None,
        "expires_at": record.expires_at.isoformat() if record.expires_at else None,
    }
    if similarity is not None:
        data["similarity"] = round(similarity, 4)
    if signals is not None:
        data["re_ranking_signals"] = signals
    if base_similarity is not None:
        data["base_similarity"] = round(base_similarity, 4)
    return data


def store_memory(
    db: Session,
    content: str,
    memory_type: str = "LONG_TERM",
    subject: str = "general",
    category: str = "general",
    is_verified_fact: bool = False,
    fact_or_inference: Optional[str] = None,
    source_type: str = "conversation",
    source_reference: str = "user_session",
    confidence: float = 0.85,
    concepts: Optional[List[Dict[str, str]]] = None,
    metadata: Optional[Dict[str, Any]] = None,
    user_approved: bool = True,
    allow_sensitive: bool = False,
    session_id: str = "default",
    ttl_hours: Optional[int] = None,
) -> Dict[str, Any]:
    """
    Stores a memory in the TARS Memory System with:
    1. Sensitive data guard (blocks storing secrets without consent)
    2. Deduplication (prevents storing identical or near-identical memories)
    3. Fact vs. Inference tagging
    4. Semantic embedding generation
    """
    clean_content = (content or "").strip()
    if not clean_content:
        raise ValueError("Memory content cannot be empty.")

    mem_type = memory_type.upper().strip()
    if mem_type not in ("SHORT_TERM", "LONG_TERM", "EPISODIC", "SEMANTIC"):
        mem_type = "LONG_TERM"

    # 1. Sensitive data check
    has_sensitive, sensitive_types, _ = detect_sensitive_data(clean_content)
    if has_sensitive and not allow_sensitive:
        return {
            "success": False,
            "blocked_sensitive": True,
            "sensitive_types": sensitive_types,
            "message": f"Blocked storing sensitive data ({', '.join(sensitive_types)}) without explicit consent (allow_sensitive=True)."
        }

    # 2. Deduplication check
    c_hash = compute_content_hash(clean_content)
    existing_exact = (
        db.query(MemoryRecord)
        .filter(MemoryRecord.content_hash == c_hash, MemoryRecord.memory_type == mem_type)
        .first()
    )
    if existing_exact:
        existing_exact.updated_at = datetime.utcnow()
        existing_exact.confidence = max(existing_exact.confidence or 0.0, confidence)
        if is_verified_fact:
            existing_exact.is_verified_fact = True
            existing_exact.fact_or_inference = "FACT"
        db.commit()
        db.refresh(existing_exact)
        return {
            "success": True,
            "deduplicated": True,
            "memory": serialize_memory(existing_exact),
            "message": "Duplicate memory detected; updated existing record timestamp and confidence."
        }

    embedding = compute_semantic_embedding(f"{subject} {clean_content}")

    # Check high semantic similarity (>= 0.95) within same memory_type and subject
    same_subject_records = (
        db.query(MemoryRecord)
        .filter(MemoryRecord.memory_type == mem_type, MemoryRecord.subject == subject)
        .all()
    )
    for rec in same_subject_records:
        try:
            rec_vec = json.loads(rec.embedding_json) if rec.embedding_json else None
        except Exception:
            rec_vec = None
        sim = hybrid_text_similarity(clean_content, rec.content, embedding, rec_vec)
        if sim >= 0.95:
            rec.updated_at = datetime.utcnow()
            db.commit()
            db.refresh(rec)
            return {
                "success": True,
                "deduplicated": True,
                "memory": serialize_memory(rec, similarity=sim),
                "message": f"Near-duplicate memory detected (similarity={sim}); merged with existing record."
            }

    foi = (fact_or_inference or ("FACT" if is_verified_fact else "INFERENCE")).upper()
    if foi not in ("FACT", "INFERENCE"):
        foi = "FACT" if is_verified_fact else "INFERENCE"

    expires_at = None
    if ttl_hours is not None:
        expires_at = datetime.utcnow() + timedelta(hours=ttl_hours)
    elif mem_type == "SHORT_TERM":
        expires_at = datetime.utcnow() + timedelta(hours=24)

    is_fact_flag = bool(user_approved and (is_verified_fact or (foi == "FACT" and user_approved)))

    enriched_meta = dict(metadata or {})
    if "structured_attributes" not in enriched_meta:
        enriched_meta["structured_attributes"] = extract_structured_metadata(
            text=clean_content,
            subject=subject,
            explicit_metadata=enriched_meta,
            is_verified_fact=is_fact_flag,
            source_reference=source_reference,
        )

    record = MemoryRecord(
        memory_uid=f"mem_{uuid.uuid4().hex[:12]}",
        memory_type=mem_type,
        category=category,
        subject=subject,
        content=clean_content,
        content_hash=c_hash,
        is_verified_fact=is_fact_flag,
        fact_or_inference=foi,
        source_type=source_type,
        source_reference=source_reference,
        confidence=float(confidence),
        embedding_json=json.dumps(embedding),
        concepts_json=json.dumps(concepts or [], ensure_ascii=False),
        metadata_json=json.dumps(enriched_meta, ensure_ascii=False),
        user_approved=bool(user_approved),
        contains_sensitive=bool(has_sensitive),
        session_id=session_id,
        expires_at=expires_at,
    )
    db.add(record)
    db.commit()
    db.refresh(record)

    return {
        "success": True,
        "deduplicated": False,
        "memory": serialize_memory(record),
        "message": "Memory stored successfully."
    }


def record_episodic_event(
    db: Session,
    what_user_asked: str,
    what_tars_did: str,
    result_summary: str,
    error_occurred: Optional[str] = None,
    lesson_extracted: Optional[str] = None,
    session_id: str = "default",
) -> Dict[str, Any]:
    """
    Stores a structured Episodic Memory of an interaction/event:
    - what the user asked
    - what TARS did
    - what the outcome was
    - what error occurred (if any)
    - what lesson was extracted
    """
    content = (
        f"User Query: {what_user_asked} | Action: {what_tars_did} | "
        f"Outcome: {result_summary} | Error: {error_occurred or 'None'} | "
        f"Lesson: {lesson_extracted or 'Standard execution'}"
    )
    meta = {
        "what_user_asked": what_user_asked,
        "what_tars_did": what_tars_did,
        "result_summary": result_summary,
        "error_occurred": error_occurred,
        "lesson_extracted": lesson_extracted,
    }
    return store_memory(
        db=db,
        content=content,
        memory_type="EPISODIC",
        subject=what_user_asked[:120] or "episodic_event",
        category="episode",
        is_verified_fact=True,
        fact_or_inference="FACT",
        source_type="experience",
        source_reference="tars_episodic_logger",
        confidence=0.95,
        metadata=meta,
        user_approved=True,
        session_id=session_id,
    )


def re_rank_memory_candidates(
    query: str,
    candidates: List[Tuple[float, MemoryRecord]],
    top_k: int = 10,
) -> List[Dict[str, Any]]:
    """
    Stage 2 Re-ranking:
    Takes top candidates from semantic/lexical similarity (Stage 1) and applies
    multi-signal disambiguation:
    - Sibling / component side matching & contradiction penalty (-0.45 / +0.20)
    - Hardware model code match & mismatch penalty (+0.18 / -0.30)
    - Subsystem match (+0.08)
    - Exact numeric specification match (+0.10)
    - Verified fact confidence boost (+0.05)
    """
    if not candidates:
        return []

    norm_query = normalize_text(query)
    q_tokens = set(re.findall(r"[\w-]+", norm_query))

    query_side = None
    for side in SIDE_VARIANTS:
        if side in q_tokens or f"{side}-side" in norm_query or f"{side}side" in norm_query:
            query_side = side
            break

    query_models = set(re.findall(r"\b[A-Za-z]{1,5}-\d{2,5}[A-Za-z]?\b", query.upper()))
    query_specs = set(re.findall(r"\b\d+(?:\.\d+)?\b", query))
    query_subsystems = set()
    for sub, aliases in SUBSYSTEM_ALIASES.items():
        if sub in q_tokens or any(alias in q_tokens for alias in aliases):
            query_subsystems.add(sub)

    re_ranked: List[Tuple[float, float, List[str], MemoryRecord]] = []

    for base_sim, record in candidates:
        signals: List[str] = []
        score_adj = 0.0

        try:
            cand_meta = json.loads(record.metadata_json or "{}")
        except Exception:
            cand_meta = {}

        cand_struct = cand_meta.get("structured_attributes")
        if not cand_struct or not isinstance(cand_struct, dict):
            cand_struct = extract_structured_metadata(
                text=record.content,
                subject=record.subject,
                explicit_metadata=cand_meta,
                is_verified_fact=bool(record.is_verified_fact),
                source_reference=record.source_reference,
            )

        cand_text_lower = f"{record.subject} {record.content}".lower()
        cand_side = cand_struct.get("component_side")

        # 1. Sibling / Component Side Disambiguation
        if query_side:
            opp_sides = SIDE_VARIANTS.get(query_side, set())
            if cand_side and cand_side in opp_sides:
                score_adj -= 0.45
                signals.append(f"SIDE_MISMATCH_PENALTY(-0.45: query requires '{query_side}', candidate is '{cand_side}')")
            elif cand_side and cand_side == query_side:
                score_adj += 0.20
                signals.append(f"SIDE_MATCH_BONUS(+0.20: '{query_side}')")
            else:
                has_opp = False
                for opp in opp_sides:
                    if re.search(r"\b" + re.escape(opp) + r"\b", cand_text_lower):
                        score_adj -= 0.45
                        signals.append(f"SIDE_MISMATCH_PENALTY(-0.45: query requires '{query_side}', candidate mentions opposing '{opp}')")
                        has_opp = True
                        break
                if not has_opp and re.search(r"\b" + re.escape(query_side) + r"\b", cand_text_lower):
                    score_adj += 0.20
                    signals.append(f"SIDE_MATCH_BONUS(+0.20: candidate mentions '{query_side}')")

        # 2. Hardware Model Code Matching
        cand_models = set(cand_struct.get("models") or [])
        if not cand_models:
            cand_models = set(re.findall(r"\b[A-Za-z]{1,5}-\d{2,5}[A-Za-z]?\b", f"{record.subject} {record.content}".upper()))

        if query_models:
            matched_models = query_models & cand_models
            if matched_models:
                score_adj += 0.18
                signals.append(f"MODEL_MATCH_BONUS(+0.18: {list(matched_models)})")
            elif cand_models:
                score_adj -= 0.30
                signals.append(f"MODEL_MISMATCH_PENALTY(-0.30: query requested {list(query_models)}, candidate is {list(cand_models)})")

        # 3. Subsystem Matching
        cand_sub = cand_struct.get("subsystem")
        if query_subsystems and cand_sub and cand_sub in query_subsystems:
            score_adj += 0.16
            signals.append(f"SUBSYSTEM_MATCH_BONUS(+0.16: {cand_sub})")

        # 4. Specification Matching
        cand_specs = set(cand_struct.get("specifications") or [])
        if query_specs and (query_specs & cand_specs):
            score_adj += 0.10
            signals.append(f"SPEC_MATCH_BONUS(+0.10: {list(query_specs & cand_specs)})")

        # 5. Engineering Unit Matching
        cand_units = set(cand_struct.get("units") or [])
        matched_units = [u for u in cand_units if u in q_tokens or f"{u}s" in q_tokens]
        if matched_units:
            score_adj += 0.14
            signals.append(f"UNIT_MATCH_BONUS(+0.14: {matched_units})")

        # 6. Verified Fact Boost
        if record.is_verified_fact:
            score_adj += 0.05
            signals.append("VERIFIED_FACT_BONUS(+0.05)")

        final_score = round(max(0.01, min(1.0, base_sim + score_adj)), 4)
        re_ranked.append((final_score, base_sim, signals, record))

    re_ranked.sort(key=lambda x: (x[0], x[1]), reverse=True)

    results = []
    for final_sim, base_sim, sigs, rec in re_ranked[:top_k]:
        results.append(serialize_memory(
            rec,
            similarity=final_sim,
            signals=sigs,
            base_similarity=base_sim
        ))
    return results


def search_memories(
    db: Session,
    query: str = "",
    memory_type: Optional[str] = None,
    category: Optional[str] = None,
    only_verified_facts: bool = False,
    top_k: int = 10,
    min_similarity: float = 0.15,
) -> List[Dict[str, Any]]:
    """
    Two-Stage Hybrid Memory Retrieval:
    Stage 1: Semantic embedding + token Jaccard similarity across candidate records.
    Stage 2: Multi-signal structured re-ranking with side conflict penalty and model/spec bonuses.
    """
    q = db.query(MemoryRecord)
    if memory_type:
        q = q.filter(MemoryRecord.memory_type == memory_type.upper())
    if category:
        q = q.filter(MemoryRecord.category == category)
    if only_verified_facts:
        q = q.filter(MemoryRecord.is_verified_fact == True)  # noqa: E712

    records = q.order_by(MemoryRecord.updated_at.desc()).limit(300).all()
    if not query or not query.strip():
        return [serialize_memory(r) for r in records[:top_k]]

    query_vec = compute_semantic_embedding(query)
    scored: List[Tuple[float, MemoryRecord]] = []

    for r in records:
        try:
            r_vec = json.loads(r.embedding_json) if r.embedding_json else None
        except Exception:
            r_vec = None
        full_text = f"{r.subject} {r.content}"
        sim = hybrid_text_similarity(query, full_text, query_vec, r_vec)
        # Boost direct substring match
        if normalize_text(query) in normalize_text(full_text):
            sim = max(sim, 0.88)
        if sim >= min_similarity:
            scored.append((sim, r))

    scored.sort(key=lambda x: x[0], reverse=True)
    # Stage 1: Candidate retrieval pool (top 35)
    candidates = scored[:35]
    # Stage 2: Multi-signal re-ranking
    return re_rank_memory_candidates(query=query, candidates=candidates, top_k=top_k)


def update_memory(
    db: Session,
    memory_uid: str,
    content: Optional[str] = None,
    subject: Optional[str] = None,
    category: Optional[str] = None,
    is_verified_fact: Optional[bool] = None,
    fact_or_inference: Optional[str] = None,
    user_approved: Optional[bool] = None,
    concepts: Optional[List[Dict[str, str]]] = None,
) -> Optional[Dict[str, Any]]:
    record = db.query(MemoryRecord).filter(MemoryRecord.memory_uid == memory_uid).first()
    if not record:
        return None

    if content is not None and content.strip():
        record.content = content.strip()
        record.content_hash = compute_content_hash(record.content)
    if subject is not None and subject.strip():
        record.subject = subject.strip()
    if category is not None:
        record.category = category
    if is_verified_fact is not None:
        record.is_verified_fact = bool(is_verified_fact)
        record.fact_or_inference = "FACT" if is_verified_fact else "INFERENCE"
    if fact_or_inference is not None and fact_or_inference.upper() in ("FACT", "INFERENCE"):
        record.fact_or_inference = fact_or_inference.upper()
        record.is_verified_fact = record.fact_or_inference == "FACT"
    if user_approved is not None:
        record.user_approved = bool(user_approved)
    if concepts is not None:
        record.concepts_json = json.dumps(concepts, ensure_ascii=False)

    record.embedding_json = json.dumps(compute_semantic_embedding(f"{record.subject} {record.content}"))
    record.updated_at = datetime.utcnow()
    db.commit()
    db.refresh(record)
    return serialize_memory(record)


def delete_memory(db: Session, memory_uid: str) -> bool:
    record = db.query(MemoryRecord).filter(MemoryRecord.memory_uid == memory_uid).first()
    if not record:
        return False
    db.delete(record)
    db.commit()
    return True


def get_memory_stats(db: Session) -> Dict[str, Any]:
    total = db.query(MemoryRecord).count()
    short_term = db.query(MemoryRecord).filter(MemoryRecord.memory_type == "SHORT_TERM").count()
    long_term = db.query(MemoryRecord).filter(MemoryRecord.memory_type == "LONG_TERM").count()
    episodic = db.query(MemoryRecord).filter(MemoryRecord.memory_type == "EPISODIC").count()
    semantic = db.query(MemoryRecord).filter(MemoryRecord.memory_type == "SEMANTIC").count()
    verified_facts = db.query(MemoryRecord).filter(MemoryRecord.is_verified_fact == True).count()  # noqa: E712

    return {
        "total_memories": total,
        "by_type": {
            "SHORT_TERM": short_term,
            "LONG_TERM": long_term,
            "EPISODIC": episodic,
            "SEMANTIC": semantic,
        },
        "verified_facts_count": verified_facts,
        "inferences_count": max(0, total - verified_facts),
    }
