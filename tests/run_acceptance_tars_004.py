import os
import sys
import json
import time
import requests

sys.stdout.reconfigure(encoding='utf-8')

API_BASE = "http://127.0.0.1:8000"

def get_test_memories(namespace):
    return [
        # Domain 1: Networking & Cybersecurity
        {
            "id": "net_firewall_rule",
            "subject": f"{namespace}_firewall_ingress_ssh",
            "content": f"In {namespace} network configuration, ingress SSH access on port 2222 is restricted to subnet 10.240.0.0/16.",
            "category": "cybersecurity",
            "source_type": "document",
            "source_reference": f"sec_policy_{namespace}_v1",
            "confidence": 0.95,
            "is_verified_fact": True
        },
        {
            "id": "net_interface_eth0",
            "subject": f"{namespace}_interface_eth0",
            "content": f"Network interface eth0 on host {namespace} is assigned static IPv4 address 192.168.10.50 with MTU 1500.",
            "category": "networking",
            "source_type": "document",
            "source_reference": f"net_config_{namespace}_eth0",
            "confidence": 0.95,
            "is_verified_fact": True
        },
        {
            "id": "net_interface_eth1",
            "subject": f"{namespace}_interface_eth1",
            "content": f"Network interface eth1 on host {namespace} is assigned static IPv4 address 10.0.5.100 with MTU 9000 jumbo frames.",
            "category": "networking",
            "source_type": "document",
            "source_reference": f"net_config_{namespace}_eth1",
            "confidence": 0.95,
            "is_verified_fact": True
        },

        # Domain 2: General Computing
        {
            "id": "server_node_alpha",
            "subject": f"{namespace}_cluster_node_alpha",
            "content": f"Compute cluster node Alpha in {namespace} datacenter runs Ubuntu 24.04 LTS on an AMD EPYC 9654 processor with 768 GB DDR5 ECC RAM.",
            "category": "computing",
            "source_type": "document",
            "source_reference": f"infra_spec_{namespace}_alpha",
            "confidence": 0.95,
            "is_verified_fact": True
        },
        {
            "id": "server_node_beta",
            "subject": f"{namespace}_cluster_node_beta",
            "content": f"Compute cluster node Beta in {namespace} datacenter runs RHEL 9.3 on an Intel Xeon Platinum 8480 processor with 512 GB DDR5 ECC RAM.",
            "category": "computing",
            "source_type": "document",
            "source_reference": f"infra_spec_{namespace}_beta",
            "confidence": 0.95,
            "is_verified_fact": True
        },
        {
            "id": "cache_redis_port",
            "subject": f"{namespace}_cache_redis_port",
            "content": f"The primary Redis caching instance for {namespace} binds to localhost TCP port 6389 with password authentication enabled.",
            "category": "computing",
            "source_type": "document",
            "source_reference": f"db_spec_{namespace}_redis",
            "confidence": 0.92,
            "is_verified_fact": True
        },

        # Domain 3: Education and Science
        {
            "id": "science_chlorophyll",
            "subject": f"{namespace}_chlorophyll_absorption",
            "content": f"According to scientific reference {namespace}, chlorophyll a exhibits peak absorption wavelengths at 430 nm and 662 nm.",
            "category": "science",
            "source_type": "reference",
            "source_reference": f"bio_handbook_{namespace}_ch4",
            "confidence": 0.98,
            "is_verified_fact": True
        },
        {
            "id": "science_mars_gravity",
            "subject": f"{namespace}_mars_surface_gravity",
            "content": f"تبلغ الجاذبية السطحية لكوكب المريخ في دراسة {namespace} حوالي 3.72 متر لكل ثانية مربعة، وهي تعادل 38 بالمائة من جاذبية الأرض.",
            "category": "science",
            "source_type": "reference",
            "source_reference": f"astro_paper_{namespace}_mars",
            "confidence": 0.99,
            "is_verified_fact": True
        },

        # Domain 4: General Knowledge
        {
            "id": "general_treaty_westphalia",
            "subject": f"{namespace}_treaty_of_westphalia",
            "content": f"Historical archive {namespace} notes the Peace of Westphalia was signed in 1648, establishing national sovereignty principles.",
            "category": "history",
            "source_type": "reference",
            "source_reference": f"hist_archive_{namespace}_doc12",
            "confidence": 0.95,
            "is_verified_fact": True
        },
        {
            "id": "general_cairo_founding",
            "subject": f"{namespace}_cairo_founding_year",
            "content": f"تأسست مدينة القاهرة التاريخية في سجل {namespace} عام 969 ميلادية على يد القائد جوهر الصقلي بأمر من المعز لدين الله الفاطمي.",
            "category": "history",
            "source_type": "reference",
            "source_reference": f"islamic_history_{namespace}_cairo",
            "confidence": 0.98,
            "is_verified_fact": True
        },

        # Domain 5: Robotics and Hardware
        {
            "id": "robot_joint_1",
            "subject": f"{namespace}_robot_joint_1_motor",
            "content": f"The robotic manipulator Joint 1 base azimuth on {namespace} uses a Maxon EC-90 brushless DC motor with 120 Nm peak torque.",
            "category": "robotics",
            "source_type": "document",
            "source_reference": f"robot_spec_{namespace}_arm",
            "confidence": 0.95,
            "is_verified_fact": True
        },
        {
            "id": "robot_joint_2",
            "subject": f"{namespace}_robot_joint_2_motor",
            "content": f"The robotic manipulator Joint 2 shoulder elevation on {namespace} uses a Harmonic Drive strain wave actuator with 280 Nm peak torque.",
            "category": "robotics",
            "source_type": "document",
            "source_reference": f"robot_spec_{namespace}_arm",
            "confidence": 0.95,
            "is_verified_fact": True
        },
        {
            "id": "robot_joint_3",
            "subject": f"{namespace}_robot_joint_3_motor",
            "content": f"The robotic manipulator Joint 3 elbow pitch on {namespace} uses a Kollmorgen AKM-32 servo motor with 45 Nm peak torque.",
            "category": "robotics",
            "source_type": "document",
            "source_reference": f"robot_spec_{namespace}_arm",
            "confidence": 0.95,
            "is_verified_fact": True
        },

        # Domain 6 / Source Trust Variations: Verified Fact vs Unverified Inference
        {
            "id": "quantum_crypto_key",
            "subject": f"{namespace}_quantum_cryptography_key",
            "content": f"In {namespace} lab prototype, the quantum key distribution operates over dark fiber with a 1550 nm single-photon transmitter.",
            "category": "cybersecurity",
            "source_type": "document",
            "source_reference": f"qkd_lab_{namespace}_report",
            "confidence": 0.98,
            "is_verified_fact": True
        },
        {
            "id": "unverified_rumor",
            "subject": f"{namespace}_unverified_speculation",
            "content": f"Unverified forum rumor claims {namespace} wireless link might be upgraded to 60 GHz WiGig next month.",
            "category": "networking",
            "source_type": "user_session",
            "source_reference": f"forum_chatter_{namespace}",
            "confidence": 0.35,
            "is_verified_fact": False
        }
    ]


def get_evaluation_battery(namespace):
    return [
        # --- Dimension A: Exact Retrieval ---
        {
            "id": "A1_exact_ssh",
            "dimension": "A_exact",
            "domain": "networking",
            "lang": "en",
            "query": f"What ingress SSH port and subnet are configured for {namespace} firewall?",
            "expected_subject": f"{namespace}_firewall_ingress_ssh",
            "expected_tokens": ["2222", "10.240.0.0/16"]
        },
        {
            "id": "A2_exact_node_alpha",
            "dimension": "A_exact",
            "domain": "computing",
            "lang": "en",
            "query": f"Which operating system and processor are installed on {namespace} cluster node Alpha?",
            "expected_subject": f"{namespace}_cluster_node_alpha",
            "expected_tokens": ["Ubuntu 24.04", "EPYC 9654"]
        },
        {
            "id": "A3_exact_chlorophyll",
            "dimension": "A_exact",
            "domain": "science",
            "lang": "en",
            "query": f"What are the peak absorption wavelengths of chlorophyll a in {namespace}?",
            "expected_subject": f"{namespace}_chlorophyll_absorption",
            "expected_tokens": ["430 nm", "662 nm"]
        },
        {
            "id": "A4_exact_mars_gravity",
            "dimension": "A_exact",
            "domain": "science",
            "lang": "ar",
            "query": f"كم تبلغ الجاذبية السطحية لكوكب المريخ في دراسة {namespace}؟",
            "expected_subject": f"{namespace}_mars_surface_gravity",
            "expected_tokens": ["3.72", "38"]
        },
        {
            "id": "A5_exact_cairo",
            "dimension": "A_exact",
            "domain": "general",
            "lang": "ar",
            "query": f"في أي عام تأسست مدينة القاهرة التاريخية في سجل {namespace}؟",
            "expected_subject": f"{namespace}_cairo_founding_year",
            "expected_tokens": ["969", "جوهر الصقلي"]
        },

        # --- Dimension B: Paraphrased Retrieval (EN, AR, Cross) ---
        {
            "id": "B1_para_ssh_port",
            "dimension": "B_paraphrase",
            "domain": "networking",
            "lang": "en",
            "query": f"Which port number allows secure shell inbound connections on the {namespace} network gateway?",
            "expected_subject": f"{namespace}_firewall_ingress_ssh",
            "expected_tokens": ["2222"]
        },
        {
            "id": "B2_para_node_alpha_ram",
            "dimension": "B_paraphrase",
            "domain": "computing",
            "lang": "en",
            "query": f"How much system memory and what Linux distribution does the Alpha computing server have in {namespace}?",
            "expected_subject": f"{namespace}_cluster_node_alpha",
            "expected_tokens": ["768 GB", "Ubuntu"]
        },
        {
            "id": "B3_para_mars_gravity_ar",
            "dimension": "B_paraphrase",
            "domain": "science",
            "lang": "ar",
            "query": f"ما هي شدة جذب سطح كوكب المريخ مقارنة بالأرض حسب أبحاث {namespace}؟",
            "expected_subject": f"{namespace}_mars_surface_gravity",
            "expected_tokens": ["3.72", "38"]
        },
        {
            "id": "B4_para_cairo_ar",
            "dimension": "B_paraphrase",
            "domain": "general",
            "lang": "ar",
            "query": f"متى تم بناء وتأسيس عاصمة مصر الفاطمية على يد جوهر الصقلي في وثائق {namespace}؟",
            "expected_subject": f"{namespace}_cairo_founding_year",
            "expected_tokens": ["969"]
        },
        {
            "id": "B5_para_cross_redis",
            "dimension": "B_paraphrase",
            "domain": "computing",
            "lang": "cross",
            "query": f"ما هو المنفذ المخصص للاتصال بقاعدة بيانات ريديس السريعة في {namespace}؟",
            "expected_subject": f"{namespace}_cache_redis_port",
            "expected_tokens": ["6389"]
        },
        {
            "id": "B6_para_cross_mars",
            "dimension": "B_paraphrase",
            "domain": "science",
            "lang": "cross",
            "query": f"How does the gravitational acceleration of Mars compare to Earth's gravity in {namespace} report?",
            "expected_subject": f"{namespace}_mars_surface_gravity",
            "expected_tokens": ["3.72", "38"]
        },

        # --- Dimension C: Entity Disambiguation (Non-Aerospace Siblings) ---
        {
            "id": "C1_disambig_eth0",
            "dimension": "C_disambiguation",
            "domain": "networking",
            "lang": "en",
            "query": f"What is the static IP address and MTU of network interface eth0 on {namespace}?",
            "expected_subject": f"{namespace}_interface_eth0",
            "forbidden_subject": f"{namespace}_interface_eth1",
            "expected_tokens": ["192.168.10.50", "1500"]
        },
        {
            "id": "C2_disambig_eth1",
            "dimension": "C_disambiguation",
            "domain": "networking",
            "lang": "en",
            "query": f"What is the static IP address and MTU of network interface eth1 on {namespace}?",
            "expected_subject": f"{namespace}_interface_eth1",
            "forbidden_subject": f"{namespace}_interface_eth0",
            "expected_tokens": ["10.0.5.100", "9000"]
        },
        {
            "id": "C3_disambig_node_alpha",
            "dimension": "C_disambiguation",
            "domain": "computing",
            "lang": "en",
            "query": f"What processor model powers cluster node Alpha in {namespace}?",
            "expected_subject": f"{namespace}_cluster_node_alpha",
            "forbidden_subject": f"{namespace}_cluster_node_beta",
            "expected_tokens": ["EPYC 9654"]
        },
        {
            "id": "C4_disambig_node_beta",
            "dimension": "C_disambiguation",
            "domain": "computing",
            "lang": "en",
            "query": f"What processor model powers cluster node Beta in {namespace}?",
            "expected_subject": f"{namespace}_cluster_node_beta",
            "forbidden_subject": f"{namespace}_cluster_node_alpha",
            "expected_tokens": ["Xeon Platinum 8480"]
        },
        {
            "id": "C5_disambig_joint_1",
            "dimension": "C_disambiguation",
            "domain": "robotics",
            "lang": "en",
            "query": f"Which motor and peak torque are utilized on robotic manipulator Joint 1 in {namespace}?",
            "expected_subject": f"{namespace}_robot_joint_1_motor",
            "forbidden_subject": f"{namespace}_robot_joint_2_motor",
            "expected_tokens": ["Maxon EC-90", "120 Nm"]
        },
        {
            "id": "C6_disambig_joint_2",
            "dimension": "C_disambiguation",
            "domain": "robotics",
            "lang": "en",
            "query": f"Which actuator is installed on robotic manipulator Joint 2 in {namespace}?",
            "expected_subject": f"{namespace}_robot_joint_2_motor",
            "forbidden_subject": f"{namespace}_robot_joint_1_motor",
            "expected_tokens": ["Harmonic Drive", "280 Nm"]
        },

        # --- Dimension D: Generic Queries (Broad / Multi-candidate) ---
        {
            "id": "D1_generic_interfaces",
            "dimension": "D_generic",
            "domain": "networking",
            "lang": "en",
            "query": f"What are the network interfaces configured on host {namespace}?",
            "expected_candidates": [f"{namespace}_interface_eth0", f"{namespace}_interface_eth1"]
        },
        {
            "id": "D2_generic_cluster_nodes",
            "dimension": "D_generic",
            "domain": "computing",
            "lang": "en",
            "query": f"Tell me about the cluster compute nodes in {namespace} datacenter",
            "expected_candidates": [f"{namespace}_cluster_node_alpha", f"{namespace}_cluster_node_beta"]
        },

        # --- Dimension E: Unknown Questions (Zero Hallucination / Rejection) ---
        {
            "id": "E1_unknown_quantum_antenna",
            "dimension": "E_unknown",
            "domain": "science",
            "lang": "en",
            "query": f"What is the zero-point quantum vacuum fluctuation frequency of {namespace} subspace antenna?",
            "is_unknown": True
        },
        {
            "id": "E2_unknown_botanist",
            "dimension": "E_unknown",
            "domain": "general",
            "lang": "en",
            "query": f"What is the employee ID of the chief botanist at {namespace} greenhouse in 1892?",
            "is_unknown": True
        },
        {
            "id": "E3_unknown_submarine_ar",
            "dimension": "E_unknown",
            "domain": "general",
            "lang": "ar",
            "query": f"ما هو الاسم الرمزي للغواصة النووية التابعة لمشروع {namespace} عام 1941؟",
            "is_unknown": True
        },

        # --- Dimension G: Source Trust & Provenance ---
        {
            "id": "G1_trust_verified_qkd",
            "dimension": "G_trust",
            "domain": "cybersecurity",
            "lang": "en",
            "query": f"What is the optical wavelength of the quantum key distribution transmitter in {namespace}?",
            "expected_subject": f"{namespace}_quantum_cryptography_key",
            "expected_verified_fact": True,
            "expected_source_type": "document",
            "expected_src_ref": f"qkd_lab_{namespace}_report"
        },
        {
            "id": "G2_trust_unverified_rumor",
            "dimension": "G_trust",
            "domain": "networking",
            "lang": "en",
            "query": f"What forum speculation exists regarding {namespace} wireless link upgrade?",
            "expected_subject": f"{namespace}_unverified_speculation",
            "expected_verified_fact": False,
            "expected_source_type": "user_session",
            "expected_src_ref": f"forum_chatter_{namespace}"
        }
    ]


def execute_evaluation_battery(namespace):
    battery = get_evaluation_battery(namespace)
    results = []
    for item in battery:
        dim = item["dimension"]
        q = item["query"]

        if dim == "D_generic":
            r = requests.get(f"{API_BASE}/tars/memory", params={"query": q, "memory_type": "LONG_TERM", "top_k": 5}).json().get("memories", [])
            retrieved_subjects = [m.get("subject") for m in r]
            expected_set = set(item["expected_candidates"])
            found_set = expected_set & set(retrieved_subjects[:4])
            passed = len(found_set) == len(expected_set)
            results.append({
                "id": item["id"],
                "dimension": dim,
                "domain": item["domain"],
                "lang": item["lang"],
                "query": q,
                "expected_candidates": item["expected_candidates"],
                "retrieved_subjects": retrieved_subjects[:4],
                "passed": passed,
                "rank": 1 if passed else None,
                "top1_match": passed,
                "top3_match": passed,
                "top5_match": passed
            })

        elif dim == "E_unknown":
            r = requests.get(f"{API_BASE}/tars/memory", params={"query": q, "memory_type": "LONG_TERM", "top_k": 3}).json().get("memories", [])
            top_sim = r[0].get("similarity", 0.0) if r else 0.0
            rejected = (len(r) == 0) or (top_sim < 0.60)
            results.append({
                "id": item["id"],
                "dimension": dim,
                "domain": item["domain"],
                "lang": item["lang"],
                "query": q,
                "is_unknown": True,
                "top_similarity": top_sim,
                "passed": rejected,
                "rank": None,
                "top1_match": rejected,
                "top3_match": rejected,
                "top5_match": rejected
            })

        elif dim == "G_trust":
            r = requests.get(f"{API_BASE}/tars/memory", params={"query": q, "memory_type": "LONG_TERM", "top_k": 3}).json().get("memories", [])
            top = r[0] if r else {}
            top_subj = top.get("subject")
            rank = None
            for idx, cand in enumerate(r):
                if cand.get("subject") == item["expected_subject"]:
                    rank = idx + 1
                    break
            is_fact_match = (top.get("is_verified_fact") == item["expected_verified_fact"])
            src_type_match = (top.get("source_type") == item["expected_source_type"])
            src_ref_match = (top.get("source_reference") == item["expected_src_ref"])
            subj_match = (top_subj == item["expected_subject"])

            passed = subj_match and is_fact_match and src_type_match and src_ref_match
            results.append({
                "id": item["id"],
                "dimension": dim,
                "domain": item["domain"],
                "lang": item["lang"],
                "query": q,
                "expected_subject": item["expected_subject"],
                "retrieved_subject": top_subj,
                "rank": rank,
                "top1_match": rank == 1,
                "top3_match": bool(rank and rank <= 3),
                "top5_match": bool(rank and rank <= 5),
                "provenance_intact": src_type_match and src_ref_match,
                "trust_status_correct": is_fact_match,
                "passed": passed
            })

        else:
            r = requests.get(f"{API_BASE}/tars/memory", params={"query": q, "memory_type": "LONG_TERM", "top_k": 5}).json().get("memories", [])
            top = r[0] if r else {}
            top_subj = top.get("subject", "")
            top_content = top.get("content", "")

            rank = None
            for idx, cand in enumerate(r):
                if cand.get("subject") == item["expected_subject"]:
                    rank = idx + 1
                    break

            tokens_present = all(tok in top_content for tok in item.get("expected_tokens", []))
            not_forbidden = True
            if "forbidden_subject" in item:
                not_forbidden = (top_subj != item["forbidden_subject"])

            passed = (rank == 1) and tokens_present and not_forbidden

            results.append({
                "id": item["id"],
                "dimension": dim,
                "domain": item["domain"],
                "lang": item["lang"],
                "query": q,
                "expected_subject": item["expected_subject"],
                "retrieved_subject": top_subj,
                "rank": rank,
                "top1_match": rank == 1,
                "top3_match": bool(rank and rank <= 3),
                "top5_match": bool(rank and rank <= 5),
                "tokens_verified": tokens_present,
                "forbidden_avoided": not_forbidden,
                "passed": passed
            })

    return results


if __name__ == "__main__":
    NAMESPACE = f"tars004_{int(time.time())}"
    print(f"=== Starting TARS-004 Acceptance Test (Namespace: {NAMESPACE}) ===")

    # Backup snapshot
    try:
        bak_res = requests.post(f"{API_BASE}/tars/permissions/backup", params={"label": f"pre_{NAMESPACE}"})
        if bak_res.status_code == 200 and bak_res.json().get("success"):
            print(f"[PASSED] Backup snapshot created: {bak_res.json().get('snapshot_id')}")
    except Exception as e:
        print(f"[WARNING] Backup error: {e}")

    # Ingest memories
    test_memories = get_test_memories(NAMESPACE)
    created_memories = {}
    for m in test_memories:
        res = requests.post(f"{API_BASE}/tars/memory", json={
            "subject": m["subject"],
            "content": m["content"],
            "category": m["category"],
            "source_type": m["source_type"],
            "source_reference": m["source_reference"],
            "is_verified_fact": m["is_verified_fact"],
            "confidence": m["confidence"],
            "memory_type": "LONG_TERM"
        })
        if res.status_code == 200 and res.json().get("success"):
            created_memories[m["id"]] = res.json()["memory"]

    print(f"Stored {len(created_memories)} test memories across 6 domains in namespace {NAMESPACE}.")

    # Ingest Contradictory Test Documents for Dimension F
    doc_a_text = f"Official Campus Contract {NAMESPACE}: The dedicated dark fiber link bandwidth is certified at 40 Gbps symmetrical throughput."
    doc_b_text = f"Official Campus Audit Report {NAMESPACE}: The dedicated dark fiber link bandwidth is measured at 10 Gbps due to optical transceiver constraints."

    requests.post(
        f"{API_BASE}/tars/knowledge/ingest-text",
        json={"title": f"{NAMESPACE}_Fiber_Bandwidth_Contract", "content": doc_a_text, "source_reference": f"contract_{NAMESPACE}_fiber"}
    )
    requests.post(
        f"{API_BASE}/tars/knowledge/ingest-text",
        json={"title": f"{NAMESPACE}_Fiber_Bandwidth_Audit", "content": doc_b_text, "source_reference": f"audit_{NAMESPACE}_fiber"}
    )

    # Test Dimension F
    res_search_chunks = requests.get(
        f"{API_BASE}/tars/knowledge/search",
        params={"query": f"What is the certified bandwidth of the dedicated dark fiber link in {NAMESPACE} campus?", "top_k": 5}
    )
    chunks_found = res_search_chunks.json().get("results", [])
    both_docs_preserved = (
        any(f"{NAMESPACE}_Fiber_Bandwidth_Contract" in c.get("document_title", "") for c in chunks_found) and
        any(f"{NAMESPACE}_Fiber_Bandwidth_Audit" in c.get("document_title", "") for c in chunks_found)
    )
    has_conflict_flag = any(c.get("has_conflict") or "CONFLICT" in c.get("citation", "") for c in chunks_found)
    dim_f_passed = both_docs_preserved and has_conflict_flag
    print(f"[{'PASSED' if dim_f_passed else 'FAILED'}] F. Contradictory Sources Preservation")

    # Robustness checks
    robustness_tests = [
        {"type": "empty", "query": "", "label": "Empty query"},
        {"type": "short", "query": "IP", "label": "Very short query"},
        {"type": "long", "query": f"In regards to the system architecture and network infrastructure of {NAMESPACE}, could you please provide a comprehensive breakdown of all the security rules and firewall configurations that govern how inbound connections on port 2222 are managed across the subnet range?", "label": "Long paragraph query"},
        {"type": "repeated", "query": f"firewall firewall firewall ingress SSH port 2222 {NAMESPACE} firewall", "label": "Repeated words"},
        {"type": "typo", "query": f"what is the firwll ingrss ssh rule on prt 2222 for {NAMESPACE}?", "label": "Misspelled query"},
        {"type": "missing_id", "query": "What is the static IPv4 address of interface eth0?", "label": "Missing host identifier"},
        {"type": "conflicting_id", "query": f"What is the MTU of interface eth0 on cluster node Beta {NAMESPACE}?", "label": "Conflicting identifiers"},
        {"type": "unsupported_lang", "query": "Ποια είναι η διαμόρφωση του δικτύου στο σύστημα;", "label": "Unsupported alphabet (Greek)"}
    ]

    robustness_results = []
    for rb in robustness_tests:
        r = requests.get(f"{API_BASE}/tars/memory", params={"query": rb["query"], "memory_type": "LONG_TERM", "top_k": 3})
        robustness_results.append({
            "type": rb["type"],
            "label": rb["label"],
            "query": rb["query"][:60],
            "http_status": r.status_code,
            "results_count": len(r.json().get("memories", [])) if r.status_code == 200 else 0,
            "passed": r.status_code == 200
        })

    rob_acc = sum(1 for r in robustness_results if r["passed"]) / len(robustness_results)
    print(f"[{'PASSED' if rob_acc == 1.0 else 'FAILED'}] Robustness Checks ({rob_acc*100:.1f}%)")

    # Run Pre-restart evaluation
    pre_results = execute_evaluation_battery(NAMESPACE)

    with open("tests/tars_004_state.json", "w", encoding="utf-8") as f:
        json.dump({
            "namespace": NAMESPACE,
            "pre_results": pre_results,
            "robustness_results": robustness_results,
            "dim_f_passed": dim_f_passed
        }, f, indent=2, ensure_ascii=False)

    print(f"[INFO] Pre-restart evaluation complete ({len(pre_results)} items recorded). State saved to tests/tars_004_state.json.")
