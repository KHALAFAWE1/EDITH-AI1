import os
import sys
import json
import time
import requests

sys.stdout.reconfigure(encoding='utf-8')

API_BASE = "http://127.0.0.1:8000"

with open("tests/tars_004_state.json", "r", encoding="utf-8") as f:
    state = json.load(f)

NAMESPACE = state["namespace"]
pre_results = state["pre_results"]
robustness_results = state["robustness_results"]
dim_f_passed = state["dim_f_passed"]

print(f"=== Running Post-Restart Verification for TARS-004 (Namespace: {NAMESPACE}) ===")

# Verify server connectivity
try:
    stats_res = requests.get(f"{API_BASE}/tars/memory/stats")
    if stats_res.status_code != 200:
        print(f"[FATAL] Server offline: HTTP {stats_res.status_code}")
        sys.exit(1)
    print(f"Server is LIVE. Total memories: {stats_res.json().get('total_memories')}")
except Exception as e:
    print(f"[FATAL] Connection error: {e}")
    sys.exit(1)

# Import battery executor
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from run_acceptance_tars_004 import execute_evaluation_battery

post_results = execute_evaluation_battery(NAMESPACE)

# Check Post-Restart Consistency
consistency_matches = 0
for pre, post in zip(pre_results, post_results):
    pre_top = pre.get("retrieved_subject")
    post_top = post.get("retrieved_subject")
    if pre_top == post_top:
        consistency_matches += 1

post_restart_consistency = consistency_matches / len(pre_results) if pre_results else 1.0

# Metric Calculations across all Dimensions
standard_queries = [r for r in post_results if r["dimension"] in ("A_exact", "B_paraphrase", "C_disambiguation", "G_trust")]
unknown_queries = [r for r in post_results if r["dimension"] == "E_unknown"]
generic_queries = [r for r in post_results if r["dimension"] == "D_generic"]
disambig_queries = [r for r in post_results if r["dimension"] == "C_disambiguation"]

# Top-1, Top-3, Recall@5, MRR
top1_count = sum(1 for r in standard_queries if r.get("top1_match"))
top3_count = sum(1 for r in standard_queries if r.get("top3_match"))
top5_count = sum(1 for r in standard_queries if r.get("top5_match"))

top1_accuracy = top1_count / len(standard_queries) if standard_queries else 0.0
top3_accuracy = top3_count / len(standard_queries) if standard_queries else 0.0
recall_at_5 = top5_count / len(standard_queries) if standard_queries else 0.0

reciprocal_ranks = []
for r in standard_queries:
    rank = r.get("rank")
    reciprocal_ranks.append(1.0 / rank if rank else 0.0)
mrr = sum(reciprocal_ranks) / len(reciprocal_ranks) if reciprocal_ranks else 0.0

# Language breakdowns
en_queries = [r for r in standard_queries if r.get("lang") == "en"]
ar_queries = [r for r in standard_queries if r.get("lang") == "ar"]
cross_queries = [r for r in standard_queries if r.get("lang") == "cross"]

en_acc = sum(1 for r in en_queries if r.get("top1_match")) / len(en_queries) if en_queries else 0.0
ar_acc = sum(1 for r in ar_queries if r.get("top1_match")) / len(ar_queries) if ar_queries else 0.0
cross_acc = sum(1 for r in cross_queries if r.get("top1_match")) / len(cross_queries) if cross_queries else 0.0

# Entity collision rate (Sibling queries where wrong sibling ranked #1)
collision_count = 0
for r in disambig_queries:
    if not r.get("forbidden_avoided") or not r.get("top1_match"):
        collision_count += 1
entity_collision_rate = collision_count / len(disambig_queries) if disambig_queries else 0.0

# Unknown rejection rate & False retrieval rate
unknown_rejected_count = sum(1 for r in unknown_queries if r.get("passed"))
unknown_rejection_rate = unknown_rejected_count / len(unknown_queries) if unknown_queries else 0.0
false_retrieval_rate = 1.0 - unknown_rejection_rate

# Provenance accuracy
trust_queries = [r for r in post_results if r["dimension"] == "G_trust"]
prov_count = sum(1 for r in trust_queries if r.get("provenance_intact"))
prov_accuracy = prov_count / len(trust_queries) if trust_queries else 0.0

# Conflict detection accuracy
conflict_accuracy = 1.0 if dim_f_passed else 0.0

# Robustness accuracy
rob_accuracy = sum(1 for r in robustness_results if r["passed"]) / len(robustness_results) if robustness_results else 0.0

# Remaining failure cases
failures = []
for r in post_results:
    if not r.get("passed"):
        failures.append({
            "id": r["id"],
            "dimension": r["dimension"],
            "query": r["query"],
            "expected": r.get("expected_subject") or r.get("expected_candidates"),
            "retrieved": r.get("retrieved_subject") or r.get("retrieved_subjects"),
            "rank": r.get("rank"),
            "reason": "Cross-lingual zero-lexical token overlap" if r.get("lang") == "cross" else "Candidate ranking mismatch"
        })

# Full report structure
full_report = {
    "test_name": "TARS-004 — Generalization & Reliability Acceptance Test",
    "namespace": NAMESPACE,
    "timestamp": time.strftime("%Y-%m-%d %H:%M:%S"),
    "domains": [
        "1. Networking and cybersecurity",
        "2. General computing",
        "3. Education and science",
        "4. General knowledge",
        "5. Robotics and hardware",
        "6. Arabic and English mixed-language queries"
    ],
    "metrics": {
        "top_1_accuracy": round(top1_accuracy, 4),
        "top_3_accuracy": round(top3_accuracy, 4),
        "recall_at_5": round(recall_at_5, 4),
        "mean_reciprocal_rank_mrr": round(mrr, 4),
        "english_retrieval_accuracy": round(en_acc, 4),
        "arabic_retrieval_accuracy": round(ar_acc, 4),
        "cross_language_retrieval_accuracy": round(cross_acc, 4),
        "entity_collision_rate": round(entity_collision_rate, 4),
        "false_retrieval_rate": round(false_retrieval_rate, 4),
        "unknown_question_rejection_rate": round(unknown_rejection_rate, 4),
        "conflict_detection_accuracy": round(conflict_accuracy, 4),
        "provenance_accuracy": round(prov_accuracy, 4),
        "post_restart_consistency": round(post_restart_consistency, 4),
        "robustness_pass_rate": round(rob_accuracy, 4)
    },
    "comparison_with_tars_003": {
        "domain_coverage": {
            "tars_003": "Aerospace and space hardware only",
            "tars_004": "6 General Domains (Networking, Computing, Science, General, Robotics, Mixed AR/EN)"
        },
        "sibling_collision_rate": {
            "tars_003": 0.0,
            "tars_004": round(entity_collision_rate, 4),
            "note": "Evaluated across IT nodes, network interfaces, and manipulator joints"
        },
        "arabic_retrieval_accuracy": {
            "tars_003": "N/A (English only)",
            "tars_004": f"{ar_acc*100:.1f}%"
        },
        "cross_language_accuracy": {
            "tars_003": "N/A",
            "tars_004": f"{cross_acc*100:.1f}% (Identified failure mode for offline n-gram model)"
        },
        "unknown_rejection_rate": {
            "tars_003": 1.0,
            "tars_004": round(unknown_rejection_rate, 4)
        },
        "post_restart_consistency": {
            "tars_003": 1.0,
            "tars_004": round(post_restart_consistency, 4)
        }
    },
    "post_restart_results": post_results,
    "robustness_checks": robustness_results,
    "remaining_failures": failures,
    "overall_status": "PASSED" if (top1_accuracy >= 0.85 and unknown_rejection_rate >= 0.90 and post_restart_consistency == 1.0) else "COMPLETED_WITH_FINDINGS"
}

with open("tests/tars_004_full_report.json", "w", encoding="utf-8") as f:
    json.dump(full_report, f, indent=2, ensure_ascii=False)

print("\n" + "=" * 65)
print(f"TARS-004 Acceptance Suite Complete: Status = {full_report['overall_status']}")
print("=" * 65)
print(f"• Top-1 Accuracy:                          {top1_accuracy * 100:.1f}%")
print(f"• Top-3 Accuracy:                          {top3_accuracy * 100:.1f}%")
print(f"• Recall@5:                                {recall_at_5 * 100:.1f}%")
print(f"• Mean Reciprocal Rank (MRR):              {mrr:.4f}")
print(f"• English Retrieval Accuracy:              {en_acc * 100:.1f}%")
print(f"• Arabic Retrieval Accuracy:               {ar_acc * 100:.1f}%")
print(f"• Cross-Language Accuracy (AR <-> EN):     {cross_acc * 100:.1f}%")
print(f"• Entity Collision Rate:                   {entity_collision_rate * 100:.1f}%")
print(f"• Unknown-Question Rejection Rate:         {unknown_rejection_rate * 100:.1f}%")
print(f"• Conflict Detection Accuracy:             {conflict_accuracy * 100:.1f}%")
print(f"• Provenance Accuracy:                     {prov_accuracy * 100:.1f}%")
print(f"• Post-Restart Consistency:                {post_restart_consistency * 100:.1f}%")
print(f"• Robustness Checks Pass Rate:             {rob_accuracy * 100:.1f}%")
print(f"• Total Remaining Failure Cases:           {len(failures)}")
print("=" * 65)
