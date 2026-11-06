import os
import sys
import json
import time
import sqlite3
import requests

sys.stdout.reconfigure(encoding='utf-8')

API_BASE = "http://127.0.0.1:8000"
DB_PATH = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "edith_ai.db"))

results = {
    "test_name": "TARS-001 — Persistent Learning Verification",
    "timestamp": time.strftime("%Y-%m-%d %H:%M:%S"),
    "steps": {}
}

def log_step(step_key, step_title, passed, details):
    results["steps"][step_key] = {
        "title": step_title,
        "passed": passed,
        "details": details
    }
    status_icon = "PASSED" if passed else "FAILED"
    print(f"[{status_icon}] {step_key}: {step_title}")

print("=== Starting Acceptance Test TARS-001 ===")

# ------------------------------------------------------------------------------
# STEP 1: Inspect actual execution files and database
# ------------------------------------------------------------------------------
conn = sqlite3.connect(DB_PATH)
cursor = conn.cursor()
cursor.execute("SELECT name FROM sqlite_master WHERE type='table' AND name LIKE 'tars_%';")
tars_tables = [row[0] for row in cursor.fetchall()]
conn.close()

step1_passed = "tars_memories" in tars_tables and "tars_learning_records" in tars_tables and "tars_improvement_proposals" in tars_tables
log_step("STEP_1", "Inspect database tables and live execution files", step1_passed, {
    "db_path": DB_PATH,
    "tars_tables_found": tars_tables,
})

# ------------------------------------------------------------------------------
# STEP 2 & 3 & 4: Ingest new knowledge with auto_verify=False -> verify NOT approved before test
# ------------------------------------------------------------------------------
unique_tag = f"TEST_ISOLATION_{int(time.time())}"
test_subject = f"Antigravity Propulsion Subsystem ({unique_tag})"
test_raw_input = (
    f"The Antigravity Propulsion Subsystem ({unique_tag}) utilizes a tri-phase gravimetric oscillator "
    f"operating at 1.42 GHz with superconducting yttrium barium copper oxide coils."
)

ingest_res = requests.post(f"{API_BASE}/tars/learning/ingest", json={
    "raw_input": test_raw_input,
    "subject_hint": test_subject,
    "source_type": "document",
    "source_reference": f"acceptance_test_doc_{unique_tag}",
    "auto_verify": False
})

ingest_data = ingest_res.json()
learning_uid = ingest_data.get("learning_record", {}).get("learning_uid")
cand_mem_uid = ingest_data.get("learning_record", {}).get("candidate_memory_uid")
status_before_test = ingest_data.get("learning_record", {}).get("approval_status")
pipeline_step_before = ingest_data.get("pipeline_step_reached")

# Verify in DB directly before verification test
conn = sqlite3.connect(DB_PATH)
cursor = conn.cursor()
cursor.execute("SELECT approval_status, pipeline_step, verification_passed FROM tars_learning_records WHERE learning_uid=?", (learning_uid,))
db_lr_row = cursor.fetchone()
cursor.execute("SELECT user_approved, is_verified_fact, fact_or_inference FROM tars_memories WHERE memory_uid=?", (cand_mem_uid,))
db_mem_row = cursor.fetchone()
conn.close()

step2_passed = (
    status_before_test == "PENDING_TEST" and
    pipeline_step_before == 6 and
    db_lr_row[0] == "PENDING_TEST" and
    db_lr_row[2] == 0 and # verification_passed is False
    db_mem_row[0] == 0 and # user_approved is False
    db_mem_row[1] == 0     # is_verified_fact is False
)

log_step("STEP_2_4", "Verify 8-Step pipeline stages knowledge at Step 6 and BLOCKS approval before testing", step2_passed, {
    "learning_uid": learning_uid,
    "candidate_memory_uid": cand_mem_uid,
    "api_approval_status": status_before_test,
    "api_pipeline_step": pipeline_step_before,
    "db_learning_record": {
        "approval_status": db_lr_row[0] if db_lr_row else None,
        "pipeline_step": db_lr_row[1] if db_lr_row else None,
        "verification_passed": bool(db_lr_row[2]) if db_lr_row else None
    },
    "db_candidate_memory": {
        "user_approved": bool(db_mem_row[0]) if db_mem_row else None,
        "is_verified_fact": bool(db_mem_row[1]) if db_mem_row else None,
        "fact_or_inference": db_mem_row[2] if db_mem_row else None
    }
})

# ------------------------------------------------------------------------------
# STEP 4 (continued): Execute Verification Test (Step 7 & 8) -> verify it transitions to APPROVED
# ------------------------------------------------------------------------------
verify_res = requests.post(f"{API_BASE}/tars/learning/verify/{learning_uid}", json={
    "candidate_answer": test_raw_input,
    "pass_threshold": 0.75
})
verify_data = verify_res.json()
verified_passed = verify_data.get("verification_passed") is True
verified_status = verify_data.get("learning_record", {}).get("approval_status")
verified_score = verify_data.get("verification_score")

# Verify candidate memory is now approved in DB
conn = sqlite3.connect(DB_PATH)
cursor = conn.cursor()
cursor.execute("SELECT approval_status, verification_score, verification_passed, pipeline_step FROM tars_learning_records WHERE learning_uid=?", (learning_uid,))
db_lr_post = cursor.fetchone()
cursor.execute("SELECT user_approved, is_verified_fact, fact_or_inference FROM tars_memories WHERE memory_uid=?", (cand_mem_uid,))
db_mem_post = cursor.fetchone()
conn.close()

step4_passed = (
    verified_passed and
    verified_status == "APPROVED" and
    db_lr_post[0] == "APPROVED" and
    db_lr_post[2] == 1 and
    db_lr_post[3] == 8 and # Reached step 8
    db_mem_post[0] == 1 and # user_approved is True
    db_mem_post[1] == 1 and # is_verified_fact is True
    db_mem_post[2] == "FACT"
)

log_step("STEP_4_APPROVAL", "Verify passing the test advances pipeline to Step 8 and APPROVES the knowledge in DB", step4_passed, {
    "verification_score": verified_score,
    "verification_passed": verified_passed,
    "db_learning_post": {
        "status": db_lr_post[0],
        "score": db_lr_post[1],
        "passed": bool(db_lr_post[2]),
        "pipeline_step": db_lr_post[3]
    },
    "db_memory_post": {
        "user_approved": bool(db_mem_post[0]),
        "is_verified_fact": bool(db_mem_post[1]),
        "fact_or_inference": db_mem_post[2]
    }
})

# ------------------------------------------------------------------------------
# STEP 5: Verify persistent database storage before restart
# ------------------------------------------------------------------------------
conn = sqlite3.connect(DB_PATH)
cursor = conn.cursor()
cursor.execute("SELECT count(*) FROM tars_memories WHERE subject=?", (test_subject,))
count_before_restart = cursor.fetchone()[0]
conn.close()

step5_passed = count_before_restart == 1
log_step("STEP_5", "Verify knowledge is stored persistently in database tables before restart", step5_passed, {
    "rows_found_in_db": count_before_restart
})

# Save state for step 6 & 7
with open("tests/tars_001_state.json", "w", encoding="utf-8") as f:
    json.dump({
        "unique_tag": unique_tag,
        "test_subject": test_subject,
        "test_raw_input": test_raw_input,
        "learning_uid": learning_uid,
        "cand_mem_uid": cand_mem_uid,
        "results": results
    }, f, indent=2)

print("Pre-restart verification complete. Ready for Backend restart.")
