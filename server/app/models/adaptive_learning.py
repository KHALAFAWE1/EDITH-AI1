from datetime import datetime
from sqlalchemy import Column, Integer, String, Float, Boolean, Text, DateTime, ForeignKey
from app.database import Base


class MemoryRecord(Base):
    """
    TARS Hybrid Memory System:
    Supports SHORT_TERM, LONG_TERM, EPISODIC, and SEMANTIC memory types.
    Distinguishes verified facts from AI inferences, tracks source & timestamp,
    stores vector embeddings for semantic search, and prevents duplicate storage.
    """
    __tablename__ = "tars_memories"

    id = Column(Integer, primary_key=True, index=True)
    memory_uid = Column(String(64), unique=True, index=True, nullable=False)
    memory_type = Column(String(32), index=True, nullable=False)  # SHORT_TERM | LONG_TERM | EPISODIC | SEMANTIC
    category = Column(String(64), default="general", index=True)  # preference | project | person | fact | episode | concept
    subject = Column(String(200), index=True, nullable=False)
    content = Column(Text, nullable=False)
    content_hash = Column(String(64), index=True, nullable=False)

    # Fact vs. Inference distinction
    is_verified_fact = Column(Boolean, default=False)
    fact_or_inference = Column(String(20), default="INFERENCE")  # FACT | INFERENCE

    # Source & Confidence
    source_type = Column(String(64), default="conversation")  # conversation | document | experience | user_correction | test_result | reference
    source_reference = Column(String(255), default="user_session")
    confidence = Column(Float, default=0.8)

    # Semantic & Concept Relations (JSON strings)
    embedding_json = Column(Text, nullable=True)  # Normalized vector for cosine similarity
    concepts_json = Column(Text, default="[]")    # Related concepts / edges [{"target": "...", "relation": "..."}]
    metadata_json = Column(Text, default="{}")    # Episodic details or session id

    # Consent & Privacy
    user_approved = Column(Boolean, default=True)
    contains_sensitive = Column(Boolean, default=False)
    session_id = Column(String(64), index=True, default="default")

    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    expires_at = Column(DateTime, nullable=True)


class LearningRecord(Base):
    """
    TARS 8-Step Learning Pipeline Record:
    1. Receive info/experience -> 2. Classify type/source -> 3. Validate quality ->
    4. Extract knowledge -> 5. Store in candidate memory -> 6. Generate verification test ->
    7. Measure test score -> 8. Approve or reject knowledge.
    """
    __tablename__ = "tars_learning_records"

    id = Column(Integer, primary_key=True, index=True)
    learning_uid = Column(String(64), unique=True, index=True, nullable=False)
    source_type = Column(String(64), nullable=False)  # conversation | document | book | search | experience | correction | test
    source_reference = Column(String(255), default="")
    raw_input = Column(Text, nullable=False)
    quality_score = Column(Float, default=0.0)
    extracted_subject = Column(String(200), nullable=False)
    extracted_knowledge = Column(Text, nullable=False)
    fact_or_inference = Column(String(20), default="FACT")
    candidate_memory_uid = Column(String(64), nullable=True)

    # Verification test (Steps 6-8)
    verification_question = Column(Text, nullable=False)
    expected_answer = Column(Text, nullable=False)
    actual_answer = Column(Text, nullable=True)
    verification_score = Column(Float, default=0.0)
    verification_passed = Column(Boolean, default=False)
    pipeline_step = Column(Integer, default=1)  # 1..8
    approval_status = Column(String(32), default="PENDING_TEST")  # PENDING_TEST | APPROVED | REJECTED
    rejection_reason = Column(Text, nullable=True)

    created_at = Column(DateTime, default=datetime.utcnow)
    verified_at = Column(DateTime, nullable=True)


class ExperienceRecord(Base):
    """
    TARS Experience & Feedback System:
    Stores all 13 mandatory experience attributes so TARS can retrieve past similar
    experiences and avoid repeating errors.
    """
    __tablename__ = "tars_experiences"

    id = Column(Integer, primary_key=True, index=True)
    experience_id = Column(String(64), unique=True, index=True, nullable=False)
    task_description = Column(Text, nullable=False)
    input_text = Column(Text, nullable=False)
    context = Column(Text, default="{}")
    actions_taken = Column(Text, default="[]")
    tools_used = Column(Text, default="[]")
    expected_result = Column(Text, default="")
    actual_result = Column(Text, default="")
    evaluation_score = Column(Float, default=0.0)
    errors = Column(Text, default="None")
    human_feedback = Column(Text, default="")
    lessons_extracted = Column(Text, default="")
    approval_status = Column(String(32), default="APPROVED")  # PENDING | APPROVED | REJECTED

    embedding_json = Column(Text, nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)


class EvaluationRun(Base):
    """
    TARS Independent Evaluation Engine:
    Tests knowledge against trusted sources, runs isolated code checks, compares
    current performance against previous runs, and detects regression.
    """
    __tablename__ = "tars_evaluation_runs"

    id = Column(Integer, primary_key=True, index=True)
    eval_uid = Column(String(64), unique=True, index=True, nullable=False)
    eval_type = Column(String(64), default="comprehensive")  # comprehensive | source_accuracy | code_sandbox | regression
    total_tests = Column(Integer, default=0)
    passed_tests = Column(Integer, default=0)
    overall_score = Column(Float, default=0.0)
    previous_score = Column(Float, nullable=True)
    score_delta = Column(Float, default=0.0)
    regression_detected = Column(Boolean, default=False)
    task_success_rate = Column(Float, default=0.0)
    details_json = Column(Text, default="[]")
    report_summary = Column(Text, default="")
    created_at = Column(DateTime, default=datetime.utcnow)


class ImprovementProposal(Base):
    """
    TARS Improvement Manager (Controlled Self-Improvement):
    Proposes, tests in isolation, compares, and gates sensitive changes behind mandatory
    human approval with rollback support.
    """
    __tablename__ = "tars_improvement_proposals"

    id = Column(Integer, primary_key=True, index=True)
    proposal_id = Column(String(64), unique=True, index=True, nullable=False)
    title = Column(String(200), nullable=False)
    problem_description = Column(Text, nullable=False)
    proposed_solution = Column(Text, nullable=False)
    affected_files = Column(Text, default="[]")  # JSON list of files/components
    action_category = Column(String(64), nullable=False)
    # Categories: prompt_tuning | memory_optimization | modify_project_code | change_base_model |
    # fine_tune_model | change_model_weights | alter_database_schema | install_packages |
    # modify_permissions | execute_system_command | deploy_new_version
    risk_level = Column(String(20), default="MEDIUM")  # LOW | MEDIUM | HIGH | CRITICAL
    requires_human_approval = Column(Boolean, default=True)

    # Isolated testing & comparison
    isolated_test_executed = Column(Boolean, default=False)
    isolated_test_passed = Column(Boolean, default=False)
    test_results_json = Column(Text, default="{}")
    comparison_json = Column(Text, default="{}")  # Before vs. After metrics

    # Approval & Rollback state
    approval_status = Column(String(32), default="PENDING_APPROVAL")
    # PENDING_APPROVAL | TESTED_AWAITING_APPROVAL | APPROVED | APPLIED | REJECTED | ROLLED_BACK
    reviewed_by = Column(String(100), nullable=True)
    review_notes = Column(Text, nullable=True)
    rollback_snapshot_json = Column(Text, default="{}")

    created_at = Column(DateTime, default=datetime.utcnow)
    reviewed_at = Column(DateTime, nullable=True)


class KnowledgeDocument(Base):
    """
    TARS Knowledge Acquisition Module — Document Registry:
    Supports TXT, PDF, DOCX, MD, JSON files with source metadata, expiration tracking,
    and cross-source conflict detection.
    """
    __tablename__ = "tars_knowledge_documents"

    id = Column(Integer, primary_key=True, index=True)
    doc_uid = Column(String(64), unique=True, index=True, nullable=False)
    title = Column(String(255), nullable=False)
    filename = Column(String(255), nullable=False)
    file_type = Column(String(20), nullable=False)  # TXT | PDF | DOCX | MD | JSON
    source_reference = Column(String(255), default="uploaded_file")
    trust_level = Column(Float, default=0.9)
    total_chunks = Column(Integer, default=0)
    total_chars = Column(Integer, default=0)
    content_hash = Column(String(64), index=True, nullable=False)
    conflicts_json = Column(Text, default="[]")  # Detected contradictions with other sources
    expires_at = Column(DateTime, nullable=True)
    is_expired = Column(Boolean, default=False)
    created_at = Column(DateTime, default=datetime.utcnow)


class KnowledgeChunk(Base):
    """
    TARS Knowledge Acquisition Module — Chunked Passages for Citation & Vector Retrieval.
    """
    __tablename__ = "tars_knowledge_chunks"

    id = Column(Integer, primary_key=True, index=True)
    chunk_uid = Column(String(64), unique=True, index=True, nullable=False)
    doc_uid = Column(String(64), index=True, nullable=False)
    chunk_index = Column(Integer, default=0)
    heading = Column(String(255), default="")
    content = Column(Text, nullable=False)
    embedding_json = Column(Text, nullable=True)
    keywords_json = Column(Text, default="[]")
    created_at = Column(DateTime, default=datetime.utcnow)


class TrainingDatasetVersion(Base):
    """
    TARS Model Training & Fine-Tuning Readiness:
    Curates, cleans, deduplicates, versions, and exports approved JSONL datasets.
    """
    __tablename__ = "tars_training_datasets"

    id = Column(Integer, primary_key=True, index=True)
    dataset_version = Column(String(64), unique=True, index=True, nullable=False)
    name = Column(String(200), nullable=False)
    total_raw_records = Column(Integer, default=0)
    duplicates_removed = Column(Integer, default=0)
    noisy_removed = Column(Integer, default=0)
    clean_record_count = Column(Integer, default=0)
    export_path = Column(String(500), nullable=True)
    user_approved = Column(Boolean, default=False)
    quality_metrics_json = Column(Text, default="{}")
    created_at = Column(DateTime, default=datetime.utcnow)


class ModelVersionRecord(Base):
    """
    Tracks base models, adapter/LoRA readiness, and pre/post evaluation comparisons.
    """
    __tablename__ = "tars_model_versions"

    id = Column(Integer, primary_key=True, index=True)
    version_tag = Column(String(64), unique=True, index=True, nullable=False)
    provider_type = Column(String(32), nullable=False)  # LOCAL_OLLAMA | CLOUD_GEMINI | CLOUD_OPENAI | LOCAL_CORE
    base_model_name = Column(String(120), nullable=False)
    adapter_type = Column(String(32), default="NONE")  # NONE | LORA | PEFT | SYSTEM_PROMPT
    dataset_version = Column(String(64), nullable=True)
    pre_eval_score = Column(Float, default=0.0)
    post_eval_score = Column(Float, default=0.0)
    is_active = Column(Boolean, default=False)
    is_verified_trained = Column(Boolean, default=False)  # False unless actual training completed
    notes = Column(Text, default="")
    created_at = Column(DateTime, default=datetime.utcnow)


class PermissionScopeRecord(Base):
    """
    TARS Scoped Permissions:
    read_only, memory_write, file_access, web_access, tool_execution,
    code_modification, model_modification, system_admin
    """
    __tablename__ = "tars_permission_scopes"

    id = Column(Integer, primary_key=True, index=True)
    scope_name = Column(String(64), unique=True, index=True, nullable=False)
    enabled = Column(Boolean, default=False)
    requires_human_approval = Column(Boolean, default=True)
    description = Column(String(255), default="")
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)


class ModelRoutingLog(Base):
    """
    TARS Hybrid AI Core — Model Router Decision Log:
    Records every routing decision between Local AI Provider and Cloud AI Provider,
    including why the provider was chosen, fallback usage, and privacy checks.
    """
    __tablename__ = "tars_model_routing_logs"

    id = Column(Integer, primary_key=True, index=True)
    routing_uid = Column(String(64), unique=True, index=True, nullable=False)
    task_type = Column(String(64), nullable=False)  # chat | vision | telemetry | command | embedding | evaluation
    routing_policy = Column(String(32), default="HYBRID_AUTO")  # LOCAL_FIRST | CLOUD_FIRST | LOCAL_ONLY | HYBRID_AUTO
    provider_chosen = Column(String(64), nullable=False)  # LOCAL_OLLAMA | CLOUD_GEMINI | LOCAL_DETERMINISTIC
    model_name = Column(String(100), nullable=False)
    routing_reason = Column(Text, nullable=False)
    contains_private_data = Column(Boolean, default=False)
    privacy_redacted = Column(Boolean, default=False)
    fallback_triggered = Column(Boolean, default=False)
    latency_ms = Column(Float, default=0.0)
    success = Column(Boolean, default=True)
    created_at = Column(DateTime, default=datetime.utcnow)
