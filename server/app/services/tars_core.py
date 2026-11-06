import json
import os
import time
import uuid
from datetime import datetime
from typing import Any, Callable, Dict, List, Optional

import requests
from sqlalchemy.orm import Session

from app.config import DEFAULT_GEMINI_MODEL, get_gemini_api_key
from app.models.adaptive_learning import ModelRoutingLog
from app.services.knowledge_service import search_knowledge_chunks
from app.services.learning_engine import find_similar_experiences, record_experience
from app.services.memory_service import (
    detect_sensitive_data,
    search_memories,
    store_memory,
)

ROUTING_CONFIG_FILE = os.path.abspath(
    os.path.join(os.path.dirname(__file__), "..", "..", "tars_routing_config.json")
)

DEFAULT_ROUTING_CONFIG: Dict[str, Any] = {
    "routing_policy": "HYBRID_AUTO",  # HYBRID_AUTO | LOCAL_FIRST | CLOUD_FIRST | LOCAL_ONLY
    "ollama_base_url": os.getenv("OLLAMA_BASE_URL", "http://127.0.0.1:11434"),
    "preferred_local_model": os.getenv("OLLAMA_MODEL", "llama3.2"),
    "preferred_cloud_provider": "GEMINI",  # GEMINI | OPENAI_COMPATIBLE
    "openai_base_url": os.getenv("OPENAI_BASE_URL", "https://api.openai.com/v1"),
    "openai_model": os.getenv("OPENAI_MODEL", "gpt-4o-mini"),
    "block_private_data_to_cloud": True,
    "auto_fallback": True,
    "inject_memory_and_knowledge": True,
}


def load_routing_config() -> Dict[str, Any]:
    cfg = dict(DEFAULT_ROUTING_CONFIG)
    if os.path.exists(ROUTING_CONFIG_FILE):
        try:
            with open(ROUTING_CONFIG_FILE, "r", encoding="utf-8") as f:
                saved = json.load(f)
                if isinstance(saved, dict):
                    cfg.update(saved)
        except Exception:
            pass
    return cfg


def save_routing_config(updates: Dict[str, Any]) -> Dict[str, Any]:
    cfg = load_routing_config()
    for k, v in updates.items():
        if k in DEFAULT_ROUTING_CONFIG and v is not None:
            cfg[k] = v
    try:
        with open(ROUTING_CONFIG_FILE, "w", encoding="utf-8") as f:
            json.dump(cfg, f, indent=2, ensure_ascii=False)
    except Exception:
        pass
    return cfg


def probe_ollama_status(base_url: Optional[str] = None, timeout: float = 1.2) -> Dict[str, Any]:
    """
    Probes the local Ollama server (/api/tags) to check if local LLM inference is online.
    """
    cfg = load_routing_config()
    url = (base_url or cfg.get("ollama_base_url") or "http://127.0.0.1:11434").rstrip("/")
    try:
        resp = requests.get(f"{url}/api/tags", timeout=timeout)
        if resp.status_code == 200:
            data = resp.json()
            models = [m.get("name") for m in data.get("models", []) if m.get("name")]
            return {
                "available": True,
                "base_url": url,
                "models": models,
                "active_model": models[0] if models else cfg.get("preferred_local_model", "llama3.2"),
            }
    except Exception:
        pass
    return {
        "available": False,
        "base_url": url,
        "models": [],
        "active_model": None,
    }


def call_ollama_local(
    prompt: str,
    system_prompt: str,
    history: Optional[List[Dict[str, str]]] = None,
    model_name: Optional[str] = None,
    base_url: Optional[str] = None,
    timeout: float = 20.0,
) -> Dict[str, Any]:
    """
    Calls local Ollama /api/chat endpoint for offline local LLM execution.
    """
    cfg = load_routing_config()
    status = probe_ollama_status(base_url=base_url)
    if not status["available"]:
        raise RuntimeError("Local Ollama service is not reachable at " + status["base_url"])

    chosen_model = model_name or status["active_model"] or cfg.get("preferred_local_model", "llama3.2")
    messages = [{"role": "system", "content": system_prompt}]
    for h in (history or [])[-8:]:
        role = h.get("role", "user") if isinstance(h, dict) else getattr(h, "role", "user")
        content = h.get("content", "") if isinstance(h, dict) else getattr(h, "content", "")
        messages.append({"role": "assistant" if role in ("assistant", "model") else "user", "content": content})
    messages.append({"role": "user", "content": prompt})

    resp = requests.post(
        f"{status['base_url']}/api/chat",
        json={"model": chosen_model, "messages": messages, "stream": False},
        timeout=timeout,
    )
    if resp.status_code != 200:
        raise RuntimeError(f"Ollama HTTP {resp.status_code}: {resp.text[:160]}")

    data = resp.json()
    reply_text = data.get("message", {}).get("content", "")
    if not reply_text:
        raise RuntimeError("Ollama returned an empty response.")

    return {
        "success": True,
        "reply": reply_text,
        "provider": "LOCAL_OLLAMA",
        "model": chosen_model,
        "engine": f"TARS Local AI Core (Ollama: {chosen_model})",
    }


def build_adaptive_context_block(db: Session, query: str) -> Dict[str, Any]:
    """
    Retrieves relevant Long-Term/Semantic Memories, Knowledge Document Chunks (with citations),
    and Past Similar Experiences to ground TARS's response in verified facts.
    """
    all_memories = search_memories(db, query=query, top_k=6, min_similarity=0.18)
    # Filter out raw conversational echo messages from knowledge grounding
    memories = [
        m for m in all_memories
        if m.get("subject") != "recent_operator_message"
        and m.get("memory_type") in ("LONG_TERM", "SEMANTIC", "EPISODIC")
    ][:4]
    knowledge_chunks = search_knowledge_chunks(db, query=query, top_k=3, min_similarity=0.18)
    similar_experiences = find_similar_experiences(db, query=query, top_k=2, min_similarity=0.22)

    lines: List[str] = []
    citations: List[str] = []

    if memories:
        lines.append("[TARS VERIFIED MEMORY RETRIEVAL]:")
        for m in memories:
            tag = "VERIFIED FACT" if m.get("is_verified_fact") else "INFERENCE"
            lines.append(f"- [{tag} | {m['memory_type']} | Source: {m['source_type']}] {m['subject']}: {m['content']}")
            citations.append(f"Memory({m['memory_uid']}:{m['subject']})")

    if knowledge_chunks:
        lines.append("\n[TARS DOCUMENT KNOWLEDGE BASE (CITE THESE SOURCES)]:")
        for kc in knowledge_chunks:
            lines.append(f"- {kc['citation']}: {kc['content']}")
            citations.append(kc["citation"])

    if similar_experiences:
        lines.append("\n[TARS PAST OPERATIONAL EXPERIENCES & LESSONS]:")
        for exp in similar_experiences:
            lines.append(f"- Task: {exp['task_description']} | Lesson: {exp['lessons_extracted']}")

    return {
        "context_text": "\n".join(lines),
        "memories_used": memories,
        "knowledge_chunks_used": knowledge_chunks,
        "experiences_used": similar_experiences,
        "citations": citations,
    }


def log_routing_decision(
    db: Session,
    task_type: str,
    routing_policy: str,
    provider_chosen: str,
    model_name: str,
    routing_reason: str,
    contains_private_data: bool = False,
    privacy_redacted: bool = False,
    fallback_triggered: bool = False,
    latency_ms: float = 0.0,
    success: bool = True,
) -> Dict[str, Any]:
    rec = ModelRoutingLog(
        routing_uid=f"rt_{uuid.uuid4().hex[:12]}",
        task_type=task_type,
        routing_policy=routing_policy,
        provider_chosen=provider_chosen,
        model_name=model_name,
        routing_reason=routing_reason,
        contains_private_data=bool(contains_private_data),
        privacy_redacted=bool(privacy_redacted),
        fallback_triggered=bool(fallback_triggered),
        latency_ms=round(float(latency_ms), 2),
        success=bool(success),
    )
    db.add(rec)
    db.commit()
    db.refresh(rec)
    return serialize_routing_log(rec)


def serialize_routing_log(rec: ModelRoutingLog) -> Dict[str, Any]:
    return {
        "id": rec.id,
        "routing_uid": rec.routing_uid,
        "task_type": rec.task_type,
        "routing_policy": rec.routing_policy,
        "provider_chosen": rec.provider_chosen,
        "model_name": rec.model_name,
        "routing_reason": rec.routing_reason,
        "contains_private_data": bool(rec.contains_private_data),
        "privacy_redacted": bool(rec.privacy_redacted),
        "fallback_triggered": bool(rec.fallback_triggered),
        "latency_ms": rec.latency_ms,
        "success": bool(rec.success),
        "created_at": rec.created_at.isoformat() if rec.created_at else None,
    }


def route_and_execute_chat(
    db: Session,
    prompt: str,
    history: List[Any],
    personality: Dict[str, int],
    system_prompt_builder: Callable[[Optional[Dict[str, int]]], str],
    cloud_gemini_callable: Callable[..., Dict[str, Any]],
    local_fallback_callable: Callable[..., Dict[str, Any]],
    force_policy: Optional[str] = None,
) -> Dict[str, Any]:
    """
    TARS Hybrid AI Core — Intelligent Model Router:
    1. Retrieves relevant Long-Term/Semantic Memories, Document Chunks, and Past Experiences.
    2. Stores current user message in Short-Term Memory.
    3. Inspects prompt for sensitive/private data (`detect_sensitive_data`).
    4. Selects between Local AI Provider (Ollama / Local Knowledge Core) and Cloud AI Provider (Gemini)
       based on `routing_policy`, privacy sensitivity, and provider availability.
    5. Logs the exact routing decision reason in `ModelRoutingLog` and records an `ExperienceRecord`.
    """
    t0 = time.perf_counter()
    cfg = load_routing_config()
    policy = (force_policy or cfg.get("routing_policy") or "HYBRID_AUTO").upper()

    # 1. Store incoming prompt in Short-Term Memory (non-sensitive only)
    has_sensitive, sens_types, redacted_prompt = detect_sensitive_data(prompt)
    if not has_sensitive:
        try:
            store_memory(
                db=db,
                content=prompt,
                memory_type="SHORT_TERM",
                subject="recent_operator_message",
                category="conversation",
                is_verified_fact=False,
                fact_or_inference="INFERENCE",
                source_type="conversation",
                source_reference="active_chat",
                ttl_hours=24,
            )
        except Exception:
            pass

    # 2. Retrieve Adaptive Context (Memories + Document Citations + Past Experiences)
    adaptive_ctx = build_adaptive_context_block(db, prompt)
    base_sys_prompt = system_prompt_builder(personality)
    if adaptive_ctx["context_text"]:
        augmented_sys_prompt = f"{base_sys_prompt}\n\n{adaptive_ctx['context_text']}"
    else:
        augmented_sys_prompt = base_sys_prompt

    api_key = get_gemini_api_key()
    has_cloud_key = bool(api_key and len(api_key) > 10)
    ollama_info = probe_ollama_status()
    has_ollama = bool(ollama_info["available"])

    provider_chosen = "LOCAL_DETERMINISTIC"
    model_used = "TARS-Local-Core"
    routing_reason = ""
    fallback_triggered = False
    privacy_redacted = False
    result: Dict[str, Any] = {}

    # 3. Privacy check: Never send unredacted private/sensitive data to external cloud
    if has_sensitive and cfg.get("block_private_data_to_cloud", True) and policy != "LOCAL_ONLY":
        privacy_redacted = True

    # 4. Route according to policy
    if policy == "LOCAL_ONLY" or (has_sensitive and cfg.get("block_private_data_to_cloud", True) and not privacy_redacted):
        if has_ollama:
            try:
                result = call_ollama_local(prompt, augmented_sys_prompt, history)
                provider_chosen = "LOCAL_OLLAMA"
                model_used = result.get("model", "ollama-local")
                routing_reason = "Routed to Local Ollama Provider per LOCAL_ONLY / Privacy policy."
            except Exception as e:
                fallback_triggered = True
                result = _answer_with_local_knowledge_and_fallback(
                    db, prompt, personality, adaptive_ctx, local_fallback_callable
                )
                provider_chosen = "LOCAL_KNOWLEDGE_CORE"
                model_used = result.get("model", "TARS-Local-Core")
                routing_reason = f"Local Ollama failed ({e}); fell back to TARS Local Knowledge & Telemetry Core."
        else:
            result = _answer_with_local_knowledge_and_fallback(
                db, prompt, personality, adaptive_ctx, local_fallback_callable
            )
            provider_chosen = "LOCAL_KNOWLEDGE_CORE"
            model_used = result.get("model", "TARS-Local-Core")
            routing_reason = "LOCAL_ONLY policy active (Ollama offline); handled by TARS Local Knowledge & Telemetry Core."

    elif policy == "LOCAL_FIRST":
        if has_ollama:
            try:
                result = call_ollama_local(prompt, augmented_sys_prompt, history)
                provider_chosen = "LOCAL_OLLAMA"
                model_used = result.get("model", "ollama-local")
                routing_reason = "LOCAL_FIRST policy selected active local Ollama model."
            except Exception as e:
                fallback_triggered = True
                if has_cloud_key:
                    cloud_prompt = redacted_prompt if has_sensitive else prompt
                    result = cloud_gemini_callable(cloud_prompt, history, api_key, db, personality, adaptive_ctx["context_text"])
                    provider_chosen = "CLOUD_GEMINI"
                    model_used = result.get("model", DEFAULT_GEMINI_MODEL)
                    routing_reason = f"Local Ollama failed ({e}); fell back to Cloud Gemini Provider."
                else:
                    result = _answer_with_local_knowledge_and_fallback(
                        db, prompt, personality, adaptive_ctx, local_fallback_callable
                    )
                    provider_chosen = "LOCAL_KNOWLEDGE_CORE"
                    model_used = result.get("model", "TARS-Local-Core")
                    routing_reason = "Local Ollama failed and no Cloud API key configured; handled by Local Knowledge Core."
        elif has_cloud_key:
            fallback_triggered = True
            cloud_prompt = redacted_prompt if has_sensitive else prompt
            try:
                result = cloud_gemini_callable(cloud_prompt, history, api_key, db, personality, adaptive_ctx["context_text"])
                provider_chosen = "CLOUD_GEMINI"
                model_used = result.get("model", DEFAULT_GEMINI_MODEL)
                routing_reason = "LOCAL_FIRST policy: Ollama offline, fell back to Cloud Gemini Provider."
            except Exception as e:
                result = _answer_with_local_knowledge_and_fallback(
                    db, prompt, personality, adaptive_ctx, local_fallback_callable
                )
                provider_chosen = "LOCAL_KNOWLEDGE_CORE"
                model_used = result.get("model", "TARS-Local-Core")
                routing_reason = f"Cloud fallback failed ({e}); handled by TARS Local Knowledge Core."
        else:
            result = _answer_with_local_knowledge_and_fallback(
                db, prompt, personality, adaptive_ctx, local_fallback_callable
            )
            provider_chosen = "LOCAL_KNOWLEDGE_CORE"
            model_used = result.get("model", "TARS-Local-Core")
            routing_reason = "LOCAL_FIRST policy: Handled by TARS Local Knowledge & Telemetry Core."

    else:
        # HYBRID_AUTO or CLOUD_FIRST
        p_lower = prompt.lower().strip()
        is_direct_local_cmd = any(
            p_lower.startswith(prefix)
            for prefix in ("افتح ", "open ", "اقفل ", "أغلق ", "close ")
        )
        if is_direct_local_cmd:
            result = local_fallback_callable(prompt, personality, db)
            provider_chosen = "LOCAL_COMMAND_CORE"
            model_used = result.get("model", "TARS-Local-Core")
            routing_reason = "Direct OS command detected; routed directly to TARS Local Command Core for zero-latency execution."
        elif has_cloud_key:
            cloud_prompt = redacted_prompt if has_sensitive else prompt
            try:
                result = cloud_gemini_callable(cloud_prompt, history, api_key, db, personality, adaptive_ctx["context_text"])
                provider_chosen = "CLOUD_GEMINI"
                model_used = result.get("model", DEFAULT_GEMINI_MODEL)
                routing_reason = (
                    "Routed to Cloud Gemini Provider with sensitive tokens redacted."
                    if has_sensitive
                    else "Routed to Cloud Gemini Provider (HYBRID_AUTO high-reasoning path)."
                )
            except Exception as e:
                fallback_triggered = True
                if has_ollama:
                    try:
                        result = call_ollama_local(prompt, augmented_sys_prompt, history)
                        provider_chosen = "LOCAL_OLLAMA"
                        model_used = result.get("model", "ollama-local")
                        routing_reason = f"Cloud Gemini failed ({e}); fell back to Local Ollama Provider."
                    except Exception:
                        result = _answer_with_local_knowledge_and_fallback(
                            db, prompt, personality, adaptive_ctx, local_fallback_callable
                        )
                        provider_chosen = "LOCAL_KNOWLEDGE_CORE"
                        model_used = result.get("model", "TARS-Local-Core")
                        routing_reason = f"Cloud Gemini and Ollama unavailable; fell back to Local Knowledge Core."
                else:
                    result = _answer_with_local_knowledge_and_fallback(
                        db, prompt, personality, adaptive_ctx, local_fallback_callable
                    )
                    provider_chosen = "LOCAL_KNOWLEDGE_CORE"
                    model_used = result.get("model", "TARS-Local-Core")
                    routing_reason = f"Cloud Gemini failed ({e}); fell back to Local Knowledge & Telemetry Core."
        elif has_ollama:
            try:
                result = call_ollama_local(prompt, augmented_sys_prompt, history)
                provider_chosen = "LOCAL_OLLAMA"
                model_used = result.get("model", "ollama-local")
                routing_reason = "Cloud key not configured; routed automatically to Local Ollama Provider."
            except Exception as e:
                fallback_triggered = True
                result = _answer_with_local_knowledge_and_fallback(
                    db, prompt, personality, adaptive_ctx, local_fallback_callable
                )
                provider_chosen = "LOCAL_KNOWLEDGE_CORE"
                model_used = result.get("model", "TARS-Local-Core")
                routing_reason = f"Local Ollama failed ({e}); handled by Local Knowledge & Telemetry Core."
        else:
            result = _answer_with_local_knowledge_and_fallback(
                db, prompt, personality, adaptive_ctx, local_fallback_callable
            )
            provider_chosen = "LOCAL_KNOWLEDGE_CORE"
            model_used = result.get("model", "TARS-Local-Core")
            routing_reason = "No external Cloud API key or Ollama daemon active; handled by TARS Local Knowledge, Memory & Telemetry Core."

    latency_ms = (time.perf_counter() - t0) * 1000.0
    routing_log = log_routing_decision(
        db=db,
        task_type="chat",
        routing_policy=policy,
        provider_chosen=provider_chosen,
        model_name=model_used,
        routing_reason=routing_reason,
        contains_private_data=has_sensitive,
        privacy_redacted=privacy_redacted,
        fallback_triggered=fallback_triggered,
        latency_ms=latency_ms,
        success=bool(result.get("success", True)),
    )

    # Record operational experience
    try:
        record_experience(
            db=db,
            task_description=f"Chat query routed via {provider_chosen}",
            input_text=redacted_prompt if has_sensitive else prompt,
            actual_result=(result.get("reply") or "")[:500],
            context={
                "provider": provider_chosen,
                "model": model_used,
                "citations": adaptive_ctx["citations"],
            },
            actions_taken=["memory_retrieval", "knowledge_search", f"route:{provider_chosen}"],
            tools_used=[provider_chosen, "TARS_Memory_System", "TARS_Knowledge_Base"],
            expected_result="Context-grounded response",
            evaluation_score=0.9 if result.get("success") else 0.6,
            errors="None" if result.get("success") else str(result.get("error", "LLM_FALLBACK")),
        )
    except Exception:
        pass

    result["routing"] = routing_log
    result["citations"] = adaptive_ctx["citations"]
    result["memories_used_count"] = len(adaptive_ctx["memories_used"])
    result["knowledge_chunks_used_count"] = len(adaptive_ctx["knowledge_chunks_used"])
    return result


def _answer_with_local_knowledge_and_fallback(
    db: Session,
    prompt: str,
    personality: Dict[str, int],
    adaptive_ctx: Dict[str, Any],
    local_fallback_callable: Callable[..., Dict[str, Any]],
) -> Dict[str, Any]:
    """
    If relevant verified memories or ingested knowledge document chunks match the user's question,
    synthesizes a direct, source-cited local response before falling back to diagnostic telemetry.
    """
    memories = adaptive_ctx.get("memories_used", [])
    chunks = adaptive_ctx.get("knowledge_chunks_used", [])

    # Check if we have strong verified memory or document hits (excluding raw prompt echo)
    strong_memories = [
        m for m in memories
        if (m.get("similarity") or 0.0) >= 0.25
        and m.get("subject") != "recent_operator_message"
        and m.get("memory_type") in ("LONG_TERM", "SEMANTIC")
    ]
    strong_chunks = [c for c in chunks if (c.get("similarity") or 0.0) >= 0.25]

    if strong_memories or strong_chunks:
        parts: List[str] = ["[TARS Verified Local Knowledge & Memory Synthesis]"]
        if strong_memories:
            for m in strong_memories[:3]:
                badge = "حقيقة موثقة (FACT)" if m.get("is_verified_fact") else "استنتاج (INFERENCE)"
                parts.append(f"• [{badge} — {m['subject']}]: {m['content']}")
        if strong_chunks:
            for c in strong_chunks[:2]:
                parts.append(f"• {c['citation']}:\n  {c['content']}")
        return {
            "success": True,
            "reply": "\n\n".join(parts),
            "model": "TARS-Local-Knowledge-Engine",
            "engine": "TARS Hybrid Memory & Document Synthesis Core (Verified Local Sources)",
            "client_action": None,
        }

    return local_fallback_callable(prompt, personality, db)


def get_hybrid_core_status(db: Session) -> Dict[str, Any]:
    cfg = load_routing_config()
    api_key = get_gemini_api_key()
    has_gemini = bool(api_key and len(api_key) > 10)
    has_openai = bool(os.getenv("OPENAI_API_KEY", "").strip())
    ollama_status = probe_ollama_status()

    recent_logs = (
        db.query(ModelRoutingLog)
        .order_by(ModelRoutingLog.id.desc())
        .limit(15)
        .all()
    )

    return {
        "core_name": "TARS Hybrid Adaptive AI Core",
        "routing_config": cfg,
        "providers": {
            "local_ollama": ollama_status,
            "local_knowledge_telemetry": {
                "available": True,
                "engine": "TARS Local Memory, Document & Telemetry Core",
            },
            "cloud_gemini": {
                "available": has_gemini,
                "configured_model": DEFAULT_GEMINI_MODEL,
                "key_stored_securely_on_server": True,
            },
            "cloud_openai_compatible": {
                "available": has_openai,
                "base_url": cfg.get("openai_base_url"),
                "configured_model": cfg.get("openai_model"),
            },
        },
        "recent_routing_logs": [serialize_routing_log(r) for r in recent_logs],
    }
