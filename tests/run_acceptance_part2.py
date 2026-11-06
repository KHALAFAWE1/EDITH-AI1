import os
import sys
import json
import time
import sqlite3
import requests

sys.stdout.reconfigure(encoding='utf-8')

API_BASE = "http://127.0.0.1:8000"
DB_PATH = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "edith_ai.db"))

with open("tests/tars_001_state.json", "r", encoding="utf-8") as f:
    state = json.load(f)

results = state["results"]
unique_tag = state["unique_tag"]
test_subject = state["test_subject"]
test_raw_input = state["test_raw_input"]
learning_uid = state["learning_uid"]
cand_mem_uid = state["cand_mem_uid"]

def log_step(step_key, step_title, passed, details):
    results["steps"][step_key] = {
        "title": step_title,
        "passed": passed,
        "details": details
    }
    status_icon = "PASSED" if passed else "FAILED"
    print(f"[{status_icon}] {step_key}: {step_title}")

print("=== Resuming Acceptance Test TARS-001 (Post-Restart & Edge Cases) ===")

# ------------------------------------------------------------------------------
# STEP 6 & 7 & 8: Verify persistence after restart and retrieve with different phrasing
# ------------------------------------------------------------------------------
# Phrasing 1: Ask via semantic memory query with completely different wording
differently_phrased_query = f"What oscillator frequency and coil materials does the {unique_tag} gravimetric propulsion use?"

search_res = requests.get(f"{API_BASE}/tars/memory", params={
    "query": differently_phrased_query,
    "top_k": 5
})
search_data = search_res.json()
hits = search_data.get("memories", [])

matched_hit = None
for h in hits:
    if unique_tag in h.get("content", "") or unique_tag in h.get("subject", ""):
        matched_hit = h
        break

step7_passed = (
    matched_hit is not None and
    "1.42 GHz" in matched_hit.get("content", "") and
    "yttrium barium copper oxide" in matched_hit.get("content", "") and
    matched_hit.get("is_verified_fact") is True and
    matched_hit.get("user_approved") is True
)

log_step("STEP_7_8", "Retrieve knowledge post-restart using differently phrased query and verify citations", step7_passed, {
    "differently_phrased_query": differently_phrased_query,
    "matched_memory_uid": matched_hit.get("memory_uid") if matched_hit else None,
    "matched_subject": matched_hit.get("subject") if matched_hit else None,
    "matched_content": matched_hit.get("content") if matched_hit else None,
    "is_verified_fact": matched_hit.get("is_verified_fact") if matched_hit else None,
    "source_type": matched_hit.get("source_type") if matched_hit else None,
    "source_reference": matched_hit.get("source_reference") if matched_hit else None,
    "similarity_score": matched_hit.get("similarity") if matched_hit else None,
})

# ------------------------------------------------------------------------------
# STEP 9: Test false / conflicting / low-quality knowledge -> ensure NOT approved
# ------------------------------------------------------------------------------
# Case A: Too short/noisy knowledge input
noisy_res = requests.post(f"{API_BASE}/tars/learning/ingest", json={
    "raw_input": "fake",
    "source_type": "conversation"
})
noisy_rejected = noisy_res.json().get("learned") is False and noisy_res.json().get("pipeline_step_reached") == 3

# Case B: False knowledge that fails verification quiz
false_input = f"The {unique_tag} reactor operates at zero energy and emits purple laser beams."
false_res = requests.post(f"{API_BASE}/tars/learning/ingest", json={
    "raw_input": false_input,
    "subject_hint": f"False Reactor Spec {unique_tag}",
    "source_type": "conversation",
    "auto_verify": True,
    "simulated_answer_override": "This completely contradicts verified physics."
})
false_data = false_res.json()
false_rejected = (
    false_data.get("learned") is False and
    false_data.get("verification_passed") is False and
    false_data.get("learning_record", {}).get("approval_status") == "REJECTED"
)

# Verify DB check on false knowledge
conn = sqlite3.connect(DB_PATH)
cursor = conn.cursor()
false_uid = false_data.get("learning_record", {}).get("learning_uid")
cursor.execute("SELECT approval_status, verification_passed FROM tars_learning_records WHERE learning_uid=?", (false_uid,))
db_false_lr = cursor.fetchone()
cursor.execute("SELECT user_approved, is_verified_fact FROM tars_memories WHERE subject=?", (f"False Reactor Spec {unique_tag}",))
db_false_mem = cursor.fetchone()
conn.close()

db_false_guarded = (
    db_false_lr[0] == "REJECTED" and
    db_false_lr[1] == 0 and
    (db_false_mem is None or (db_false_mem[0] == 0 and db_false_mem[1] == 0))
)

step9_passed = noisy_rejected and false_rejected and db_false_guarded
log_step("STEP_9", "Test false/conflicting/noisy knowledge and verify it is NEVER approved automatically", step9_passed, {
    "noisy_rejected": noisy_rejected,
    "false_rejected": false_rejected,
    "db_status": db_false_lr[0] if db_false_lr else None,
    "rejection_reason": false_data.get("learning_record", {}).get("rejection_reason")
})

# ------------------------------------------------------------------------------
# STEP 10: Test that rejecting an improvement proposal strictly prevents its application
# ------------------------------------------------------------------------------
# Create an improvement proposal
prop_res = requests.post(f"{API_BASE}/tars/improvements", json={
    "title": f"Acceptance Test Proposal {unique_tag}",
    "problem_description": "Testing rejection enforcement gate.",
    "proposed_solution": "Attempt applying after operator rejection.",
    "action_category": "modify_project_code",
    "affected_files": ["server/app/main.py"]
})
prop_data = prop_res.json().get("proposal", {})
prop_id = prop_data.get("proposal_id")

# Reject the proposal explicitly
reject_res = requests.post(f"{API_BASE}/tars/improvements/{prop_id}/review", json={
    "decision": "REJECT",
    "reviewed_by": "Flight_Director",
    "review_notes": "Rejected by security policy in acceptance test TARS-001."
})
rejected_status = reject_res.json().get("proposal", {}).get("approval_status")

# Attempt to apply the rejected proposal -> MUST be HTTP 403 Forbidden
apply_attempt = requests.post(f"{API_BASE}/tars/improvements/{prop_id}/apply")
apply_blocked = apply_attempt.status_code == 403

# Verify in DB
conn = sqlite3.connect(DB_PATH)
cursor = conn.cursor()
cursor.execute("SELECT approval_status, reviewed_by FROM tars_improvement_proposals WHERE proposal_id=?", (prop_id,))
db_prop = cursor.fetchone()
conn.close()

step10_passed = (
    rejected_status == "REJECTED" and
    apply_blocked and
    db_prop[0] == "REJECTED"
)

log_step("STEP_10", "Test that rejecting an improvement proposal strictly blocks application (HTTP 403)", step10_passed, {
    "proposal_id": prop_id,
    "review_status": rejected_status,
    "apply_http_status": apply_attempt.status_code,
    "apply_response_detail": apply_attempt.json().get("detail"),
    "db_proposal_status": db_prop[0] if db_prop else None
})

# Save full results report to JSON
with open("tests/tars_001_full_report.json", "w", encoding="utf-8") as f:
    json.dump(results, f, indent=2, ensure_ascii=False)

all_passed = all(s["passed"] for s in results["steps"].values())
print(f"\n=== OVERALL ACCEPTANCE RESULT: {'SUCCESS (ALL PASSED)' if all_passed else 'FAILURE'} ===")
