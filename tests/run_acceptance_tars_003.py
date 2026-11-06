import os
import sys
import json
import time
import requests

sys.stdout.reconfigure(encoding='utf-8')

API_BASE = "http://127.0.0.1:8000"
NAMESPACE = f"tars003_{int(time.time())}"

report_data = {
    "test_name": "TARS-003 — Structured Retrieval & Re-ranking Improvement",
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

print(f"=== Starting TARS-003 Acceptance Test (Namespace: {NAMESPACE}) ===")

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
# 1. Ingest Structured Test Facts & Sibling Component Sets
# ------------------------------------------------------------------------------
test_memories = [
    # Baseline Fact 1: Propulsion
    {
        "id": "fact_1",
        "subject": f"{NAMESPACE}_alpha_thruster_coolant",
        "content": f"The {NAMESPACE} Alpha Thruster uses liquid methane coolant pressurized to 42 bar.",
        "category": "propulsion",
        "source_type": "document",
        "source_reference": f"doc_{NAMESPACE}_propulsion",
        "is_verified_fact": True
    },
    # Baseline Fact 2: Storage Cryo
    {
        "id": "fact_2",
        "subject": f"{NAMESPACE}_cryo_storage_temperature",
        "content": f"The {NAMESPACE} primary cryo-storage bay maintains a nominal temperature of 77 Kelvin.",
        "category": "storage",
        "source_type": "document",
        "source_reference": f"doc_{NAMESPACE}_storage",
        "is_verified_fact": True
    },
    # Baseline Fact 3: Telecom
    {
        "id": "fact_3",
        "subject": f"{NAMESPACE}_baud_rate_comms",
        "content": f"The {NAMESPACE} deep-space communication array operates at an optical baud rate of 100 Gbps.",
        "category": "telecom",
        "source_type": "document",
        "source_reference": f"doc_{NAMESPACE}_telecom",
        "is_verified_fact": True
    },
    # Sibling Pair: Guidance Attitude Sensors (Port vs Starboard)
    {
        "id": "sibling_sensor_port",
        "subject": f"{NAMESPACE}_attitude_sensor_port",
        "content": f"The {NAMESPACE} port-side attitude sensor uses laser gyroscope model LG-400 with 0.01 degree resolution.",
        "category": "guidance",
        "source_type": "document",
        "source_reference": f"doc_{NAMESPACE}_guidance_port",
        "is_verified_fact": True
    },
    {
        "id": "sibling_sensor_starboard",
        "subject": f"{NAMESPACE}_attitude_sensor_starboard",
        "content": f"The {NAMESPACE} starboard-side attitude sensor uses star tracker model ST-900 with 0.002 degree resolution.",
        "category": "guidance",
        "source_type": "document",
        "source_reference": f"doc_{NAMESPACE}_guidance_starboard",
        "is_verified_fact": True
    },
    # Sibling Triplet: Thruster Pods (Primary vs Secondary vs Tertiary)
    {
        "id": "thruster_primary",
        "subject": f"{NAMESPACE}_primary_thruster_vector",
        "content": f"The {NAMESPACE} primary thruster pod provides 120 kN nominal forward propulsion thrust.",
        "category": "propulsion",
        "source_type": "document",
        "source_reference": f"doc_{NAMESPACE}_propulsion_primary",
        "is_verified_fact": True
    },
    {
        "id": "thruster_secondary",
        "subject": f"{NAMESPACE}_secondary_thruster_vector",
        "content": f"The {NAMESPACE} secondary thruster pod provides 45 kN auxiliary lateral propulsion thrust.",
        "category": "propulsion",
        "source_type": "document",
        "source_reference": f"doc_{NAMESPACE}_propulsion_secondary",
        "is_verified_fact": True
    },
    {
        "id": "thruster_tertiary",
        "subject": f"{NAMESPACE}_tertiary_thruster_vector",
        "content": f"The {NAMESPACE} tertiary thruster pod provides 15 kN emergency vernier attitude correction thrust.",
        "category": "propulsion",
        "source_type": "document",
        "source_reference": f"doc_{NAMESPACE}_propulsion_tertiary",
        "is_verified_fact": True
    }
]

created_memories = {}
for m in test_memories:
    res = requests.post(f"{API_BASE}/tars/memory", json={
        "subject": m["subject"],
        "content": m["content"],
        "category": m["category"],
        "source_type": m["source_type"],
        "source_reference": m["source_reference"],
        "is_verified_fact": m["is_verified_fact"],
        "memory_type": "LONG_TERM"
    })
    if res.status_code == 200 and res.json().get("success"):
        created_memories[m["id"]] = res.json()["memory"]
    else:
        print(f"[ERROR] Failed to insert memory {m['id']}: {res.text}")

print(f"Stored {len(created_memories)} test memories in namespace {NAMESPACE}.")

# ------------------------------------------------------------------------------
# 2. Test Section 1: Exact Retrieval
# ------------------------------------------------------------------------------
exact_tests = [
    {
        "query": f"What coolant and pressure does the {NAMESPACE} Alpha Thruster use?",
        "expected_id": "fact_1",
        "expected_subject": f"{NAMESPACE}_alpha_thruster_coolant",
        "expected_token": "liquid methane"
    },
    {
        "query": f"What is the nominal temperature of the {NAMESPACE} cryo-storage bay?",
        "expected_id": "fact_2",
        "expected_subject": f"{NAMESPACE}_cryo_storage_temperature",
        "expected_token": "77 Kelvin"
    },
    {
        "query": f"What is the optical baud rate of the {NAMESPACE} deep-space communication array?",
        "expected_id": "fact_3",
        "expected_subject": f"{NAMESPACE}_baud_rate_comms",
        "expected_token": "100 Gbps"
    }
]

exact_results = []
for t in exact_tests:
    res = requests.get(f"{API_BASE}/tars/memory", params={"query": t["query"], "top_k": 5})
    data = res.json().get("memories", [])
    top = data[0] if data else {}
    top_subject = top.get("subject", "")
    top_content = top.get("content", "")
    passed = (top_subject == t["expected_subject"]) and (t["expected_token"] in top_content)
    exact_results.append({
        "query": t["query"],
        "expected": t["expected_subject"],
        "top_match": top_subject,
        "similarity": top.get("similarity"),
        "base_similarity": top.get("base_similarity"),
        "signals": top.get("re_ranking_signals", []),
        "passed": passed
    })

exact_acc = sum(1 for r in exact_results if r["passed"]) / len(exact_results)
log("1. Exact Retrieval", exact_acc == 1.0, {
    "accuracy": exact_acc,
    "tests": exact_results
})

# ------------------------------------------------------------------------------
# 3. Test Section 2: Paraphrased Retrieval
# ------------------------------------------------------------------------------
paraphrase_tests = [
    {
        "query": f"In the {NAMESPACE} thruster assembly, which liquid agent handles cooling and at what bar pressure level?",
        "expected_id": "fact_1",
        "expected_subject": f"{NAMESPACE}_alpha_thruster_coolant",
        "expected_token": "42 bar"
    },
    {
        "query": f"How cold in Kelvin is the {NAMESPACE} cryogenic container chamber kept?",
        "expected_id": "fact_2",
        "expected_subject": f"{NAMESPACE}_cryo_storage_temperature",
        "expected_token": "77 Kelvin"
    },
    {
        "query": f"How fast in Gbps can the {NAMESPACE} long-range communications send data optically?",
        "expected_id": "fact_3",
        "expected_subject": f"{NAMESPACE}_baud_rate_comms",
        "expected_token": "100 Gbps"
    }
]

paraphrase_results = []
for t in paraphrase_tests:
    res = requests.get(f"{API_BASE}/tars/memory", params={"query": t["query"], "top_k": 5})
    data = res.json().get("memories", [])
    top = data[0] if data else {}
    top_subject = top.get("subject", "")
    top_content = top.get("content", "")
    passed = (top_subject == t["expected_subject"]) and (t["expected_token"] in top_content)
    paraphrase_results.append({
        "query": t["query"],
        "expected": t["expected_subject"],
        "top_match": top_subject,
        "similarity": top.get("similarity"),
        "base_similarity": top.get("base_similarity"),
        "signals": top.get("re_ranking_signals", []),
        "passed": passed
    })

para_acc = sum(1 for r in paraphrase_results if r["passed"]) / len(paraphrase_results)
log("2. Paraphrased Retrieval", para_acc == 1.0, {
    "accuracy": para_acc,
    "tests": paraphrase_results
})

# ------------------------------------------------------------------------------
# 4. Test Section 3: Sibling Component Collision Tests (Port/Starboard & Multi-Thruster)
# ------------------------------------------------------------------------------
collision_tests = [
    # 3A: Explicit Starboard Query
    {
        "query": f"What sensor model and resolution does the {NAMESPACE} starboard-side attitude sensor have?",
        "expected_subject": f"{NAMESPACE}_attitude_sensor_starboard",
        "forbidden_subject": f"{NAMESPACE}_attitude_sensor_port",
        "expected_content_token": "ST-900",
        "label": "Starboard Attitude Sensor"
    },
    # 3B: Explicit Port Query
    {
        "query": f"What model is installed on the {NAMESPACE} port attitude sensor?",
        "expected_subject": f"{NAMESPACE}_attitude_sensor_port",
        "forbidden_subject": f"{NAMESPACE}_attitude_sensor_starboard",
        "expected_content_token": "LG-400",
        "label": "Port Attitude Sensor"
    },
    # 3C: Sibling Triplet: Secondary Thruster Pod
    {
        "query": f"What is the thrust output of the {NAMESPACE} secondary thruster pod?",
        "expected_subject": f"{NAMESPACE}_secondary_thruster_vector",
        "forbidden_subject": f"{NAMESPACE}_primary_thruster_vector",
        "expected_content_token": "45 kN",
        "label": "Secondary Thruster Pod (Lateral)"
    },
    # 3D: Sibling Triplet: Primary Thruster Pod
    {
        "query": f"What is the forward thrust capacity of the {NAMESPACE} primary thruster pod?",
        "expected_subject": f"{NAMESPACE}_primary_thruster_vector",
        "forbidden_subject": f"{NAMESPACE}_secondary_thruster_vector",
        "expected_content_token": "120 kN",
        "label": "Primary Thruster Pod (Forward)"
    },
    # 3E: Direct Hardware Model Disambiguation (ST-900)
    {
        "query": f"Which attitude sensor uses ST-900 on {NAMESPACE}?",
        "expected_subject": f"{NAMESPACE}_attitude_sensor_starboard",
        "forbidden_subject": f"{NAMESPACE}_attitude_sensor_port",
        "expected_content_token": "ST-900",
        "label": "Direct Hardware Model Match (ST-900 -> Starboard)"
    }
]

collision_results = []
for ct in collision_tests:
    res = requests.get(f"{API_BASE}/tars/memory", params={"query": ct["query"], "top_k": 5})
    data = res.json().get("memories", [])
    top = data[0] if data else {}
    top_subject = top.get("subject", "")
    top_content = top.get("content", "")
    top_sim = top.get("similarity", 0)

    # Find the rank of the forbidden sibling (if present)
    forbidden_rank = None
    forbidden_sim = None
    for idx, cand in enumerate(data):
        if cand.get("subject") == ct["forbidden_subject"]:
            forbidden_rank = idx + 1
            forbidden_sim = cand.get("similarity")
            break

    passed = (top_subject == ct["expected_subject"]) and (top_subject != ct["forbidden_subject"]) and (ct["expected_content_token"] in top_content)

    collision_results.append({
        "label": ct["label"],
        "query": ct["query"],
        "expected_subject": ct["expected_subject"],
        "retrieved_top_subject": top_subject,
        "top_similarity": top_sim,
        "top_base_similarity": top.get("base_similarity"),
        "top_signals": top.get("re_ranking_signals", []),
        "forbidden_sibling": ct["forbidden_subject"],
        "forbidden_sibling_rank": forbidden_rank,
        "forbidden_sibling_similarity": forbidden_sim,
        "passed": passed
    })

collision_acc = sum(1 for r in collision_results if r["passed"]) / len(collision_results)
log("3. Sibling Collision & Re-ranking Disambiguation", collision_acc == 1.0, {
    "accuracy": collision_acc,
    "tests": collision_results
})

# ------------------------------------------------------------------------------
# 5. Test Section 4: Missing Component & Graceful Degradation
# ------------------------------------------------------------------------------
degradation_tests = [
    # 4A: Generic query without side specification
    {
        "query": f"What are the attitude sensors installed on {NAMESPACE}?",
        "label": "Generic query without side",
        "type": "generic"
    },
    # 4B: Completely unknown query (should not hallucinate or match with high false positive score)
    {
        "query": f"What is the plasma flux of the {NAMESPACE} hyperdrive warp coil?",
        "label": "Completely unknown component",
        "type": "unknown"
    }
]

degradation_results = []
for dt in degradation_tests:
    res = requests.get(f"{API_BASE}/tars/memory", params={"query": dt["query"], "top_k": 5})
    data = res.json().get("memories", [])
    if dt["type"] == "generic":
        subjects = [d.get("subject") for d in data]
        has_port = f"{NAMESPACE}_attitude_sensor_port" in subjects
        has_starboard = f"{NAMESPACE}_attitude_sensor_starboard" in subjects
        passed = has_port and has_starboard
        degradation_results.append({
            "label": dt["label"],
            "query": dt["query"],
            "results_count": len(data),
            "subjects_found": subjects[:4],
            "passed": passed
        })
    elif dt["type"] == "unknown":
        top_sim = data[0].get("similarity", 0) if data else 0
        passed = (len(data) == 0) or (top_sim < 0.60)
        degradation_results.append({
            "label": dt["label"],
            "query": dt["query"],
            "top_similarity": top_sim,
            "passed": passed
        })

deg_acc = sum(1 for r in degradation_results if r["passed"]) / len(degradation_results)
log("4. Missing Component & Graceful Degradation", deg_acc == 1.0, {
    "accuracy": deg_acc,
    "tests": degradation_results
})

# ------------------------------------------------------------------------------
# 6. Test Section 5: Contradictory Sources Knowledge Test
# ------------------------------------------------------------------------------
doc_a_text = f"Specification Report for {NAMESPACE}: The main solar array generates 850 kW of electrical power at 1 AU under nominal illumination."
doc_b_text = f"Specification Report for {NAMESPACE}: The main solar array generates 250 kW of electrical power at 1 AU under nominal illumination."

res_doc_a = requests.post(
    f"{API_BASE}/tars/knowledge/ingest-text",
    json={
        "title": f"{NAMESPACE}_Solar_Array_Specs_Alpha",
        "content": doc_a_text,
        "source_reference": f"doc_{NAMESPACE}_solar_alpha"
    }
)
doc_a_json = res_doc_a.json()

res_doc_b = requests.post(
    f"{API_BASE}/tars/knowledge/ingest-text",
    json={
        "title": f"{NAMESPACE}_Solar_Array_Specs_Beta",
        "content": doc_b_text,
        "source_reference": f"doc_{NAMESPACE}_solar_beta"
    }
)
doc_b_json = res_doc_b.json()

res_search_chunks = requests.get(
    f"{API_BASE}/tars/knowledge/search",
    params={"query": f"How much electrical power does the {NAMESPACE} main solar array generate at 1 AU?", "top_k": 5}
)
chunks_found = res_search_chunks.json().get("results", [])

both_docs_preserved = (
    any(f"{NAMESPACE}_Solar_Array_Specs_Alpha" in c.get("document_title", "") for c in chunks_found) and
    any(f"{NAMESPACE}_Solar_Array_Specs_Beta" in c.get("document_title", "") for c in chunks_found)
)
has_conflict_flag = any(c.get("has_conflict") or "CONFLICT" in c.get("citation", "") for c in chunks_found)

log("5. Contradictory Sources Knowledge Preservation", both_docs_preserved and has_conflict_flag, {
    "doc_a_ingest": doc_a_json.get("success"),
    "doc_b_ingest": doc_b_json.get("success"),
    "both_preserved": both_docs_preserved,
    "conflict_detected_in_citations": has_conflict_flag,
    "chunks_count": len(chunks_found),
    "citations": [c.get("citation") for c in chunks_found[:2]]
})

# ------------------------------------------------------------------------------
# 7. Test Section 6: Server Restart & Persistence Verification Preparation
# ------------------------------------------------------------------------------
restart_queries = [
    f"What sensor model and resolution does the {NAMESPACE} starboard-side attitude sensor have?",
    f"What model is installed on the {NAMESPACE} port attitude sensor?",
    f"What is the thrust output of the {NAMESPACE} secondary thruster pod?",
    f"What coolant and pressure does the {NAMESPACE} Alpha Thruster use?"
]

pre_restart_results = []
for q in restart_queries:
    r = requests.get(f"{API_BASE}/tars/memory", params={"query": q, "top_k": 3}).json().get("memories", [])
    top = r[0] if r else {}
    pre_restart_results.append({
        "query": q,
        "subject": top.get("subject"),
        "similarity": top.get("similarity"),
        "signals": top.get("re_ranking_signals", [])
    })

report_data["pre_restart_results"] = pre_restart_results
report_data["restart_queries"] = restart_queries

# Save state
with open("tests/tars_003_full_report.json", "w", encoding="utf-8") as f:
    json.dump(report_data, f, indent=2, ensure_ascii=False)

print(f"[INFO] Section 1-5 complete. Pre-restart snapshot saved for namespace {NAMESPACE}.")
