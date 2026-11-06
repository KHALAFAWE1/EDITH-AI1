import os
import sys
import json
import time
import requests

sys.stdout.reconfigure(encoding='utf-8')

API_BASE = "http://127.0.0.1:8000"
NAMESPACE = f"tars002_{int(time.time())}"

report_data = {
    "test_name": "TARS-002 — Memory Retrieval Quality & Provenance Test",
    "namespace": NAMESPACE,
    "timestamp": time.strftime("%Y-%m-%d %H:%M:%S"),
    "backup_taken": False,
    "sections": {},
    "metrics": {}
}

def log(section_name, passed, details):
    report_data["sections"][section_name] = {
        "passed": passed,
        "details": details
    }
    status = "PASSED" if passed else "FAILED"
    print(f"[{status}] {section_name}")

print(f"=== Starting TARS-002 Acceptance Test (Namespace: {NAMESPACE}) ===")

# ------------------------------------------------------------------------------
# 0. Create Backup Snapshot Before Any Mutation
# ------------------------------------------------------------------------------
try:
    bak_res = requests.post(f"{API_BASE}/tars/permissions/backup", params={"label": f"pre_{NAMESPACE}"})
    if bak_res.status_code == 200 and bak_res.json().get("success"):
        report_data["backup_taken"] = True
        report_data["backup_info"] = bak_res.json()
        print(f"[PASSED] Backup snapshot created: {bak_res.json().get('snapshot_id')}")
    else:
        print("[WARNING] Backup API returned non-success; proceeding with isolated namespace.")
except Exception as e:
    print(f"[WARNING] Backup error: {e}")

# ------------------------------------------------------------------------------
# 1. Insert Test Facts & 3. Collision Facts
# ------------------------------------------------------------------------------
facts = [
    {
        "id": "fact_1",
        "subject": f"{NAMESPACE}_alpha_thruster_coolant",
        "content": f"The {NAMESPACE} Alpha Thruster uses liquid methane coolant pressurized to 42 bar.",
        "category": "propulsion",
        "source_type": "document",
        "source_reference": f"doc_{NAMESPACE}_propulsion",
        "is_verified_fact": True
    },
    {
        "id": "fact_2",
        "subject": f"{NAMESPACE}_cryo_storage_temperature",
        "content": f"The {NAMESPACE} primary cryo-storage bay maintains a nominal temperature of 77 Kelvin.",
        "category": "storage",
        "source_type": "document",
        "source_reference": f"doc_{NAMESPACE}_storage",
        "is_verified_fact": True
    },
    {
        "id": "fact_3",
        "subject": f"{NAMESPACE}_baud_rate_comms",
        "content": f"The {NAMESPACE} deep-space communication array operates at an optical baud rate of 100 Gbps.",
        "category": "telecom",
        "source_type": "document",
        "source_reference": f"doc_{NAMESPACE}_telecom",
        "is_verified_fact": True
    },
    # Collision Pair: Very similar subject & vocabulary, but opposite side and different hardware
    {
        "id": "collision_port",
        "subject": f"{NAMESPACE}_attitude_sensor_port",
        "content": f"The {NAMESPACE} port-side attitude sensor uses laser gyroscope model LG-400 with 0.01 degree resolution.",
        "category": "guidance",
        "source_type": "document",
        "source_reference": f"doc_{NAMESPACE}_guidance_port",
        "is_verified_fact": True
    },
    {
        "id": "collision_starboard",
        "subject": f"{NAMESPACE}_attitude_sensor_starboard",
        "content": f"The {NAMESPACE} starboard-side attitude sensor uses star tracker model ST-900 with 0.002 degree resolution.",
        "category": "guidance",
        "source_type": "document",
        "source_reference": f"doc_{NAMESPACE}_guidance_starboard",
        "is_verified_fact": True
    }
]

created_memories = {}
for f in facts:
    res = requests.post(f"{API_BASE}/tars/memory", json={
        "subject": f["subject"],
        "content": f["content"],
        "category": f["category"],
        "memory_type": "LONG_TERM",
        "is_verified_fact": f["is_verified_fact"],
        "fact_or_inference": "FACT",
        "source_type": f["source_type"],
        "source_reference": f["source_reference"],
        "confidence": 0.95,
        "user_approved": True
    })
    data = res.json()
    created_memories[f["id"]] = data.get("memory", {})

print(f"Stored {len(created_memories)} isolated test facts in memory.")

# ------------------------------------------------------------------------------
# 4. Insert Contradictory Test Documents (Cross-Source Conflict)
# ------------------------------------------------------------------------------
doc1_text = (
    f"{NAMESPACE} Solar Array Specification Sheet Version 1\n\n"
    f"The {NAMESPACE} photovoltaic solar array generates a maximum output of 850 Kilowatts under direct solar flux."
)
doc2_text = (
    f"{NAMESPACE} Solar Array Field Modification Bulletin Version 2\n\n"
    f"The {NAMESPACE} photovoltaic solar array generates a maximum output of 250 Kilowatts under direct solar flux."
)

r_doc1 = requests.post(f"{API_BASE}/tars/knowledge/ingest-text", json={
    "title": f"{NAMESPACE}_solar_array_v1",
    "content": doc1_text,
    "source_reference": f"spec_{NAMESPACE}_revA",
    "trust_level": 0.90
})
r_doc2 = requests.post(f"{API_BASE}/tars/knowledge/ingest-text", json={
    "title": f"{NAMESPACE}_solar_array_v2",
    "content": doc2_text,
    "source_reference": f"bulletin_{NAMESPACE}_revB",
    "trust_level": 0.85
})

doc2_data = r_doc2.json()
conflicts_detected = doc2_data.get("conflicts_detected", [])
has_numeric_conflict = any(c.get("conflict_type") == "NUMERIC_DISCREPANCY" for c in conflicts_detected)
log("SECTION_4_CONFLICT_DETECTION", has_numeric_conflict, {
    "doc1_res": r_doc1.json().get("success"),
    "doc2_res": doc2_data.get("success"),
    "conflicts_count": len(conflicts_detected),
    "conflicts": conflicts_detected
})

# ------------------------------------------------------------------------------
# Test Evaluation Function (Runs before and after restart)
# ------------------------------------------------------------------------------
def run_evaluation_battery(run_label="pre_restart"):
    print(f"\n--- Running Evaluation Battery: {run_label} ---")
    battery_res = {
        "exact_retrieval": [],
        "paraphrased_retrieval": [],
        "similarity_collision": [],
        "contradictory_sources": [],
        "unknown_information": [],
        "provenance_checks": []
    }

    # 1. Exact Retrieval Queries
    exact_queries = [
        {
            "query": f"What coolant and pressure is used in {NAMESPACE} Alpha Thruster?",
            "expected_uid": created_memories["fact_1"]["memory_uid"],
            "expected_tokens": ["methane", "42 bar"],
            "expected_src_ref": f"doc_{NAMESPACE}_propulsion"
        },
        {
            "query": f"What is the nominal temperature of the {NAMESPACE} primary cryo-storage bay?",
            "expected_uid": created_memories["fact_2"]["memory_uid"],
            "expected_tokens": ["77", "kelvin"],
            "expected_src_ref": f"doc_{NAMESPACE}_storage"
        },
        {
            "query": f"What is the optical baud rate of the {NAMESPACE} deep-space communication array?",
            "expected_uid": created_memories["fact_3"]["memory_uid"],
            "expected_tokens": ["100", "gbps"],
            "expected_src_ref": f"doc_{NAMESPACE}_telecom"
        }
    ]

    for item in exact_queries:
        r = requests.get(f"{API_BASE}/tars/memory", params={"query": item["query"], "memory_type": "LONG_TERM", "top_k": 3})
        hits = r.json().get("memories", [])
        top1_hit = hits[0] if hits else None
        top1_match = bool(top1_hit and top1_hit["memory_uid"] == item["expected_uid"])
        top3_match = any(h["memory_uid"] == item["expected_uid"] for h in hits)
        battery_res["exact_retrieval"].append({
            "query": item["query"],
            "top1_match": top1_match,
            "top3_match": top3_match,
            "top1_uid": top1_hit.get("memory_uid") if top1_hit else None,
            "similarity": top1_hit.get("similarity") if top1_hit else 0.0
        })
        if top1_hit:
            battery_res["provenance_checks"].append({
                "query_type": "exact",
                "uid": top1_hit.get("memory_uid"),
                "source_type": top1_hit.get("source_type"),
                "source_ref": top1_hit.get("source_reference"),
                "expected_src_ref": item["expected_src_ref"],
                "has_correct_ref": top1_hit.get("source_reference") == item["expected_src_ref"],
                "is_verified_fact": top1_hit.get("is_verified_fact") is True,
                "similarity": top1_hit.get("similarity")
            })

    # 2. Paraphrased Retrieval Queries
    para_queries = [
        {
            "query": f"In the {NAMESPACE} thruster assembly, which liquid agent handles cooling and at what bar pressure level?",
            "expected_uid": created_memories["fact_1"]["memory_uid"],
            "expected_src_ref": f"doc_{NAMESPACE}_propulsion"
        },
        {
            "query": f"How cold in Kelvin is the {NAMESPACE} cryogenic container chamber kept?",
            "expected_uid": created_memories["fact_2"]["memory_uid"],
            "expected_src_ref": f"doc_{NAMESPACE}_storage"
        },
        {
            "query": f"How fast in Gbps can the {NAMESPACE} long-range communications send data optically?",
            "expected_uid": created_memories["fact_3"]["memory_uid"],
            "expected_src_ref": f"doc_{NAMESPACE}_telecom"
        }
    ]

    for item in para_queries:
        r = requests.get(f"{API_BASE}/tars/memory", params={"query": item["query"], "memory_type": "LONG_TERM", "top_k": 3})
        hits = r.json().get("memories", [])
        top1_hit = hits[0] if hits else None
        top1_match = bool(top1_hit and top1_hit["memory_uid"] == item["expected_uid"])
        top3_match = any(h["memory_uid"] == item["expected_uid"] for h in hits)
        battery_res["paraphrased_retrieval"].append({
            "query": item["query"],
            "top1_match": top1_match,
            "top3_match": top3_match,
            "top1_uid": top1_hit.get("memory_uid") if top1_hit else None,
            "similarity": top1_hit.get("similarity") if top1_hit else 0.0
        })
        if top1_hit:
            battery_res["provenance_checks"].append({
                "query_type": "paraphrased",
                "uid": top1_hit.get("memory_uid"),
                "source_type": top1_hit.get("source_type"),
                "source_ref": top1_hit.get("source_reference"),
                "expected_src_ref": item["expected_src_ref"],
                "has_correct_ref": top1_hit.get("source_reference") == item["expected_src_ref"],
                "is_verified_fact": top1_hit.get("is_verified_fact") is True,
                "similarity": top1_hit.get("similarity")
            })

    # 3. Similarity Collision Queries (Port vs Starboard)
    collision_tests = [
        {
            "name": "port_attitude_query",
            "query": f"Which model and resolution is used in {NAMESPACE} port-side attitude sensor?",
            "expected_uid": created_memories["collision_port"]["memory_uid"],
            "forbidden_uid": created_memories["collision_starboard"]["memory_uid"],
            "expected_tokens": ["LG-400", "0.01"],
            "forbidden_tokens": ["ST-900", "0.002"]
        },
        {
            "name": "starboard_attitude_query",
            "query": f"Which model and resolution is used in {NAMESPACE} starboard-side attitude sensor?",
            "expected_uid": created_memories["collision_starboard"]["memory_uid"],
            "forbidden_uid": created_memories["collision_port"]["memory_uid"],
            "expected_tokens": ["ST-900", "0.002"],
            "forbidden_tokens": ["LG-400", "0.01"]
        }
    ]

    for item in collision_tests:
        r = requests.get(f"{API_BASE}/tars/memory", params={"query": item["query"], "memory_type": "LONG_TERM", "top_k": 3})
        hits = r.json().get("memories", [])
        top1_hit = hits[0] if hits else None
        no_collision_leak = bool(top1_hit and top1_hit["memory_uid"] == item["expected_uid"])
        collision_detected_wrong = bool(top1_hit and top1_hit["memory_uid"] == item["forbidden_uid"])
        battery_res["similarity_collision"].append({
            "test": item["name"],
            "passed": no_collision_leak and not collision_detected_wrong,
            "top1_uid": top1_hit.get("memory_uid") if top1_hit else None,
            "expected_uid": item["expected_uid"],
            "forbidden_uid": item["forbidden_uid"],
            "content": top1_hit.get("content") if top1_hit else ""
        })

    # 4. Contradictory Sources Retrieval (Both sources preserved & cited)
    r_contra = requests.get(f"{API_BASE}/tars/knowledge/search", params={
        "query": f"maximum output of {NAMESPACE} photovoltaic solar array",
        "top_k": 5
    })
    k_hits = r_contra.json().get("results", [])
    found_850 = any("850 Kilowatts" in h.get("content", "") for h in k_hits)
    found_250 = any("250 Kilowatts" in h.get("content", "") for h in k_hits)
    citations_preserved = [h.get("citation") for h in k_hits if NAMESPACE in h.get("content", "")]

    battery_res["contradictory_sources"] = {
        "found_version_1": found_850,
        "found_version_2": found_250,
        "both_sources_preserved": found_850 and found_250,
        "citations_preserved": citations_preserved
    }

    # 6. Unknown Information Rejection Queries
    unknown_queries = [
        f"What is the quantum encryption frequency of the {NAMESPACE} hyperdrive warp coil?",
        f"Who was the chief botanist on the {NAMESPACE} greenhouse expedition in 1985?"
    ]

    for uq in unknown_queries:
        # Check verified long-term memory search similarity
        r_mem = requests.get(f"{API_BASE}/tars/memory", params={"query": uq, "memory_type": "LONG_TERM", "top_k": 3})
        top_mem = r_mem.json().get("memories", [])[0] if r_mem.json().get("memories") else None
        top_sim = top_mem.get("similarity", 0.0) if top_mem else 0.0

        # Also query /ai/chat
        r_chat = requests.post(f"{API_BASE}/ai/chat", json={"prompt": uq})
        chat_reply = r_chat.json().get("reply", "")

        # Proper guarding: No high-similarity verified memory exists (< 0.35)
        # and TARS does not claim verified truth for unknown data
        is_unknown_guarded = (top_sim < 0.35) and (
            "[حقيقة موثقة" not in chat_reply or "warp coil" not in chat_reply.lower()
        )

        battery_res["unknown_information"].append({
            "query": uq,
            "top_memory_similarity": top_sim,
            "chat_reply_excerpt": chat_reply[:180],
            "properly_guarded": is_unknown_guarded
        })

    # Compute Summary Metrics
    total_exact = len(battery_res["exact_retrieval"])
    exact_top1 = sum(1 for x in battery_res["exact_retrieval"] if x["top1_match"])
    exact_top3 = sum(1 for x in battery_res["exact_retrieval"] if x["top3_match"])

    total_para = len(battery_res["paraphrased_retrieval"])
    para_top1 = sum(1 for x in battery_res["paraphrased_retrieval"] if x["top1_match"])
    para_top3 = sum(1 for x in battery_res["paraphrased_retrieval"] if x["top3_match"])

    total_retrievals = total_exact + total_para
    overall_top1 = (exact_top1 + para_top1) / max(1, total_retrievals)
    overall_top3 = (exact_top3 + para_top3) / max(1, total_retrievals)

    prov_checks = battery_res["provenance_checks"]
    correct_prov = sum(1 for p in prov_checks if p["has_correct_ref"] and p["is_verified_fact"])
    prov_rate = correct_prov / max(1, len(prov_checks))

    collision_passed = sum(1 for c in battery_res["similarity_collision"] if c["passed"])
    collision_rate = collision_passed / max(1, len(battery_res["similarity_collision"]))
    false_retrieval_rate = 1.0 - collision_rate

    unknown_passed = sum(1 for u in battery_res["unknown_information"] if u["properly_guarded"])
    unknown_rejection_rate = unknown_passed / max(1, len(battery_res["unknown_information"]))

    conflict_detection_rate = 1.0 if (has_numeric_conflict and battery_res["contradictory_sources"]["both_sources_preserved"]) else 0.0

    metrics = {
        "top_1_retrieval_accuracy": round(overall_top1, 4),
        "top_3_retrieval_accuracy": round(overall_top3, 4),
        "exact_top1_accuracy": round(exact_top1 / max(1, total_exact), 4),
        "paraphrased_top1_accuracy": round(para_top1 / max(1, total_para), 4),
        "correct_source_attribution_rate": round(prov_rate, 4),
        "false_retrieval_rate": round(false_retrieval_rate, 4),
        "collision_accuracy": round(collision_rate, 4),
        "unknown_question_rejection_rate": round(unknown_rejection_rate, 4),
        "conflict_detection_rate": round(conflict_detection_rate, 4)
    }

    battery_res["computed_metrics"] = metrics
    print(f"[{run_label}] Top-1 Accuracy: {metrics['top_1_retrieval_accuracy']*100}% | Top-3 Accuracy: {metrics['top_3_retrieval_accuracy']*100}% | Source Attribution: {metrics['correct_source_attribution_rate']*100}%")
    return battery_res

# Execute Pre-Restart Battery
pre_battery = run_evaluation_battery("pre_restart")
report_data["pre_restart_battery"] = pre_battery

# Save intermediate results
with open("tests/tars_002_full_report.json", "w", encoding="utf-8") as f:
    json.dump(report_data, f, indent=2, ensure_ascii=False)

print("Pre-restart evaluation battery finished. Ready for restart.")

