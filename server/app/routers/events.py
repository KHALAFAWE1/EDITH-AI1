import json
from typing import Optional, List
from fastapi import APIRouter, Depends, Query
from pydantic import BaseModel
from sqlalchemy.orm import Session
from sqlalchemy import desc

from app.database import SessionLocal
from app.models.event import Event

router = APIRouter(
    prefix="/events",
    tags=["Episodic Memory & Timeline"]
)


def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


class CreateEventSchema(BaseModel):
    event_type: str
    source: Optional[str] = "OPTICAL_SENSOR"
    location_name: Optional[str] = "Sector A - Main Hub"
    confidence: Optional[float] = 1.0
    severity: Optional[str] = "INFO"
    is_anomaly: Optional[bool] = False
    summary: str
    details: Optional[str] = None
    metadata: Optional[dict] = None


@router.get("")
@router.get("/")
def get_timeline_events(
    limit: int = Query(50, ge=1, le=200),
    severity: Optional[str] = None,
    anomalies_only: bool = False,
    db: Session = Depends(get_db)
):
    """جلب سجل الأحداث الزمني الحقيقي (Situational Event Timeline)"""
    query = db.query(Event)

    if anomalies_only:
        query = query.filter(Event.is_anomaly == True)
    if severity and severity.upper() != "ALL":
        query = query.filter(Event.severity == severity.upper())

    events = query.order_by(desc(Event.timestamp)).limit(limit).all()

    return [
        {
            "id": ev.id,
            "event_type": ev.event_type,
            "source": ev.source,
            "location": ev.location_name,
            "confidence": ev.confidence,
            "severity": ev.severity,
            "is_anomaly": ev.is_anomaly,
            "summary": ev.summary,
            "details": ev.details,
            "timestamp": ev.timestamp
        }
        for ev in events
    ]


@router.post("")
@router.post("/")
def log_event(req: CreateEventSchema, db: Session = Depends(get_db)):
    """تسجيل حدث جديد في الذاكرة العرضية للنظام"""
    new_event = Event(
        event_type=req.event_type.upper(),
        source=req.source.upper() if req.source else "OPTICAL_SENSOR",
        location_name=req.location_name or "Sector A - Main Hub",
        confidence=req.confidence or 1.0,
        severity=req.severity.upper() if req.severity else "INFO",
        is_anomaly=req.is_anomaly or False,
        summary=req.summary,
        details=req.details,
        metadata_json=json.dumps(req.metadata) if req.metadata else None
    )

    db.add(new_event)
    db.commit()
    db.refresh(new_event)

    return {
        "success": True,
        "event_id": new_event.id,
        "message": "Event recorded into EDITH episodic memory."
    }


@router.get("/stats")
def get_event_stats(db: Session = Depends(get_db)):
    """إحصائيات الأحداث والأنومالي المسجلة"""
    total = db.query(Event).count()
    anomalies = db.query(Event).filter(Event.is_anomaly == True).count()
    critical = db.query(Event).filter(Event.severity.in_(["HIGH", "CRITICAL"])).count()

    return {
        "total_events": total,
        "anomalies_detected": anomalies,
        "critical_incidents": critical,
        "baseline_conformity_percent": round(max(0, 100 - (anomalies * 5)), 1)
    }
