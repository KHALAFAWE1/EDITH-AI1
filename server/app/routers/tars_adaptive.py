from typing import Any, Dict, List, Optional
from fastapi import APIRouter, Depends, File, Form, HTTPException, Query, UploadFile
from pydantic import BaseModel, Field
from sqlalchemy.orm import Session

from app.database import get_db
from app.models.adaptive_learning import (
    EvaluationRun,
    ImprovementProposal,
    KnowledgeDocument,
    LearningRecord,
    ModelRoutingLog,
)
from app.services.evaluation_service import (
    evaluate_answer_against_sources,
    run_evaluation_suite,
    run_sandboxed_code_test,
    serialize_evaluation_run,
)
from app.services.improvement_manager import (
    apply_approved_proposal,
    create_improvement_proposal,
    get_training_readiness_status,
    prepare_training_dataset,
    review_improvement_proposal,
    rollback_proposal,
    serialize_proposal,
    test_proposal_in_isolation,
)
from app.services.knowledge_service import (
    ingest_document,
    search_knowledge_chunks,
    serialize_document,
)
from app.services.learning_engine import (
    add_experience_feedback,
    compute_learning_stage_status,
    find_similar_experiences,
    record_experience,
    run_learning_pipeline,
    serialize_learning_record,
    verify_learning_record,
)
from app.services.memory_service import (
    delete_memory,
    get_memory_stats,
    record_episodic_event,
    search_memories,
    store_memory,
    update_memory,
)
from app.services.permissions_service import (
    check_rate_limit,
    create_adaptive_backup_snapshot,
    get_all_permissions,
    is_permission_enabled,
    update_permission_scope,
)
from app.services.tars_core import (
    get_hybrid_core_status,
    save_routing_config,
    serialize_routing_log,
)

router = APIRouter(
    prefix="/tars",
    tags=["TARS Hybrid Adaptive Architecture"],
)


# ==============================================================================
# Pydantic Schemas
# ==============================================================================

class RoutingConfigUpdateSchema(BaseModel):
    routing_policy: Optional[str] = None
    ollama_base_url: Optional[str] = None
    preferred_local_model: Optional[str] = None
    preferred_cloud_provider: Optional[str] = None
    block_private_data_to_cloud: Optional[bool] = None
    auto_fallback: Optional[bool] = None
    inject_memory_and_knowledge: Optional[bool] = None


class MemoryCreateSchema(BaseModel):
    content: str
    memory_type: str = "LONG_TERM"  # SHORT_TERM | LONG_TERM | EPISODIC | SEMANTIC
    subject: str = "general"
    category: str = "general"
    is_verified_fact: bool = False
    fact_or_inference: Optional[str] = None
    source_type: str = "conversation"
    source_reference: str = "user_session"
    confidence: float = 0.85
    concepts: Optional[List[Dict[str, str]]] = None
    metadata: Optional[Dict[str, Any]] = None
    user_approved: bool = True
    allow_sensitive: bool = False
    session_id: str = "default"
    ttl_hours: Optional[int] = None


class MemoryUpdateSchema(BaseModel):
    content: Optional[str] = None
    subject: Optional[str] = None
    category: Optional[str] = None
    is_verified_fact: Optional[bool] = None
    fact_or_inference: Optional[str] = None
    user_approved: Optional[bool] = None
    concepts: Optional[List[Dict[str, str]]] = None


class EpisodicEventSchema(BaseModel):
    what_user_asked: str
    what_tars_did: str
    result_summary: str
    error_occurred: Optional[str] = None
    lesson_extracted: Optional[str] = None
    session_id: str = "default"


class LearningIngestSchema(BaseModel):
    raw_input: str
    source_type: str = "conversation"
    source_reference: str = "user_approved_input"
    subject_hint: Optional[str] = None
    category: str = "learned_knowledge"
    auto_verify: bool = True
    simulated_answer_override: Optional[str] = None


class LearningVerifySchema(BaseModel):
    candidate_answer: Optional[str] = None
    pass_threshold: float = 0.70


class ExperienceCreateSchema(BaseModel):
    task_description: str
    input_text: str
    actual_result: str
    context: Optional[Dict[str, Any]] = None
    actions_taken: Optional[List[str]] = Field(default_factory=list)
    tools_used: Optional[List[str]] = Field(default_factory=list)
    expected_result: str = ""
    evaluation_score: float = 0.85
    errors: str = "None"
    human_feedback: str = ""
    lessons_extracted: str = ""
    approval_status: str = "APPROVED"


class ExperienceFeedbackSchema(BaseModel):
    human_feedback: str
    evaluation_score: Optional[float] = None
    lessons_extracted: Optional[str] = None
    approval_status: Optional[str] = None
    promote_to_long_term_memory: bool = True


class EvaluationRunRequestSchema(BaseModel):
    eval_type: str = "comprehensive"
    custom_qa_tests: Optional[List[Dict[str, str]]] = None
    code_tests: Optional[List[Dict[str, str]]] = None


class SandboxTestRequestSchema(BaseModel):
    code_snippet: str
    test_assertion: str = ""
    timeout_sec: int = 4


class ProposalCreateSchema(BaseModel):
    title: str
    problem_description: str
    proposed_solution: str
    action_category: str = "modify_project_code"
    affected_files: Optional[List[str]] = Field(default_factory=list)
    risk_level: Optional[str] = None
    test_code_snippet: Optional[str] = None
    test_assertion: Optional[str] = None


class ProposalTestSchema(BaseModel):
    code_snippet: str = ""
    test_assertion: str = ""


class ProposalReviewSchema(BaseModel):
    decision: str  # APPROVE | REJECT
    reviewed_by: str = "human_operator"
    review_notes: str = ""


class ProposalRollbackSchema(BaseModel):
    reason: str = "Operator requested rollback"


class DatasetPrepareSchema(BaseModel):
    dataset_name: str = "tars_verified_dataset"
    custom_samples: Optional[List[Dict[str, str]]] = None
    user_approved: bool = False


class KnowledgeTextIngestSchema(BaseModel):
    title: str
    content: str
    file_type: str = "TXT"
    source_reference: str = "manual_reference"
    trust_level: float = 0.9
    ttl_days: Optional[int] = None
    chunk_size: int = 600


class PermissionUpdateSchema(BaseModel):
    scope_name: str
    enabled: bool
    requires_human_approval: Optional[bool] = None
    actor: str = "human_operator"


# ==============================================================================
# 1. HYBRID AI CORE & MODEL ROUTER ENDPOINTS
# ==============================================================================

@router.get("/core/status")
def api_get_core_status(db: Session = Depends(get_db)):
    return {
        "success": True,
        **get_hybrid_core_status(db),
        "learning_stage": compute_learning_stage_status(db),
        "memory_stats": get_memory_stats(db),
    }


@router.post("/core/routing-config")
def api_update_routing_config(payload: RoutingConfigUpdateSchema):
    updates = payload.model_dump(exclude_none=True) if hasattr(payload, "model_dump") else payload.dict(exclude_none=True)
    updated = save_routing_config(updates)
    return {
        "success": True,
        "routing_config": updated,
        "message": "TARS Hybrid Model Router configuration updated.",
    }


@router.get("/core/routing-logs")
def api_get_routing_logs(limit: int = Query(30, ge=1, le=200), db: Session = Depends(get_db)):
    logs = (
        db.query(ModelRoutingLog)
        .order_by(ModelRoutingLog.id.desc())
        .limit(limit)
        .all()
    )
    return {
        "success": True,
        "count": len(logs),
        "logs": [serialize_routing_log(r) for r in logs],
    }


# ==============================================================================
# 2. TARS MEMORY SYSTEM ENDPOINTS
# ==============================================================================

@router.get("/memory/stats")
def api_get_memory_stats(db: Session = Depends(get_db)):
    return {
        "success": True,
        **get_memory_stats(db),
    }


@router.get("/memory")
def api_search_memories(
    query: str = Query(""),
    memory_type: Optional[str] = Query(None),
    category: Optional[str] = Query(None),
    only_verified_facts: bool = Query(False),
    top_k: int = Query(20, ge=1, le=100),
    min_similarity: float = Query(0.12, ge=0.0, le=1.0),
    db: Session = Depends(get_db),
):
    results = search_memories(
        db=db,
        query=query,
        memory_type=memory_type,
        category=category,
        only_verified_facts=only_verified_facts,
        top_k=top_k,
        min_similarity=min_similarity,
    )
    return {
        "success": True,
        "count": len(results),
        "memories": results,
    }


@router.post("/memory")
def api_store_memory(payload: MemoryCreateSchema, db: Session = Depends(get_db)):
    if not check_rate_limit("memory_write", max_requests=120, window_seconds=60):
        raise HTTPException(status_code=429, detail="Rate limit exceeded for memory_write.")
    if not is_permission_enabled(db, "memory_write"):
        raise HTTPException(status_code=403, detail="Permission 'memory_write' is currently disabled.")

    try:
        res = store_memory(
            db=db,
            content=payload.content,
            memory_type=payload.memory_type,
            subject=payload.subject,
            category=payload.category,
            is_verified_fact=payload.is_verified_fact,
            fact_or_inference=payload.fact_or_inference,
            source_type=payload.source_type,
            source_reference=payload.source_reference,
            confidence=payload.confidence,
            concepts=payload.concepts,
            metadata=payload.metadata,
            user_approved=payload.user_approved,
            allow_sensitive=payload.allow_sensitive,
            session_id=payload.session_id,
            ttl_hours=payload.ttl_hours,
        )
        return res
    except ValueError as ve:
        raise HTTPException(status_code=400, detail=str(ve))


@router.post("/memory/episodic")
def api_record_episodic(payload: EpisodicEventSchema, db: Session = Depends(get_db)):
    if not is_permission_enabled(db, "memory_write"):
        raise HTTPException(status_code=403, detail="Permission 'memory_write' is currently disabled.")
    return record_episodic_event(
        db=db,
        what_user_asked=payload.what_user_asked,
        what_tars_did=payload.what_tars_did,
        result_summary=payload.result_summary,
        error_occurred=payload.error_occurred,
        lesson_extracted=payload.lesson_extracted,
        session_id=payload.session_id,
    )


@router.put("/memory/{memory_uid}")
def api_update_memory(memory_uid: str, payload: MemoryUpdateSchema, db: Session = Depends(get_db)):
    updated = update_memory(
        db=db,
        memory_uid=memory_uid,
        content=payload.content,
        subject=payload.subject,
        category=payload.category,
        is_verified_fact=payload.is_verified_fact,
        fact_or_inference=payload.fact_or_inference,
        user_approved=payload.user_approved,
        concepts=payload.concepts,
    )
    if not updated:
        raise HTTPException(status_code=404, detail=f"Memory '{memory_uid}' not found.")
    return {
        "success": True,
        "memory": updated,
        "message": "Memory updated successfully.",
    }


@router.delete("/memory/{memory_uid}")
def api_delete_memory(memory_uid: str, db: Session = Depends(get_db)):
    ok = delete_memory(db, memory_uid)
    if not ok:
        raise HTTPException(status_code=404, detail=f"Memory '{memory_uid}' not found.")
    return {
        "success": True,
        "deleted_uid": memory_uid,
        "message": "Memory deleted permanently.",
    }


# ==============================================================================
# 3. TARS LEARNING ENGINE & STAGES ENDPOINTS
# ==============================================================================

@router.get("/learning/stage")
def api_get_learning_stage(db: Session = Depends(get_db)):
    return {
        "success": True,
        **compute_learning_stage_status(db),
    }


@router.get("/learning/records")
def api_list_learning_records(
    status: Optional[str] = Query(None),
    limit: int = Query(30, ge=1, le=200),
    db: Session = Depends(get_db),
):
    q = db.query(LearningRecord)
    if status:
        q = q.filter(LearningRecord.approval_status == status.upper())
    records = q.order_by(LearningRecord.id.desc()).limit(limit).all()
    return {
        "success": True,
        "count": len(records),
        "records": [serialize_learning_record(r) for r in records],
    }


@router.post("/learning/ingest")
def api_ingest_learning(payload: LearningIngestSchema, db: Session = Depends(get_db)):
    if not is_permission_enabled(db, "memory_write"):
        raise HTTPException(status_code=403, detail="Permission 'memory_write' is currently disabled.")
    return run_learning_pipeline(
        db=db,
        raw_input=payload.raw_input,
        source_type=payload.source_type,
        source_reference=payload.source_reference,
        subject_hint=payload.subject_hint,
        category=payload.category,
        auto_verify=payload.auto_verify,
        simulated_answer_override=payload.simulated_answer_override,
    )


@router.post("/learning/verify/{learning_uid}")
def api_verify_learning(
    learning_uid: str,
    payload: LearningVerifySchema,
    db: Session = Depends(get_db),
):
    try:
        return verify_learning_record(
            db=db,
            learning_uid=learning_uid,
            candidate_answer=payload.candidate_answer,
            pass_threshold=payload.pass_threshold,
        )
    except ValueError as ve:
        raise HTTPException(status_code=404, detail=str(ve))


# ==============================================================================
# 4. EXPERIENCE & FEEDBACK SYSTEM ENDPOINTS
# ==============================================================================

@router.get("/experiences")
def api_get_experiences(
    query: str = Query(""),
    top_k: int = Query(20, ge=1, le=100),
    min_similarity: float = Query(0.12, ge=0.0, le=1.0),
    db: Session = Depends(get_db),
):
    results = find_similar_experiences(
        db=db,
        query=query,
        top_k=top_k,
        min_similarity=min_similarity,
    )
    return {
        "success": True,
        "count": len(results),
        "experiences": results,
    }


@router.post("/experiences")
def api_create_experience(payload: ExperienceCreateSchema, db: Session = Depends(get_db)):
    exp = record_experience(
        db=db,
        task_description=payload.task_description,
        input_text=payload.input_text,
        actual_result=payload.actual_result,
        context=payload.context,
        actions_taken=payload.actions_taken,
        tools_used=payload.tools_used,
        expected_result=payload.expected_result,
        evaluation_score=payload.evaluation_score,
        errors=payload.errors,
        human_feedback=payload.human_feedback,
        lessons_extracted=payload.lessons_extracted,
        approval_status=payload.approval_status,
    )
    return {
        "success": True,
        "experience": exp,
    }


@router.post("/experiences/{experience_id}/feedback")
def api_add_experience_feedback(
    experience_id: str,
    payload: ExperienceFeedbackSchema,
    db: Session = Depends(get_db),
):
    updated = add_experience_feedback(
        db=db,
        experience_id=experience_id,
        human_feedback=payload.human_feedback,
        evaluation_score=payload.evaluation_score,
        lessons_extracted=payload.lessons_extracted,
        approval_status=payload.approval_status,
        promote_to_long_term_memory=payload.promote_to_long_term_memory,
    )
    if not updated:
        raise HTTPException(status_code=404, detail=f"Experience '{experience_id}' not found.")
    return {
        "success": True,
        "experience": updated,
        "message": "Operator feedback recorded and lesson extracted.",
    }


# ==============================================================================
# 5. EVALUATION ENGINE ENDPOINTS
# ==============================================================================

@router.get("/evaluation/runs")
def api_list_evaluation_runs(limit: int = Query(20, ge=1, le=100), db: Session = Depends(get_db)):
    runs = (
        db.query(EvaluationRun)
        .order_by(EvaluationRun.id.desc())
        .limit(limit)
        .all()
    )
    return {
        "success": True,
        "count": len(runs),
        "runs": [serialize_evaluation_run(r) for r in runs],
    }


@router.post("/evaluation/run")
def api_run_evaluation(payload: EvaluationRunRequestSchema, db: Session = Depends(get_db)):
    res = run_evaluation_suite(
        db=db,
        eval_type=payload.eval_type,
        custom_qa_tests=payload.custom_qa_tests,
        code_tests=payload.code_tests,
    )
    return {
        "success": True,
        "evaluation": res,
    }


@router.post("/evaluation/sandbox-test")
def api_run_sandbox_test(payload: SandboxTestRequestSchema):
    res = run_sandboxed_code_test(
        code_snippet=payload.code_snippet,
        test_assertion=payload.test_assertion,
        timeout_sec=payload.timeout_sec,
    )
    return {
        "success": True,
        "sandbox_result": res,
    }


# ==============================================================================
# 6. CONTROLLED SELF-IMPROVEMENT (TARS IMPROVEMENT MANAGER) ENDPOINTS
# ==============================================================================

@router.get("/improvements")
def api_list_improvements(
    status: Optional[str] = Query(None),
    limit: int = Query(30, ge=1, le=100),
    db: Session = Depends(get_db),
):
    q = db.query(ImprovementProposal)
    if status:
        q = q.filter(ImprovementProposal.approval_status == status.upper())
    items = q.order_by(ImprovementProposal.id.desc()).limit(limit).all()
    return {
        "success": True,
        "count": len(items),
        "proposals": [serialize_proposal(p) for p in items],
    }


@router.post("/improvements")
def api_create_improvement_proposal(payload: ProposalCreateSchema, db: Session = Depends(get_db)):
    prop = create_improvement_proposal(
        db=db,
        title=payload.title,
        problem_description=payload.problem_description,
        proposed_solution=payload.proposed_solution,
        action_category=payload.action_category,
        affected_files=payload.affected_files,
        risk_level=payload.risk_level,
        test_code_snippet=payload.test_code_snippet,
        test_assertion=payload.test_assertion,
    )
    return {
        "success": True,
        "proposal": prop,
        "message": "Improvement proposal created and locked pending human review.",
    }


@router.post("/improvements/{proposal_id}/test")
def api_test_proposal(
    proposal_id: str,
    payload: ProposalTestSchema,
    db: Session = Depends(get_db),
):
    try:
        prop = test_proposal_in_isolation(
            db=db,
            proposal_id=proposal_id,
            code_snippet=payload.code_snippet,
            test_assertion=payload.test_assertion,
        )
        return {
            "success": True,
            "proposal": prop,
        }
    except ValueError as ve:
        raise HTTPException(status_code=404, detail=str(ve))


@router.post("/improvements/{proposal_id}/review")
def api_review_proposal(
    proposal_id: str,
    payload: ProposalReviewSchema,
    db: Session = Depends(get_db),
):
    try:
        prop = review_improvement_proposal(
            db=db,
            proposal_id=proposal_id,
            decision=payload.decision,
            reviewed_by=payload.reviewed_by,
            review_notes=payload.review_notes,
        )
        return {
            "success": True,
            "proposal": prop,
            "message": f"Proposal '{proposal_id}' marked as {prop['approval_status']}.",
        }
    except ValueError as ve:
        raise HTTPException(status_code=400, detail=str(ve))


@router.post("/improvements/{proposal_id}/apply")
def api_apply_proposal(proposal_id: str, db: Session = Depends(get_db)):
    try:
        prop = apply_approved_proposal(db, proposal_id)
        return {
            "success": True,
            "proposal": prop,
            "message": f"Proposal '{proposal_id}' applied with rollback snapshot saved.",
        }
    except PermissionError as pe:
        raise HTTPException(status_code=403, detail=str(pe))
    except ValueError as ve:
        raise HTTPException(status_code=404, detail=str(ve))


@router.post("/improvements/{proposal_id}/rollback")
def api_rollback_proposal(
    proposal_id: str,
    payload: ProposalRollbackSchema,
    db: Session = Depends(get_db),
):
    try:
        prop = rollback_proposal(db, proposal_id, reason=payload.reason)
        return {
            "success": True,
            "proposal": prop,
            "message": f"Proposal '{proposal_id}' rolled back successfully.",
        }
    except ValueError as ve:
        raise HTTPException(status_code=404, detail=str(ve))


# ==============================================================================
# 7. MODEL TRAINING & FINE-TUNING READINESS ENDPOINTS
# ==============================================================================

@router.get("/training/status")
def api_get_training_status(db: Session = Depends(get_db)):
    return {
        "success": True,
        **get_training_readiness_status(db),
    }


@router.post("/training/prepare-dataset")
def api_prepare_training_dataset(payload: DatasetPrepareSchema, db: Session = Depends(get_db)):
    ds = prepare_training_dataset(
        db=db,
        dataset_name=payload.dataset_name,
        custom_samples=payload.custom_samples,
        user_approved=payload.user_approved,
    )
    return {
        "success": True,
        "dataset": ds,
        "message": f"Dataset '{ds['dataset_version']}' cleaned, deduplicated, and exported ({ds['clean_record_count']} records).",
    }


# ==============================================================================
# 8. KNOWLEDGE ACQUISITION MODULE ENDPOINTS (TXT, PDF, DOCX, MD, JSON)
# ==============================================================================

@router.get("/knowledge/documents")
def api_list_knowledge_documents(db: Session = Depends(get_db)):
    docs = (
        db.query(KnowledgeDocument)
        .order_by(KnowledgeDocument.id.desc())
        .all()
    )
    return {
        "success": True,
        "count": len(docs),
        "documents": [serialize_document(d) for d in docs],
    }


@router.post("/knowledge/upload")
async def api_upload_knowledge_document(
    file: UploadFile = File(...),
    title: Optional[str] = Form(None),
    source_reference: str = Form("uploaded_document"),
    trust_level: float = Form(0.92),
    ttl_days: Optional[int] = Form(None),
    db: Session = Depends(get_db),
):
    if not is_permission_enabled(db, "file_access"):
        raise HTTPException(status_code=403, detail="Permission 'file_access' is currently disabled.")

    raw_bytes = await file.read()
    try:
        res = ingest_document(
            db=db,
            filename=file.filename or "document.txt",
            raw_bytes=raw_bytes,
            title=title,
            source_reference=source_reference,
            trust_level=trust_level,
            ttl_days=ttl_days,
        )
        return res
    except ValueError as ve:
        raise HTTPException(status_code=400, detail=str(ve))


@router.post("/knowledge/ingest-text")
def api_ingest_knowledge_text(payload: KnowledgeTextIngestSchema, db: Session = Depends(get_db)):
    if not is_permission_enabled(db, "file_access"):
        raise HTTPException(status_code=403, detail="Permission 'file_access' is currently disabled.")

    ext_map = {"TXT": ".txt", "MD": ".md", "JSON": ".json"}
    ext = ext_map.get(payload.file_type.upper(), ".txt")
    filename = f"{payload.title.strip().replace(' ', '_')[:40]}{ext}"

    try:
        return ingest_document(
            db=db,
            filename=filename,
            raw_bytes=payload.content.encode("utf-8"),
            title=payload.title,
            source_reference=payload.source_reference,
            trust_level=payload.trust_level,
            ttl_days=payload.ttl_days,
            chunk_size=payload.chunk_size,
        )
    except ValueError as ve:
        raise HTTPException(status_code=400, detail=str(ve))


@router.get("/knowledge/search")
def api_search_knowledge(
    query: str = Query(...),
    top_k: int = Query(5, ge=1, le=30),
    include_expired: bool = Query(False),
    db: Session = Depends(get_db),
):
    chunks = search_knowledge_chunks(
        db=db,
        query=query,
        top_k=top_k,
        include_expired=include_expired,
    )
    return {
        "success": True,
        "count": len(chunks),
        "results": chunks,
    }


# ==============================================================================
# 9. PERMISSIONS & SECURITY ENDPOINTS
# ==============================================================================

@router.get("/permissions")
def api_get_permissions(db: Session = Depends(get_db)):
    return {
        "success": True,
        "permissions": get_all_permissions(db),
    }


@router.post("/permissions/update")
def api_update_permission(payload: PermissionUpdateSchema, db: Session = Depends(get_db)):
    try:
        updated = update_permission_scope(
            db=db,
            scope_name=payload.scope_name,
            enabled=payload.enabled,
            requires_human_approval=payload.requires_human_approval,
            actor=payload.actor,
        )
        return {
            "success": True,
            "permission": updated,
            "message": f"Permission scope '{payload.scope_name}' updated.",
        }
    except ValueError as ve:
        raise HTTPException(status_code=404, detail=str(ve))


@router.post("/permissions/backup")
def api_create_backup(label: str = Query("manual_snapshot"), db: Session = Depends(get_db)):
    return create_adaptive_backup_snapshot(db, label=label)
