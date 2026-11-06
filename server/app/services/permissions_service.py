import json
import os
import time
import uuid
from datetime import datetime
from typing import Any, Dict, List, Optional

from sqlalchemy.orm import Session

from app.models.adaptive_learning import (
    ExperienceRecord,
    ImprovementProposal,
    KnowledgeDocument,
    LearningRecord,
    MemoryRecord,
    PermissionScopeRecord,
)
from app.models.security_log import SecurityLog

DEFAULT_PERMISSION_SCOPES: List[Dict[str, Any]] = [
    {
        "scope_name": "read_only",
        "enabled": True,
        "requires_human_approval": False,
        "description": "قراءة البيانات والحالة والذكريات دون تعديل (Read-only access)",
    },
    {
        "scope_name": "memory_write",
        "enabled": True,
        "requires_human_approval": False,
        "description": "الكتابة في نظام الذاكرة (قصيرة/طويلة المدى والدلالية) مع فحص التكرار والبيانات الحساسة",
    },
    {
        "scope_name": "file_access",
        "enabled": True,
        "requires_human_approval": False,
        "description": "قراءة وتحليل الوثائق المرفوعة (TXT, PDF, DOCX) داخل نطاق المشروع",
    },
    {
        "scope_name": "web_access",
        "enabled": False,
        "requires_human_approval": True,
        "description": "الوصول إلى المصادر الخارجية على الويب عند تفعيله من المستخدم",
    },
    {
        "scope_name": "tool_execution",
        "enabled": True,
        "requires_human_approval": False,
        "description": "تشغيل أدوات TARS المحلية الآمنة وقراءة مقاييس الجهاز",
    },
    {
        "scope_name": "code_modification",
        "enabled": False,
        "requires_human_approval": True,
        "description": "تعديل كود المشروع (يتطلب اقتراح تحسين وموافقة بشرية صريحة)",
    },
    {
        "scope_name": "model_modification",
        "enabled": False,
        "requires_human_approval": True,
        "description": "تغيير النموذج الأساسي أو أوزان النموذج أو إعدادات Fine-Tuning (يتطلب موافقة بشرية)",
    },
    {
        "scope_name": "system_admin",
        "enabled": False,
        "requires_human_approval": True,
        "description": "إدارة الصلاحيات الحساسة وتعديل قاعدة البيانات ونشر نسخ جديدة (يتطلب موافقة بشرية)",
    },
]

BACKUPS_DIR = os.path.abspath(
    os.path.join(os.path.dirname(__file__), "..", "..", "backups")
)
os.makedirs(BACKUPS_DIR, exist_ok=True)

# Simple in-memory rate limiter window: {key: [timestamps]}
_RATE_LIMIT_BUCKETS: Dict[str, List[float]] = {}


def check_rate_limit(key: str, max_requests: int = 60, window_seconds: int = 60) -> bool:
    now = time.time()
    bucket = _RATE_LIMIT_BUCKETS.get(key, [])
    bucket = [t for t in bucket if now - t < window_seconds]
    if len(bucket) >= max_requests:
        _RATE_LIMIT_BUCKETS[key] = bucket
        return False
    bucket.append(now)
    _RATE_LIMIT_BUCKETS[key] = bucket
    return True


def ensure_default_permissions(db: Session) -> List[PermissionScopeRecord]:
    existing = {p.scope_name: p for p in db.query(PermissionScopeRecord).all()}
    created_any = False
    for spec in DEFAULT_PERMISSION_SCOPES:
        if spec["scope_name"] not in existing:
            rec = PermissionScopeRecord(
                scope_name=spec["scope_name"],
                enabled=spec["enabled"],
                requires_human_approval=spec["requires_human_approval"],
                description=spec["description"],
            )
            db.add(rec)
            created_any = True
    if created_any:
        db.commit()
    return db.query(PermissionScopeRecord).order_by(PermissionScopeRecord.id.asc()).all()


def get_all_permissions(db: Session) -> List[Dict[str, Any]]:
    records = ensure_default_permissions(db)
    return [serialize_permission(r) for r in records]


def is_permission_enabled(db: Session, scope_name: str) -> bool:
    ensure_default_permissions(db)
    rec = (
        db.query(PermissionScopeRecord)
        .filter(PermissionScopeRecord.scope_name == scope_name)
        .first()
    )
    return bool(rec and rec.enabled)


def require_permission(db: Session, scope_name: str, actor: str = "TARS_CORE", human_approved: bool = False):
    """
    Verifies that `scope_name` is enabled and, if `requires_human_approval` is True,
    that explicit `human_approved=True` was supplied. Logs to SecurityLog on denial.
    """
    ensure_default_permissions(db)
    rec = (
        db.query(PermissionScopeRecord)
        .filter(PermissionScopeRecord.scope_name == scope_name)
        .first()
    )
    if not rec or not rec.enabled:
        log_security_audit(
            db=db,
            event_type="PERMISSION_DENIED",
            severity="WARNING",
            actor=actor,
            target=scope_name,
            description=f"Blocked action requiring disabled permission scope '{scope_name}'.",
        )
        raise PermissionError(f"Permission scope '{scope_name}' is currently disabled.")

    if rec.requires_human_approval and not human_approved:
        log_security_audit(
            db=db,
            event_type="APPROVAL_REQUIRED",
            severity="WARNING",
            actor=actor,
            target=scope_name,
            description=f"Blocked action on '{scope_name}' because explicit human approval was not provided.",
        )
        raise PermissionError(f"Permission scope '{scope_name}' requires explicit human approval.")


def update_permission_scope(
    db: Session,
    scope_name: str,
    enabled: bool,
    requires_human_approval: Optional[bool] = None,
    actor: str = "human_operator",
) -> Dict[str, Any]:
    ensure_default_permissions(db)
    rec = (
        db.query(PermissionScopeRecord)
        .filter(PermissionScopeRecord.scope_name == scope_name)
        .first()
    )
    if not rec:
        raise ValueError(f"Unknown permission scope '{scope_name}'.")

    old_enabled = rec.enabled
    rec.enabled = bool(enabled)
    if requires_human_approval is not None:
        rec.requires_human_approval = bool(requires_human_approval)
    rec.updated_at = datetime.utcnow()
    db.commit()
    db.refresh(rec)

    log_security_audit(
        db=db,
        event_type="PERMISSION_UPDATED",
        severity="INFO",
        actor=actor,
        target=scope_name,
        description=f"Permission '{scope_name}' changed from enabled={old_enabled} to enabled={rec.enabled}.",
    )
    return serialize_permission(rec)


def log_security_audit(
    db: Session,
    event_type: str,
    severity: str,
    actor: str,
    target: str,
    description: str,
    metadata: Optional[Dict[str, Any]] = None,
):
    try:
        entry = SecurityLog(
            event_type=event_type,
            severity=severity,
            actor=actor,
            target=target,
            description=description,
            ip_address="127.0.0.1",
            metadata_json=json.dumps(metadata or {}, ensure_ascii=False),
        )
        db.add(entry)
        db.commit()
    except Exception:
        db.rollback()


def create_adaptive_backup_snapshot(db: Session, label: str = "manual_snapshot") -> Dict[str, Any]:
    """
    Creates a complete recovery snapshot of TARS Adaptive Learning tables (Memories,
    Learning Records, Experiences, Documents, Proposals, Permissions) on disk.
    """
    snap_id = f"tars_backup_{datetime.utcnow().strftime('%Y%m%d_%H%M%S')}_{uuid.uuid4().hex[:6]}"
    filepath = os.path.join(BACKUPS_DIR, f"{snap_id}.json")

    memories = db.query(MemoryRecord).all()
    learnings = db.query(LearningRecord).all()
    experiences = db.query(ExperienceRecord).all()
    docs = db.query(KnowledgeDocument).all()
    proposals = db.query(ImprovementProposal).all()
    perms = ensure_default_permissions(db)

    payload = {
        "snapshot_id": snap_id,
        "label": label,
        "created_at": datetime.utcnow().isoformat(),
        "counts": {
            "memories": len(memories),
            "learning_records": len(learnings),
            "experiences": len(experiences),
            "documents": len(docs),
            "proposals": len(proposals),
            "permissions": len(perms),
        },
        "memories": [
            {
                "memory_uid": m.memory_uid,
                "memory_type": m.memory_type,
                "category": m.category,
                "subject": m.subject,
                "content": m.content,
                "is_verified_fact": m.is_verified_fact,
                "fact_or_inference": m.fact_or_inference,
                "source_type": m.source_type,
                "source_reference": m.source_reference,
                "confidence": m.confidence,
            }
            for m in memories
        ],
        "permissions": [serialize_permission(p) for p in perms],
    }

    with open(filepath, "w", encoding="utf-8") as f:
        json.dump(payload, f, ensure_ascii=False, indent=2)

    log_security_audit(
        db=db,
        event_type="BACKUP_CREATED",
        severity="INFO",
        actor="TARS_BACKUP_MANAGER",
        target=snap_id,
        description=f"Created adaptive learning backup snapshot '{snap_id}' at {filepath}.",
    )

    return {
        "success": True,
        "snapshot_id": snap_id,
        "label": label,
        "filepath": filepath,
        "counts": payload["counts"],
        "created_at": payload["created_at"],
    }


def serialize_permission(r: PermissionScopeRecord) -> Dict[str, Any]:
    return {
        "id": r.id,
        "scope_name": r.scope_name,
        "enabled": bool(r.enabled),
        "requires_human_approval": bool(r.requires_human_approval),
        "description": r.description,
        "updated_at": r.updated_at.isoformat() if r.updated_at else None,
    }
