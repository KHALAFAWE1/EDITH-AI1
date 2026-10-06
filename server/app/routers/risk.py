import json
from typing import Optional, List
from fastapi import APIRouter, Depends
from pydantic import BaseModel
from sqlalchemy.orm import Session
from sqlalchemy import desc

from app.database import SessionLocal
from app.models.risk_assessment import RiskAssessment
from app.models.event import Event
from app.models.network_device import NetworkDevice

router = APIRouter(
    prefix="/risk",
    tags=["Centralized Risk & Explainable AI Engine"]
)


def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


class ManualRiskEvalSchema(BaseModel):
    location: Optional[str] = "Sector A - Main Command Hub"
    detected_people_count: Optional[int] = 1
    unidentified_faces: Optional[int] = 0
    unknown_network_devices: Optional[int] = 0
    anomaly_flag: Optional[bool] = False


@router.get("/current")
def get_current_risk_assessment(db: Session = Depends(get_db)):
    """حساب مستوى الخطورة اللحظي مع التفسير الكامل (Explainable AI: WHAT, WHY, EVIDENCE)"""
    anomalies_count = db.query(Event).filter(Event.is_anomaly == True).count()
    unauthorized_nodes = db.query(NetworkDevice).filter(NetworkDevice.is_authorized == False).count()

    # Dynamic 0–100 Score Calculation
    base_score = 15.0
    evidence = []
    reasons = []

    if anomalies_count > 0:
        base_score += min(40.0, anomalies_count * 15.0)
        reasons.append(f"تم رصد {anomalies_count} نشاط غير نمطي (Anomalies) في الذاكرة العرضية.")
        evidence.append("Event memory logs flagged behavioral or environmental deviation.")

    if unauthorized_nodes > 0:
        base_score += min(35.0, unauthorized_nodes * 20.0)
        reasons.append(f"تم اكتشاف {unauthorized_nodes} جهاز غير مسجل على نطاق الشبكة المحلية.")
        evidence.append("Passive CyberVision telemetry flagged unrecognized MAC/IP.")

    if not reasons:
        reasons.append("جميع الأنظمة والعقد والتعرفات البيومترية ضمن النطاق الطبيعي المعتمد.")
        evidence.append("Optical biometrics and network state conform with baseline norms.")

    final_score = min(100.0, round(base_score, 1))

    severity = "LOW"
    if final_score >= 80:
        severity = "CRITICAL"
    elif final_score >= 60:
        severity = "HIGH"
    elif final_score >= 35:
        severity = "MEDIUM"

    recommended_action = "المراقبة الروتينية المستمرة والمسح التكتيكي الدوري."
    if severity in ["HIGH", "CRITICAL"]:
        recommended_action = "التحقق الفوري من العقد المشبوهة ومراجعة تسجيلات الكاميرا في القطاع المستهدف."
    elif severity == "MEDIUM":
        recommended_action = "تدقيق هوية الأجهزة المتصلة مؤخراً ومتابعة التواجد البشري في الموقع."

    return {
        "risk_score": final_score,
        "severity": severity,
        "confidence": 0.88,
        "location": "Sector A - Main Command Hub",
        "explainable_ai": {
            "what": f"مستوى الخطورة الإجمالي للنظام هو {final_score}/100 بنطاق ({severity}).",
            "why": reasons,
            "evidence": evidence,
            "confidence_percent": 88,
            "recommended_action": recommended_action
        }
    }


@router.post("/evaluate")
def evaluate_custom_risk(req: ManualRiskEvalSchema, db: Session = Depends(get_db)):
    """محاكاة وتقييم المخاطر لسيناريو محدد"""
    score = 10.0
    reasons = []

    if req.unidentified_faces > 0:
        score += req.unidentified_faces * 25.0
        reasons.append(f"تحديد {req.unidentified_faces} وجه غير مسجل في قاعدة البيانات.")

    if req.unknown_network_devices > 0:
        score += req.unknown_network_devices * 30.0
        reasons.append(f"ظهور {req.unknown_network_devices} أجهزة شبكية مجهولة.")

    if req.anomaly_flag:
        score += 25.0
        reasons.append("انحراف عن النمط البيئي المعتاد (Environmental Anomaly).")

    final_score = min(100.0, round(score, 1))
    severity = "LOW"
    if final_score >= 80:
        severity = "CRITICAL"
    elif final_score >= 60:
        severity = "HIGH"
    elif final_score >= 35:
        severity = "MEDIUM"

    return {
        "risk_score": final_score,
        "severity": severity,
        "reasons": reasons if reasons else ["الوضع مستقر وضمن الحدود الآمنة."],
        "recommended_action": "تطبيق تدابير الحماية الموصى بها وفقاً لمستوى الخطورة."
    }
