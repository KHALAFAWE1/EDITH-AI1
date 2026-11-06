import ast
import json
import subprocess
import sys
import tempfile
import uuid
from datetime import datetime
from typing import Any, Dict, List, Optional

from sqlalchemy.orm import Session

from app.models.adaptive_learning import (
    EvaluationRun,
    ExperienceRecord,
    LearningRecord,
    MemoryRecord,
)
from app.services.knowledge_service import search_knowledge_chunks
from app.services.memory_service import hybrid_text_similarity, search_memories

FORBIDDEN_SANDBOX_MODULES = {
    "subprocess",
    "shutil",
    "socket",
    "requests",
    "httpx",
    "urllib",
    "ctypes",
    "multiprocessing",
}


def run_sandboxed_code_test(code_snippet: str, test_assertion: str = "", timeout_sec: int = 4) -> Dict[str, Any]:
    """
    Executes a Python code snippet + test assertions in an isolated temporary directory
    with AST static safety inspection and a strict subprocess timeout.
    """
    full_code = f"{code_snippet}\n\n{test_assertion}".strip()
    if not full_code:
        return {"passed": False, "error": "Empty code snippet.", "output": ""}

    # 1. Static AST check for dangerous imports or os system calls
    try:
        tree = ast.parse(full_code)
        for node in ast.walk(tree):
            if isinstance(node, ast.Import):
                for alias in node.names:
                    root_mod = alias.name.split(".")[0]
                    if root_mod in FORBIDDEN_SANDBOX_MODULES:
                        return {
                            "passed": False,
                            "blocked_by_sandbox": True,
                            "error": f"Sandbox blocked import of restricted module '{root_mod}'.",
                            "output": "",
                        }
            elif isinstance(node, ast.ImportFrom):
                root_mod = (node.module or "").split(".")[0]
                if root_mod in FORBIDDEN_SANDBOX_MODULES:
                    return {
                        "passed": False,
                        "blocked_by_sandbox": True,
                        "error": f"Sandbox blocked import from restricted module '{root_mod}'.",
                        "output": "",
                    }
            elif isinstance(node, ast.Call):
                if isinstance(node.func, ast.Name) and node.func.id in ("eval", "exec", "__import__"):
                    return {
                        "passed": False,
                        "blocked_by_sandbox": True,
                        "error": f"Sandbox blocked dynamic call '{node.func.id}'.",
                        "output": "",
                    }
    except SyntaxError as se:
        return {"passed": False, "error": f"SyntaxError: {se}", "output": ""}

    # 2. Isolated subprocess execution
    with tempfile.TemporaryDirectory(prefix="tars_eval_sandbox_") as tmpdir:
        script_path = f"{tmpdir}/eval_check.py"
        with open(script_path, "w", encoding="utf-8") as f:
            f.write(full_code + "\nprint('TARS_SANDBOX_OK')\n")

        try:
            proc = subprocess.run(
                [sys.executable, "-I", script_path],
                cwd=tmpdir,
                capture_output=True,
                text=True,
                timeout=timeout_sec,
            )
            passed = proc.returncode == 0 and "TARS_SANDBOX_OK" in (proc.stdout or "")
            return {
                "passed": passed,
                "return_code": proc.returncode,
                "output": (proc.stdout or "").strip(),
                "error": (proc.stderr or "").strip() if not passed else None,
            }
        except subprocess.TimeoutExpired:
            return {
                "passed": False,
                "error": f"Sandbox execution timed out after {timeout_sec}s.",
                "output": "",
            }
        except Exception as e:
            return {"passed": False, "error": str(e), "output": ""}


def evaluate_answer_against_sources(
    db: Session,
    question: str,
    candidate_answer: str,
) -> Dict[str, Any]:
    """
    Verifies a candidate answer against trusted sources in TARS Semantic/Long-Term Memory
    and Knowledge Documents.
    """
    mem_hits = search_memories(db, query=question, only_verified_facts=True, top_k=3, min_similarity=0.1)
    doc_hits = search_knowledge_chunks(db, query=question, top_k=3, min_similarity=0.1)

    best_score = 0.0
    matched_source = None

    for m in mem_hits:
        sim = hybrid_text_similarity(m["content"], candidate_answer)
        if sim > best_score:
            best_score = sim
            matched_source = f"Memory[{m['memory_uid']}]: {m['subject']}"

    for d in doc_hits:
        sim = hybrid_text_similarity(d["content"], candidate_answer)
        if sim > best_score:
            best_score = sim
            matched_source = d["citation"]

    return {
        "question": question,
        "verified_against_source": best_score >= 0.65,
        "accuracy_score": round(best_score, 4),
        "matched_source": matched_source or "No matching verified source found",
    }


def run_evaluation_suite(
    db: Session,
    eval_type: str = "comprehensive",
    custom_qa_tests: Optional[List[Dict[str, str]]] = None,
    code_tests: Optional[List[Dict[str, str]]] = None,
) -> Dict[str, Any]:
    """
    Runs a comprehensive evaluation suite:
    1. Verified Learning Records re-verification (checks if approved knowledge is still accurately retrieved)
    2. Custom Q&A source verification tests (if provided)
    3. Isolated sandboxed code verification tests (if provided or default integrity test)
    4. Task success rate calculation from ExperienceRecord history
    5. Regression comparison against the most recent previous EvaluationRun
    """
    previous_run = (
        db.query(EvaluationRun)
        .filter(EvaluationRun.eval_type == eval_type)
        .order_by(EvaluationRun.id.desc())
        .first()
    )
    previous_score = previous_run.overall_score if previous_run else None

    test_details: List[Dict[str, Any]] = []
    passed_count = 0
    total_count = 0
    score_sum = 0.0

    # 1. Re-verify approved learning records against live memory
    approved_learnings = (
        db.query(LearningRecord)
        .filter(LearningRecord.approval_status == "APPROVED")
        .order_by(LearningRecord.id.desc())
        .limit(20)
        .all()
    )
    for lr in approved_learnings:
        total_count += 1
        retrieved = search_memories(db, query=lr.verification_question, top_k=2, min_similarity=0.1)
        top_ans = retrieved[0]["content"] if retrieved else ""
        sim = hybrid_text_similarity(lr.expected_answer, top_ans) if top_ans else 0.0
        ok = sim >= 0.70
        if ok:
            passed_count += 1
        score_sum += sim
        test_details.append({
            "test_category": "memory_retention",
            "target": lr.learning_uid,
            "question": lr.verification_question,
            "score": round(sim, 4),
            "passed": ok,
        })

    # 2. Custom Q&A tests against sources
    for qa in custom_qa_tests or []:
        total_count += 1
        q = qa.get("question", "")
        expected = qa.get("expected_answer", "")
        candidate = qa.get("candidate_answer", "")
        if expected and candidate:
            sim = hybrid_text_similarity(expected, candidate)
            ok = sim >= 0.70
            matched_src = "expected_reference"
        else:
            src_res = evaluate_answer_against_sources(db, q, candidate)
            sim = src_res["accuracy_score"]
            ok = src_res["verified_against_source"]
            matched_src = src_res["matched_source"]

        if ok:
            passed_count += 1
        score_sum += sim
        test_details.append({
            "test_category": "source_verification",
            "question": q,
            "score": round(sim, 4),
            "passed": ok,
            "source": matched_src,
        })

    # 3. Sandboxed code verification tests
    effective_code_tests = code_tests if code_tests is not None else [
        {
            "name": "vector_similarity_self_check",
            "code": "def dot(a, b):\n    return sum(x*y for x, y in zip(a, b))",
            "assertion": "assert abs(dot([1.0, 0.0], [1.0, 0.0]) - 1.0) < 1e-6",
        }
    ]
    for ct in effective_code_tests:
        total_count += 1
        res = run_sandboxed_code_test(ct.get("code", ""), ct.get("assertion", ""))
        ok = bool(res.get("passed"))
        sc = 1.0 if ok else 0.0
        if ok:
            passed_count += 1
        score_sum += sc
        test_details.append({
            "test_category": "code_sandbox",
            "name": ct.get("name", "sandbox_check"),
            "score": sc,
            "passed": ok,
            "error": res.get("error"),
        })

    overall_score = round(score_sum / max(1, total_count), 4)

    # 4. Task success rate from ExperienceRecord
    experiences = db.query(ExperienceRecord).order_by(ExperienceRecord.id.desc()).limit(100).all()
    if experiences:
        succ_exp = sum(1 for e in experiences if (e.evaluation_score or 0.0) >= 0.65 and e.errors in ("None", "", None))
        task_success_rate = round(succ_exp / len(experiences), 4)
    else:
        task_success_rate = 1.0 if passed_count == total_count else overall_score

    # 5. Regression detection
    score_delta = round(overall_score - previous_score, 4) if previous_score is not None else 0.0
    regression_detected = bool(previous_score is not None and score_delta < -0.05)

    summary = (
        f"Evaluation '{eval_type}' completed: {passed_count}/{total_count} checks passed "
        f"(Score: {round(overall_score * 100, 1)}% | Task Success Rate: {round(task_success_rate * 100, 1)}%). "
        + (
            f"WARNING: Regression detected ({round(score_delta * 100, 1)}% drop vs previous run)."
            if regression_detected
            else "No performance regression detected."
        )
    )

    run_rec = EvaluationRun(
        eval_uid=f"eval_{uuid.uuid4().hex[:12]}",
        eval_type=eval_type,
        total_tests=total_count,
        passed_tests=passed_count,
        overall_score=overall_score,
        previous_score=previous_score,
        score_delta=score_delta,
        regression_detected=regression_detected,
        task_success_rate=task_success_rate,
        details_json=json.dumps(test_details, ensure_ascii=False),
        report_summary=summary,
    )
    db.add(run_rec)
    db.commit()
    db.refresh(run_rec)

    return serialize_evaluation_run(run_rec)


def serialize_evaluation_run(run: EvaluationRun) -> Dict[str, Any]:
    try:
        details = json.loads(run.details_json or "[]")
    except Exception:
        details = []
    return {
        "id": run.id,
        "eval_uid": run.eval_uid,
        "eval_type": run.eval_type,
        "total_tests": run.total_tests,
        "passed_tests": run.passed_tests,
        "overall_score": run.overall_score,
        "previous_score": run.previous_score,
        "score_delta": run.score_delta,
        "regression_detected": bool(run.regression_detected),
        "task_success_rate": run.task_success_rate,
        "details": details,
        "report_summary": run.report_summary,
        "created_at": run.created_at.isoformat() if run.created_at else None,
    }
