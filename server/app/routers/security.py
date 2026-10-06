from typing import Optional, List
from fastapi import APIRouter, Depends, HTTPException, Query
from pydantic import BaseModel
from sqlalchemy.orm import Session
from sqlalchemy import desc

from app.database import SessionLocal
from app.models.security_log import SecurityLog
from app.models.user import User
from app.routers.auth import get_current_user

router = APIRouter(
    prefix="/security",
    tags=["Security Operations Center (SOC)"]
)


def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


class LogEventSchema(BaseModel):
    event_type: str
    severity: Optional[str] = "INFO"
    actor: Optional[str] = None
    target: Optional[str] = None
    description: str
    ip_address: Optional[str] = None
    metadata_json: Optional[str] = None


@router.get("/audit-logs")
def get_audit_logs(
    severity: Optional[str] = None,
    limit: int = Query(50, ge=1, le=200),
    db: Session = Depends(get_db)
):
    """جلب سجلات التدقيق الأمني مع إمكانية الفلترة حسب مستوى الخطورة"""
    query = db.query(SecurityLog)
    if severity and severity.upper() != "ALL":
        query = query.filter(SecurityLog.severity == severity.upper())

    logs = query.order_by(desc(SecurityLog.created_at)).limit(limit).all()

    return [
        {
            "id": log.id,
            "event_type": log.event_type,
            "severity": log.severity,
            "actor": log.actor,
            "target": log.target,
            "description": log.description,
            "ip_address": log.ip_address,
            "created_at": log.created_at
        }
        for log in logs
    ]


@router.get("/summary")
def get_security_summary(db: Session = Depends(get_db)):
    """إحصائيات مركز العمليات الأمنية (SOC Overview)"""
    total_logs = db.query(SecurityLog).count()
    critical_events = db.query(SecurityLog).filter(SecurityLog.severity.in_(["HIGH", "CRITICAL"])).count()
    recent_events = db.query(SecurityLog).order_by(desc(SecurityLog.created_at)).limit(5).all()

    return {
        "status": "SHIELD_ACTIVE",
        "threat_level": "ELEVATED" if critical_events > 0 else "NORMAL",
        "total_audit_events": total_logs,
        "critical_alerts_count": critical_events,
        "security_score": max(20, 100 - (critical_events * 15)),
        "recent_alerts": [
            {
                "id": log.id,
                "event_type": log.event_type,
                "severity": log.severity,
                "description": log.description,
                "timestamp": log.created_at
            }
            for log in recent_events
        ]
    }


@router.post("/log-event")
def create_security_log(req: LogEventSchema, db: Session = Depends(get_db)):
    """تسجيل حدث أمني جديد برمجياً"""
    log_entry = SecurityLog(
        event_type=req.event_type.upper(),
        severity=req.severity.upper() if req.severity else "INFO",
        actor=req.actor,
        target=req.target,
        description=req.description,
        ip_address=req.ip_address,
        metadata_json=req.metadata_json
    )
    db.add(log_entry)
    db.commit()
    db.refresh(log_entry)

    return {
        "success": True,
        "log_id": log_entry.id,
        "message": "Security event recorded."
    }
