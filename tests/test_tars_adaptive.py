import io
import os
import sys
import zipfile

import pytest
from fastapi.testclient import TestClient

ROOT_DIR = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
SERVER_DIR = os.path.join(ROOT_DIR, "server")
if SERVER_DIR not in sys.path:
    sys.path.insert(0, SERVER_DIR)

from app.main import app  # noqa: E402

client = TestClient(app)


def _build_minimal_docx_bytes(paragraphs):
    """Builds a valid OpenXML .docx file in memory for testing DOCX ingestion."""
    buf = io.BytesIO()
    body_xml = "".join(
        f"<w:p><w:r><w:t>{p}</w:t></w:r></w:p>" for p in paragraphs
    )
    doc_xml = (
        '<?xml version="1.0" encoding="UTF-8" standalone="yes"?>'
        '<w:document xmlns:w="http://schemas.openxmlformats.org/wordprocessingml/2006/main">'
        f"<w:body>{body_xml}</w:body></w:document>"
    )
    with zipfile.ZipFile(buf, "w", zipfile.ZIP_DEFLATED) as zf:
        zf.writestr("word/document.xml", doc_xml.encode("utf-8"))
    return buf.getvalue()


def _build_minimal_pdf_bytes(text_content: str) -> bytes:
    """Builds a minimal PDF stream containing parenthesized text tokens."""
    pdf_str = (
        "%PDF-1.4\n"
        "1 0 obj << /Type /Catalog /Pages 2 0 R >> endobj\n"
        "2 0 obj << /Type /Pages /Kids [3 0 R] /Count 1 >> endobj\n"
        "3 0 obj << /Type /Page /Parent 2 0 R /Contents 4 0 R >> endobj\n"
        f"4 0 obj << /Length {len(text_content) + 20} >>\n"
        "stream\n"
        f"BT /F1 12 Tf 72 712 Td ({text_content}) Tj ET\n"
        "endstream\n"
        "endobj\n"
        "%%EOF\n"
    )
    return pdf_str.encode("latin-1", errors="ignore")


def test_1_hybrid_ai_core_and_model_router():
    """Tests Hybrid AI Core status, routing policy switching, fallback, and routing logs."""
    status_res = client.get("/tars/core/status")
    assert status_res.status_code == 200
    data = status_res.json()
    assert data["success"] is True
    assert "providers" in data
    assert "routing_config" in data

    # Update routing policy to LOCAL_ONLY and verify chat routes locally and logs reason
    cfg_res = client.post("/tars/core/routing-config", json={"routing_policy": "LOCAL_ONLY"})
    assert cfg_res.status_code == 200
    assert cfg_res.json()["routing_config"]["routing_policy"] == "LOCAL_ONLY"

    chat_res = client.post("/ai/chat", json={"prompt": "What is the current CPU and RAM telemetry status?"})
    assert chat_res.status_code == 200
    chat_data = chat_res.json()
    assert "routing" in chat_data
    assert chat_data["routing"]["routing_policy"] == "LOCAL_ONLY"
    assert chat_data["routing"]["routing_reason"] != ""

    # Restore HYBRID_AUTO
    client.post("/tars/core/routing-config", json={"routing_policy": "HYBRID_AUTO"})

    logs_res = client.get("/tars/core/routing-logs?limit=5")
    assert logs_res.status_code == 200
    assert logs_res.json()["count"] >= 1


def test_2_memory_system_crud_dedup_and_privacy():
    """Tests Short-Term, Long-Term, Episodic, and Semantic memory, deduplication, fact vs inference, and sensitive guard."""
    # 1. Sensitive data must be blocked without explicit consent
    sens_res = client.post(
        "/tars/memory",
        json={
            "subject": "secret_test",
            "content": "My secret key is AIzaSyD1234567890abcdefghijklmnopqrstuv",
            "memory_type": "LONG_TERM",
            "allow_sensitive": False,
        },
    )
    assert sens_res.status_code == 200
    assert sens_res.json()["success"] is False
    assert sens_res.json()["blocked_sensitive"] is True

    # 2. Store a verified LONG_TERM fact
    unique_fact = "TARS orbital navigation module operates at 60Hz frequency in sector 7."
    create_res = client.post(
        "/tars/memory",
        json={
            "subject": "orbital_navigation_spec",
            "content": unique_fact,
            "memory_type": "LONG_TERM",
            "category": "project",
            "is_verified_fact": True,
            "fact_or_inference": "FACT",
            "source_type": "conversation",
        },
    )
    assert create_res.status_code == 200
    c_json = create_res.json()
    assert c_json["success"] is True
    mem_uid = c_json["memory"]["memory_uid"]
    assert c_json["memory"]["fact_or_inference"] == "FACT"

    # 3. Storing the exact same memory again must trigger deduplication
    dup_res = client.post(
        "/tars/memory",
        json={
            "subject": "orbital_navigation_spec",
            "content": unique_fact,
            "memory_type": "LONG_TERM",
        },
    )
    assert dup_res.status_code == 200
    assert dup_res.json()["deduplicated"] is True

    # 4. Semantic search retrieves the memory
    search_res = client.get("/tars/memory", params={"query": "orbital navigation frequency sector 7"})
    assert search_res.status_code == 200
    hits = search_res.json()["memories"]
    assert any(m["memory_uid"] == mem_uid for m in hits)

    # 5. Update memory
    upd_res = client.put(
        f"/tars/memory/{mem_uid}",
        json={"content": "TARS orbital navigation module operates at 120Hz frequency in sector 7."},
    )
    assert upd_res.status_code == 200
    assert "120Hz" in upd_res.json()["memory"]["content"]

    # 6. Episodic memory recording
    ep_res = client.post(
        "/tars/memory/episodic",
        json={
            "what_user_asked": "Run diagnostics on optical array",
            "what_tars_did": "Executed optical calibration check",
            "result_summary": "All 512D biometric vectors nominal",
            "error_occurred": "None",
            "lesson_extracted": "Verify lighting before ArcFace extraction",
        },
    )
    assert ep_res.status_code == 200
    assert ep_res.json()["memory"]["memory_type"] == "EPISODIC"

    # 7. Delete memory
    del_res = client.delete(f"/tars/memory/{mem_uid}")
    assert del_res.status_code == 200
    assert del_res.json()["deleted_uid"] == mem_uid


def test_3_learning_engine_8_step_pipeline_and_verification_gate():
    """
    Verifies that TARS ONLY marks knowledge as APPROVED/learned when the verification test passes,
    and REJECTS it when the verification test fails.
    """
    # 1. Valid knowledge that passes automatic retrieval verification test
    pass_res = client.post(
        "/tars/learning/ingest",
        json={
            "raw_input": "ArcFace buffalo_l generates 512-dimensional normalized facial embeddings for biometric matching.",
            "subject_hint": "ArcFace Embedding Dimension",
            "source_type": "document",
            "auto_verify": True,
        },
    )
    assert pass_res.status_code == 200
    p_data = pass_res.json()
    assert p_data["learned"] is True
    assert p_data["verification_passed"] is True
    assert p_data["learning_record"]["approval_status"] == "APPROVED"
    assert p_data["pipeline_step_reached"] == 8

    # 2. Knowledge test that FAILS verification must be REJECTED (not learned)
    fail_res = client.post(
        "/tars/learning/ingest",
        json={
            "raw_input": "Quantum telemetry link uses protocol X-99 on port 8443.",
            "subject_hint": "Quantum Telemetry Protocol",
            "source_type": "conversation",
            "auto_verify": True,
            "simulated_answer_override": "I have no idea about bananas and oranges.",
        },
    )
    assert fail_res.status_code == 200
    f_data = fail_res.json()
    assert f_data["learned"] is False
    assert f_data["verification_passed"] is False
    assert f_data["learning_record"]["approval_status"] == "REJECTED"


def test_4_experience_and_feedback_system():
    """Tests storing all 13 mandatory experience fields, adding human feedback, and retrieving similar experiences."""
    exp_res = client.post(
        "/tars/experiences",
        json={
            "task_description": "Calibrate low-light camera exposure for face recognition",
            "input_text": "Camera frame is too dark to detect faces",
            "context": {"ambient_lux": 12, "camera_id": 0},
            "actions_taken": ["increase_gain", "apply_clahe_histogram"],
            "tools_used": ["opencv_clahe", "insightface_buffalo_l"],
            "expected_result": "Detect face with > 0.75 confidence",
            "actual_result": "Detected face with 0.89 confidence after CLAHE",
            "evaluation_score": 0.92,
            "errors": "None",
            "human_feedback": "Excellent recovery in dark room",
            "lessons_extracted": "Apply CLAHE histogram equalization when ambient brightness is low",
            "approval_status": "APPROVED",
        },
    )
    assert exp_res.status_code == 200
    exp_obj = exp_res.json()["experience"]
    exp_id = exp_obj["experience_id"]

    # Check all 13 required fields are present
    for field in (
        "experience_id",
        "task_description",
        "input_text",
        "context",
        "actions_taken",
        "tools_used",
        "expected_result",
        "actual_result",
        "evaluation_score",
        "errors",
        "human_feedback",
        "lessons_extracted",
        "approval_status",
    ):
        assert field in exp_obj

    # Add operator feedback and promote lesson to long-term memory
    fb_res = client.post(
        f"/tars/experiences/{exp_id}/feedback",
        json={
            "human_feedback": "Always check frame brightness before running ArcFace.",
            "evaluation_score": 0.98,
            "promote_to_long_term_memory": True,
        },
    )
    assert fb_res.status_code == 200
    assert fb_res.json()["experience"]["evaluation_score"] == 0.98

    # Retrieve similar experiences
    sim_res = client.get("/tars/experiences", params={"query": "dark camera frame face recognition"})
    assert sim_res.status_code == 200
    assert sim_res.json()["count"] >= 1


def test_5_evaluation_engine_and_sandbox():
    """Tests sandboxed code execution, blocking unsafe imports, and regression detection."""
    # 1. Safe code passes sandbox
    safe_res = client.post(
        "/tars/evaluation/sandbox-test",
        json={
            "code_snippet": "def add(x, y):\n    return x + y",
            "test_assertion": "assert add(19, 23) == 42",
        },
    )
    assert safe_res.status_code == 200
    assert safe_res.json()["sandbox_result"]["passed"] is True

    # 2. Unsafe import (subprocess) is blocked by sandbox AST guard
    unsafe_res = client.post(
        "/tars/evaluation/sandbox-test",
        json={
            "code_snippet": "import subprocess\nsubprocess.run(['echo', 'hack'])",
            "test_assertion": "",
        },
    )
    assert unsafe_res.status_code == 200
    assert unsafe_res.json()["sandbox_result"]["passed"] is False
    assert unsafe_res.json()["sandbox_result"].get("blocked_by_sandbox") is True

    # 3. Run comprehensive evaluation suite
    run1 = client.post("/tars/evaluation/run", json={"eval_type": "regression_test_suite"})
    assert run1.status_code == 200
    assert run1.json()["evaluation"]["overall_score"] >= 0.0


def test_6_controlled_self_improvement_approval_gate():
    """
    Verifies that TARS ImprovementProposals cannot be applied without human approval,
    and can be tested, approved, applied, and rolled back safely.
    """
    prop_res = client.post(
        "/tars/improvements",
        json={
            "title": "Optimize semantic vector cache lookup",
            "problem_description": "Repeated identical queries recompute embeddings.",
            "proposed_solution": "Add LRU cache on normalize_text + compute_semantic_embedding.",
            "action_category": "modify_project_code",
            "affected_files": ["server/app/services/memory_service.py"],
        },
    )
    assert prop_res.status_code == 200
    prop_id = prop_res.json()["proposal"]["proposal_id"]

    # 1. Attempting to apply BEFORE human approval MUST be blocked (HTTP 403)
    unapproved_apply = client.post(f"/tars/improvements/{prop_id}/apply")
    assert unapproved_apply.status_code == 403

    # 2. Test in isolated sandbox
    test_res = client.post(
        f"/tars/improvements/{prop_id}/test",
        json={
            "code_snippet": "cache = {}\ndef cached_double(x):\n    return cache.setdefault(x, x * 2)",
            "test_assertion": "assert cached_double(21) == 42 and 21 in cache",
        },
    )
    assert test_res.status_code == 200
    assert test_res.json()["proposal"]["isolated_test_passed"] is True
    assert test_res.json()["proposal"]["approval_status"] == "TESTED_AWAITING_APPROVAL"

    # 3. Still cannot apply before explicit human APPROVE decision
    still_unapproved = client.post(f"/tars/improvements/{prop_id}/apply")
    assert still_unapproved.status_code == 403

    # 4. Human operator approves proposal
    rev_res = client.post(
        f"/tars/improvements/{prop_id}/review",
        json={"decision": "APPROVE", "reviewed_by": "Commander_Cooper", "review_notes": "Verified in sandbox"},
    )
    assert rev_res.status_code == 200
    assert rev_res.json()["proposal"]["approval_status"] == "APPROVED"

    # 5. Apply approved proposal
    apply_res = client.post(f"/tars/improvements/{prop_id}/apply")
    assert apply_res.status_code == 200
    assert apply_res.json()["proposal"]["approval_status"] == "APPLIED"

    # 6. Rollback proposal
    rb_res = client.post(
        f"/tars/improvements/{prop_id}/rollback",
        json={"reason": "Testing rollback mechanism"},
    )
    assert rb_res.status_code == 200
    assert rb_res.json()["proposal"]["approval_status"] == "ROLLED_BACK"


def test_7_knowledge_acquisition_txt_docx_pdf_and_conflict_detection():
    """Tests ingesting TXT, DOCX, and PDF documents, chunk retrieval with citations, and conflict detection."""
    import uuid
    rnd = uuid.uuid4().hex[:6]

    # 1. Ingest TXT document
    txt_bytes = (
        f"TARS Reactor Core Manual {rnd}\n\n"
        f"The primary fusion reactor {rnd} operates at a nominal temperature of 350 Kelvin and outputs 450 MW of power."
    ).encode("utf-8")
    r_txt = client.post(
        "/tars/knowledge/upload",
        files={"file": (f"reactor_manual_{rnd}.txt", txt_bytes, "text/plain")},
        data={"title": f"TARS Reactor Core Manual {rnd}", "source_reference": f"spec_v1_{rnd}"},
    )
    assert r_txt.status_code == 200
    assert r_txt.json()["success"] is True

    # 2. Ingest DOCX document with a conflicting number on the same topic to verify conflict detection
    docx_bytes = _build_minimal_docx_bytes([
        f"TARS Reactor Core Addendum {rnd}",
        f"The primary fusion reactor {rnd} operates at a nominal temperature of 900 Kelvin and outputs 1200 MW of power.",
    ])
    r_docx = client.post(
        "/tars/knowledge/upload",
        files={"file": (f"reactor_addendum_{rnd}.docx", docx_bytes, "application/vnd.openxmlformats-officedocument.wordprocessingml.document")},
        data={"title": f"TARS Reactor Core Addendum {rnd}", "source_reference": f"spec_v2_{rnd}"},
    )
    assert r_docx.status_code == 200
    docx_data = r_docx.json()
    assert docx_data["success"] is True
    assert docx_data["document"]["file_type"] == "DOCX"
    assert len(docx_data["conflicts_detected"]) >= 1

    # 3. Ingest PDF document
    pdf_bytes = _build_minimal_pdf_bytes("TARS Endurance Docking Protocol requires magnetic lock engagement within 5 seconds.")
    r_pdf = client.post(
        "/tars/knowledge/upload",
        files={"file": ("docking_protocol.pdf", pdf_bytes, "application/pdf")},
        data={"title": "Endurance Docking Protocol", "source_reference": "nasa_flight_manual"},
    )
    assert r_pdf.status_code == 200
    assert r_pdf.json()["document"]["file_type"] == "PDF"

    # 4. Search knowledge chunks with citations
    search_res = client.get("/tars/knowledge/search", params={"query": "fusion reactor nominal temperature Kelvin"})
    assert search_res.status_code == 200
    results = search_res.json()["results"]
    assert len(results) >= 1
    assert "[Source:" in results[0]["citation"]


def test_8_training_dataset_preparation_and_permissions():
    """Tests dataset cleaning/deduplication/export, honest hardware status, permissions, and backup."""
    tr_status = client.get("/tars/training/status")
    assert tr_status.status_code == 200
    assert tr_status.json()["fine_tuning_executed"] is False

    # Prepare dataset with duplicate and noisy samples to verify cleaning & deduplication
    ds_res = client.post(
        "/tars/training/prepare-dataset",
        json={
            "dataset_name": "unit_test_dataset",
            "user_approved": True,
            "custom_samples": [
                {"instruction": "What is TARS honesty setting?", "input": "config", "output": "Default honesty is 90%."},
                {"instruction": "What is TARS honesty setting?", "input": "config", "output": "Default honesty is 90%."},  # duplicate
                {"instruction": "hi", "input": "", "output": "ok"},  # noisy/too short (< 5 chars)
            ],
        },
    )
    assert ds_res.status_code == 200
    ds_data = ds_res.json()["dataset"]
    assert ds_data["duplicates_removed"] >= 1
    assert ds_data["noisy_removed"] >= 1
    assert os.path.exists(ds_data["export_path"])

    # Check permissions and backup snapshot
    perm_res = client.get("/tars/permissions")
    assert perm_res.status_code == 200
    scopes = {p["scope_name"] for p in perm_res.json()["permissions"]}
    assert {
        "read_only",
        "memory_write",
        "file_access",
        "web_access",
        "tool_execution",
        "code_modification",
        "model_modification",
        "system_admin",
    }.issubset(scopes)

    bak_res = client.post("/tars/permissions/backup?label=pytest_snapshot")
    assert bak_res.status_code == 200
    assert bak_res.json()["success"] is True
    assert os.path.exists(bak_res.json()["filepath"])
