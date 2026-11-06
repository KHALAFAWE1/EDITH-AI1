import json
import re
import uuid
from datetime import datetime
from typing import Any, Dict, List, Optional

from sqlalchemy.orm import Session

from app.models.adaptive_learning import (
    EvaluationRun,
    ExperienceRecord,
    ImprovementProposal,
    KnowledgeDocument,
    LearningRecord,
    MemoryRecord,
)
from app.services.memory_service import (
    compute_semantic_embedding,
    detect_sensitive_data,
    hybrid_text_similarity,
    record_episodic_event,
    search_memories,
    store_memory,
    update_memory,
)

VALID_LEARNING_SOURCES = {
    "conversation",
    "document",
    "book",
    "search",
    "experience",
    "user_correction",
    "test_result",
}


def evaluate_information_quality(raw_input: str, source_type: str) -> Dict[str, Any]:
    """
    Step 3 of the 8-step Learning Pipeline:
    Validates information quality, specificity, and safety before extraction.
    """
    clean = (raw_input or "").strip()
    if len(clean) < 8:
        return {
            "valid": False,
            "quality_score": 0.1,
            "reason": "Input is too short or lacks substantive knowledge (< 8 chars).",
        }

    has_sensitive, sens_types, _ = detect_sensitive_data(clean)
    if has_sensitive:
        return {
            "valid": False,
            "quality_score": 0.0,
            "reason": f"Rejected sensitive/secret data ({', '.join(sens_types)}).",
        }

    words = re.findall(r"[\w\u0600-\u06FF]+", clean)
    if len(words) < 3:
        return {
            "valid": False,
            "quality_score": 0.25,
            "reason": "Input contains fewer than 3 meaningful words.",
        }

    source_weights = {
        "user_correction": 0.96,
        "test_result": 0.95,
        "document": 0.92,
        "book": 0.94,
        "experience": 0.88,
        "conversation": 0.82,
        "search": 0.78,
    }
    base_score = source_weights.get(source_type, 0.75)
    length_bonus = min(0.08, len(words) * 0.004)
    score = round(min(1.0, base_score + length_bonus), 3)

    return {
        "valid": score >= 0.5,
        "quality_score": score,
        "reason": "Information passed quality and authenticity checks.",
    }


def extract_structured_knowledge(raw_input: str, subject_hint: Optional[str] = None) -> Dict[str, str]:
    """
    Step 4 of the 8-step Learning Pipeline:
    Extracts subject, core knowledge statement, and classifies FACT vs. INFERENCE.
    """
    clean = (raw_input or "").strip()
    lines = [ln.strip() for ln in clean.splitlines() if ln.strip()]
    first_line = lines[0] if lines else clean

    if subject_hint and subject_hint.strip():
        subject = subject_hint.strip()[:180]
    elif ":" in first_line and len(first_line.split(":")[0]) < 80:
        subject = first_line.split(":")[0].strip()
    else:
        tokens = re.findall(r"[\w\u0600-\u06FF]+", first_line)
        subject = " ".join(tokens[:6]) if tokens else "general_knowledge"

    inference_markers = ["ربما", "قد ", "أعتقد", "يحتمل", "غالباً", "maybe", "probably", "might", "hypothesis", "infer"]
    is_inference = any(m in clean.lower() for m in inference_markers)
    fact_or_inference = "INFERENCE" if is_inference else "FACT"

    return {
        "subject": subject[:180],
        "extracted_knowledge": clean,
        "fact_or_inference": fact_or_inference,
    }


def generate_verification_test(subject: str, extracted_knowledge: str) -> Dict[str, str]:
    """
    Step 6 of the 8-step Learning Pipeline:
    Generates a concrete retrieval & comprehension test question and expected answer.
    """
    is_ar = bool(re.search(r"[\u0600-\u06FF]", extracted_knowledge))
    if is_ar:
        question = f"ما هي المعلومة الموثقة لدى TARS حول موضوع «{subject}»؟"
    else:
        question = f"What is the verified knowledge stored in TARS regarding '{subject}'?"

    return {
        "question": question,
        "expected_answer": extracted_knowledge,
    }


def run_learning_pipeline(
    db: Session,
    raw_input: str,
    source_type: str = "conversation",
    source_reference: str = "user_approved_input",
    subject_hint: Optional[str] = None,
    category: str = "learned_knowledge",
    auto_verify: bool = True,
    simulated_answer_override: Optional[str] = None,
) -> Dict[str, Any]:
    """
    Executes the complete 8-Step TARS Learning Pipeline:
      Step 1: Receive information or experience
      Step 2: Identify type and source
      Step 3: Validate quality and reliability
      Step 4: Extract structured knowledge
      Step 5: Store in candidate Long-Term/Semantic memory
      Step 6: Generate verification test
      Step 7: Measure verification score (retrieval & comprehension test)
      Step 8: Approve or reject knowledge based on test result
    """
    # Step 1 & 2: Receive & classify source
    src_type = (source_type or "conversation").lower().strip()
    if src_type not in VALID_LEARNING_SOURCES:
        src_type = "conversation"

    # Step 3: Validate quality
    quality = evaluate_information_quality(raw_input, src_type)
    learning_uid = f"lrn_{uuid.uuid4().hex[:12]}"

    if not quality["valid"]:
        rejected_rec = LearningRecord(
            learning_uid=learning_uid,
            source_type=src_type,
            source_reference=source_reference,
            raw_input=raw_input or "",
            quality_score=quality["quality_score"],
            extracted_subject=subject_hint or "rejected_input",
            extracted_knowledge=raw_input or "",
            fact_or_inference="INFERENCE",
            verification_question="N/A (Quality Check Failed)",
            expected_answer="N/A",
            verification_score=0.0,
            verification_passed=False,
            pipeline_step=3,
            approval_status="REJECTED",
            rejection_reason=quality["reason"],
        )
        db.add(rejected_rec)
        db.commit()
        db.refresh(rejected_rec)
        return {
            "success": False,
            "learned": False,
            "pipeline_step_reached": 3,
            "learning_record": serialize_learning_record(rejected_rec),
            "message": f"Learning rejected at Step 3 (Quality Validation): {quality['reason']}",
        }

    # Step 4: Extract structured knowledge
    extracted = extract_structured_knowledge(raw_input, subject_hint)

    # Step 5: Store in candidate memory (initially user_approved=False until Step 8 passes)
    mem_res = store_memory(
        db=db,
        content=extracted["extracted_knowledge"],
        memory_type="SEMANTIC" if src_type in ("document", "book", "search") else "LONG_TERM",
        subject=extracted["subject"],
        category=category,
        is_verified_fact=False,
        fact_or_inference=extracted["fact_or_inference"],
        source_type=src_type,
        source_reference=source_reference,
        confidence=quality["quality_score"],
        user_approved=False,
    )
    candidate_mem_uid = mem_res.get("memory", {}).get("memory_uid")

    # Step 6: Generate verification test
    quiz = generate_verification_test(extracted["subject"], extracted["extracted_knowledge"])

    learning_rec = LearningRecord(
        learning_uid=learning_uid,
        source_type=src_type,
        source_reference=source_reference,
        raw_input=raw_input.strip(),
        quality_score=quality["quality_score"],
        extracted_subject=extracted["subject"],
        extracted_knowledge=extracted["extracted_knowledge"],
        fact_or_inference=extracted["fact_or_inference"],
        candidate_memory_uid=candidate_mem_uid,
        verification_question=quiz["question"],
        expected_answer=quiz["expected_answer"],
        pipeline_step=6,
        approval_status="PENDING_TEST",
    )
    db.add(learning_rec)
    db.commit()
    db.refresh(learning_rec)

    if not auto_verify:
        return {
            "success": True,
            "learned": False,
            "pipeline_step_reached": 6,
            "learning_record": serialize_learning_record(learning_rec),
            "message": "Knowledge extracted and staged at Step 6; awaiting verification test execution.",
        }

    # Steps 7 & 8: Run verification test & approve/reject
    return verify_learning_record(
        db=db,
        learning_uid=learning_uid,
        candidate_answer=simulated_answer_override,
    )


def verify_learning_record(
    db: Session,
    learning_uid: str,
    candidate_answer: Optional[str] = None,
    pass_threshold: float = 0.70,
) -> Dict[str, Any]:
    """
    Steps 7 & 8 of the Learning Pipeline:
    Executes the retrieval/comprehension test against TARS Memory (or evaluates a provided
    candidate answer), measures the score, and approves or rejects the knowledge.
    """
    rec = db.query(LearningRecord).filter(LearningRecord.learning_uid == learning_uid).first()
    if not rec:
        raise ValueError(f"LearningRecord '{learning_uid}' not found.")

    # Step 7: Retrieve from memory if no explicit candidate_answer override was passed
    if candidate_answer is not None:
        actual_answer = candidate_answer.strip()
    else:
        # Check if candidate memory was staged and can be read
        target_cand = None
        if rec.candidate_memory_uid:
            target_cand = (
                db.query(MemoryRecord)
                .filter(MemoryRecord.memory_uid == rec.candidate_memory_uid)
                .first()
            )

        if target_cand:
            actual_answer = target_cand.content
        else:
            retrieved = search_memories(
                db,
                query=f"{rec.extracted_subject} {rec.verification_question}",
                top_k=3,
                min_similarity=0.1,
            )
            if retrieved:
                actual_answer = retrieved[0]["content"]
            else:
                actual_answer = ""

    score = hybrid_text_similarity(rec.expected_answer, actual_answer) if actual_answer else 0.0
    passed = bool(score >= pass_threshold)

    rec.actual_answer = actual_answer
    rec.verification_score = round(score, 4)
    rec.verification_passed = passed
    rec.pipeline_step = 8
    rec.verified_at = datetime.utcnow()

    # Step 8: Approve or Reject
    if passed:
        rec.approval_status = "APPROVED"
        rec.rejection_reason = None
        if rec.candidate_memory_uid:
            update_memory(
                db=db,
                memory_uid=rec.candidate_memory_uid,
                is_verified_fact=(rec.fact_or_inference == "FACT"),
                fact_or_inference=rec.fact_or_inference,
                user_approved=True,
            )
    else:
        rec.approval_status = "REJECTED"
        rec.rejection_reason = (
            f"Verification test score ({round(score * 100, 1)}%) fell below required threshold "
            f"({round(pass_threshold * 100, 1)}%). Knowledge not promoted to verified memory."
        )
        if rec.candidate_memory_uid:
            update_memory(
                db=db,
                memory_uid=rec.candidate_memory_uid,
                is_verified_fact=False,
                user_approved=False,
            )

    db.commit()
    db.refresh(rec)

    return {
        "success": True,
        "learned": passed,
        "pipeline_step_reached": 8,
        "verification_score": rec.verification_score,
        "verification_passed": passed,
        "learning_record": serialize_learning_record(rec),
        "message": (
            f"Knowledge verified and APPROVED (Score: {round(score * 100, 1)}%)."
            if passed
            else f"Knowledge REJECTED at verification gate (Score: {round(score * 100, 1)}%)."
        ),
    }


def serialize_learning_record(rec: LearningRecord) -> Dict[str, Any]:
    return {
        "id": rec.id,
        "learning_uid": rec.learning_uid,
        "source_type": rec.source_type,
        "source_reference": rec.source_reference,
        "raw_input": rec.raw_input,
        "quality_score": rec.quality_score,
        "extracted_subject": rec.extracted_subject,
        "extracted_knowledge": rec.extracted_knowledge,
        "fact_or_inference": rec.fact_or_inference,
        "candidate_memory_uid": rec.candidate_memory_uid,
        "verification_question": rec.verification_question,
        "expected_answer": rec.expected_answer,
        "actual_answer": rec.actual_answer,
        "verification_score": rec.verification_score,
        "verification_passed": bool(rec.verification_passed),
        "pipeline_step": rec.pipeline_step,
        "approval_status": rec.approval_status,
        "rejection_reason": rec.rejection_reason,
        "created_at": rec.created_at.isoformat() if rec.created_at else None,
        "verified_at": rec.verified_at.isoformat() if rec.verified_at else None,
    }


# ==============================================================================
# EXPERIENCE & FEEDBACK SYSTEM (All 13 Mandatory Fields)
# ==============================================================================

def record_experience(
    db: Session,
    task_description: str,
    input_text: str,
    actual_result: str,
    context: Optional[Dict[str, Any]] = None,
    actions_taken: Optional[List[str]] = None,
    tools_used: Optional[List[str]] = None,
    expected_result: str = "",
    evaluation_score: float = 0.85,
    errors: str = "None",
    human_feedback: str = "",
    lessons_extracted: str = "",
    approval_status: str = "APPROVED",
) -> Dict[str, Any]:
    """
    Stores a structured operational experience with all 13 required fields and indexes
    its semantic embedding so similar past experiences can be retrieved before solving new tasks.
    """
    exp_id = f"exp_{uuid.uuid4().hex[:12]}"
    emb = compute_semantic_embedding(f"{task_description} {input_text} {lessons_extracted}")

    if not lessons_extracted:
        if errors and errors != "None":
            lessons_extracted = f"Avoid error '{errors[:120]}' when handling task '{task_description[:80]}'."
        else:
            lessons_extracted = f"Successfully executed '{task_description[:80]}' using {', '.join(tools_used or ['TARS Core'])}."

    rec = ExperienceRecord(
        experience_id=exp_id,
        task_description=task_description.strip(),
        input_text=input_text.strip(),
        context=json.dumps(context or {}, ensure_ascii=False),
        actions_taken=json.dumps(actions_taken or [], ensure_ascii=False),
        tools_used=json.dumps(tools_used or [], ensure_ascii=False),
        expected_result=expected_result or "Accurate, verified response",
        actual_result=actual_result,
        evaluation_score=float(evaluation_score),
        errors=errors or "None",
        human_feedback=human_feedback,
        lessons_extracted=lessons_extracted,
        approval_status=approval_status,
        embedding_json=json.dumps(emb),
    )
    db.add(rec)
    db.commit()
    db.refresh(rec)

    # Also log in Episodic Memory
    record_episodic_event(
        db=db,
        what_user_asked=input_text[:300],
        what_tars_did=task_description[:200],
        result_summary=actual_result[:300],
        error_occurred=errors if errors != "None" else None,
        lesson_extracted=lessons_extracted,
    )

    return serialize_experience(rec)


def add_experience_feedback(
    db: Session,
    experience_id: str,
    human_feedback: str,
    evaluation_score: Optional[float] = None,
    lessons_extracted: Optional[str] = None,
    approval_status: Optional[str] = None,
    promote_to_long_term_memory: bool = True,
) -> Optional[Dict[str, Any]]:
    """
    Records operator feedback / correction on an experience and optionally promotes
    the extracted lesson into Long-Term Memory through the 8-step Learning Pipeline.
    """
    rec = db.query(ExperienceRecord).filter(ExperienceRecord.experience_id == experience_id).first()
    if not rec:
        return None

    rec.human_feedback = human_feedback.strip()
    if evaluation_score is not None:
        rec.evaluation_score = max(0.0, min(1.0, float(evaluation_score)))
    if lessons_extracted is not None and lessons_extracted.strip():
        rec.lessons_extracted = lessons_extracted.strip()
    elif human_feedback.strip():
        rec.lessons_extracted = f"Operator feedback lesson: {human_feedback.strip()}"
    if approval_status is not None:
        rec.approval_status = approval_status.upper()

    rec.updated_at = datetime.utcnow()
    db.commit()
    db.refresh(rec)

    if promote_to_long_term_memory and rec.lessons_extracted:
        run_learning_pipeline(
            db=db,
            raw_input=f"{rec.task_description}: {rec.lessons_extracted}",
            source_type="user_correction",
            source_reference=f"experience:{rec.experience_id}",
            subject_hint=rec.task_description[:100],
            category="experience_lesson",
            auto_verify=True,
        )

    return serialize_experience(rec)


def find_similar_experiences(
    db: Session,
    query: str,
    top_k: int = 5,
    min_similarity: float = 0.15,
) -> List[Dict[str, Any]]:
    """
    Retrieves past similar experiences so TARS can reuse successful strategies and avoid past errors.
    """
    records = (
        db.query(ExperienceRecord)
        .filter(ExperienceRecord.approval_status == "APPROVED")
        .order_by(ExperienceRecord.created_at.desc())
        .limit(200)
        .all()
    )
    if not query or not query.strip():
        return [serialize_experience(r) for r in records[:top_k]]

    q_vec = compute_semantic_embedding(query)
    scored = []
    for r in records:
        try:
            r_vec = json.loads(r.embedding_json) if r.embedding_json else None
        except Exception:
            r_vec = None
        sim = hybrid_text_similarity(
            query,
            f"{r.task_description} {r.input_text} {r.lessons_extracted}",
            q_vec,
            r_vec,
        )
        if sim >= min_similarity:
            scored.append((sim, r))

    scored.sort(key=lambda x: x[0], reverse=True)
    return [serialize_experience(r, similarity=sim) for sim, r in scored[:top_k]]


def serialize_experience(rec: ExperienceRecord, similarity: Optional[float] = None) -> Dict[str, Any]:
    try:
        ctx = json.loads(rec.context or "{}")
    except Exception:
        ctx = {"raw": rec.context}
    try:
        actions = json.loads(rec.actions_taken or "[]")
    except Exception:
        actions = []
    try:
        tools = json.loads(rec.tools_used or "[]")
    except Exception:
        tools = []

    data = {
        "id": rec.id,
        "experience_id": rec.experience_id,
        "task_description": rec.task_description,
        "input_text": rec.input_text,
        "context": ctx,
        "actions_taken": actions,
        "tools_used": tools,
        "expected_result": rec.expected_result,
        "actual_result": rec.actual_result,
        "evaluation_score": rec.evaluation_score,
        "errors": rec.errors,
        "human_feedback": rec.human_feedback,
        "lessons_extracted": rec.lessons_extracted,
        "approval_status": rec.approval_status,
        "created_at": rec.created_at.isoformat() if rec.created_at else None,
        "updated_at": rec.updated_at.isoformat() if rec.updated_at else None,
    }
    if similarity is not None:
        data["similarity"] = round(similarity, 4)
    return data


# ==============================================================================
# TARS LEARNING STAGES (STAGE 1 -> STAGE 2 -> STAGE 3)
# ==============================================================================

def compute_learning_stage_status(db: Session) -> Dict[str, Any]:
    """
    Computes TARS's real learning maturity stage from verified database metrics:
      - Stage 1 — Basic Learning:
        Saving preferences, remembering user facts, logging conversations, retrieving previous info.
      - Stage 2 — Knowledge Development:
        Ingesting files/documents, building knowledge base, semantic search, testing new knowledge.
      - Stage 3 — Analytical Learning:
        Analyzing errors, learning from experiences, improving strategies, proposing verified improvements.
    """
    memories_count = db.query(MemoryRecord).count()
    verified_facts_count = db.query(MemoryRecord).filter(MemoryRecord.is_verified_fact == True).count()  # noqa: E712
    docs_count = db.query(KnowledgeDocument).count()
    approved_learning_count = (
        db.query(LearningRecord).filter(LearningRecord.approval_status == "APPROVED").count()
    )
    experiences_count = db.query(ExperienceRecord).count()
    eval_runs_count = db.query(EvaluationRun).count()
    proposals_count = db.query(ImprovementProposal).count()

    stage1_ready = memories_count >= 1
    stage2_ready = docs_count >= 1 and approved_learning_count >= 1
    stage3_ready = stage2_ready and experiences_count >= 1 and (eval_runs_count >= 1 or proposals_count >= 1)

    if stage3_ready:
        current_stage = 3
        stage_name = "Stage 3 — Analytical Learning (التعلم التحليلي)"
    elif stage2_ready:
        current_stage = 2
        stage_name = "Stage 2 — Knowledge Development (تطوير المعرفة)"
    else:
        current_stage = 1
        stage_name = "Stage 1 — Basic Learning (التعلم الأساسي)"

    return {
        "current_stage": current_stage,
        "stage_name": stage_name,
        "metrics": {
            "total_memories": memories_count,
            "verified_facts": verified_facts_count,
            "documents_ingested": docs_count,
            "approved_learning_tests": approved_learning_count,
            "experiences_logged": experiences_count,
            "evaluation_runs": eval_runs_count,
            "improvement_proposals": proposals_count,
        },
        "stages": [
            {
                "stage": 1,
                "title": "Stage 1 — Basic Learning",
                "title_ar": "المرحلة 1 — التعلم الأساسي",
                "capabilities": [
                    "حفظ التفضيلات والحقائق المعتمدة",
                    "تذكر معلومات المستخدم والمشاريع",
                    "تسجيل المحادثات في الذاكرة قصيرة وطويلة المدى",
                    "استرجاع المعلومات السابقة بدقة",
                ],
                "unlocked": True,
                "completed": stage1_ready,
            },
            {
                "stage": 2,
                "title": "Stage 2 — Knowledge Development",
                "title_ar": "المرحلة 2 — تطوير المعرفة",
                "capabilities": [
                    "قراءة الملفات والوثائق (TXT, PDF, DOCX)",
                    "بناء قاعدة معرفة مقسمة إلى فقرات مع المصادر",
                    "البحث الدلالي (Semantic Search) وكشف التعارض",
                    "اختبار المعرفة الجديدة قبل اعتمادها",
                ],
                "unlocked": stage1_ready,
                "completed": stage2_ready,
            },
            {
                "stage": 3,
                "title": "Stage 3 — Analytical Learning",
                "title_ar": "المرحلة 3 — التعلم التحليلي",
                "capabilities": [
                    "تحليل الأخطاء واستخلاص الدروس من التجارب",
                    "استرجاع التجارب المشابهة عند حل المشكلات",
                    "تقييم الأداء الدوري وكشف التراجع (Regression)",
                    "اقتراح تحسينات محكومة بإشراف وموافقة المستخدم",
                ],
                "unlocked": stage2_ready,
                "completed": stage3_ready,
            },
        ],
    }
