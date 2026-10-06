import secrets
import datetime
from typing import Optional, List
from fastapi import APIRouter, Depends, HTTPException, Request, status
from pydantic import BaseModel
from sqlalchemy.orm import Session
from sqlalchemy import desc

from app.database import SessionLocal
from app.models.pairing_session import PairingSession
from app.models.security_log import SecurityLog

router = APIRouter(
    prefix="/glasses",
    tags=["Smart Glasses & Mobile Companion Gateway"]
)


def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


class PairApproveSchema(BaseModel):
    token: str
    device_name: Optional[str] = "iPhone Smart Glasses Companion"
    device_type: Optional[str] = "iPhone_Companion"
    battery_level: Optional[int] = None
    camera_active: Optional[bool] = True
    mic_active: Optional[bool] = True


@router.post("/generate-pairing-qr")
def generate_pairing_qr(request: Request, db: Session = Depends(get_db)):
    """
    توليد رمز اقتران مشفر ومؤقت (5 دقائق صلاحية) بدون أي أسرار أو كلمات مرور
    """
    token = secrets.token_urlsafe(24)
    now = datetime.datetime.now(datetime.timezone.utc)
    expires_at = now + datetime.timedelta(minutes=5)

    session = PairingSession(
        token=token,
        status="PENDING",
        expires_at=expires_at
    )
    db.add(session)
    db.commit()
    db.refresh(session)

    # الرابط الآمن الذي يفتحه الهاتف عند مسح الـ QR
    base_url = str(request.base_url).rstrip("/")
    pairing_url = f"{base_url}/glasses-hud?pair_token={token}"

    return {
        "pairing_token": token,
        "pairing_url": pairing_url,
        "expires_in_seconds": 300,
        "expires_at": expires_at.isoformat(),
        "instructions": "Scan this QR code with iPhone or Smart Glasses companion browser to authenticate."
    }


@router.post("/pair-client")
def pair_client(req: PairApproveSchema, request: Request, db: Session = Depends(get_db)):
    """
    اعتماد الاقتران من جانب الهاتف أو النظارة الذكية مع تسجيل قدرات الجهاز
    """
    now = datetime.datetime.now(datetime.timezone.utc)
    session = db.query(PairingSession).filter(PairingSession.token == req.token.strip()).first()

    if not session:
        raise HTTPException(status_code=404, detail="Invalid pairing token.")

    # مقارنة الوقت
    session_expiry = session.expires_at
    if session_expiry.tzinfo is None:
        session_expiry = session_expiry.replace(tzinfo=datetime.timezone.utc)

    if session_expiry < now:
        session.status = "EXPIRED"
        db.commit()
        raise HTTPException(status_code=400, detail="Pairing token has expired. Please generate a new QR code.")

    client_ip = request.client.host if request.client else "127.0.0.1"

    session.status = "PAIRED"
    session.device_name = req.device_name or "Mobile Smart Glasses Client"
    session.device_type = req.device_type or "iPhone_Companion"
    session.client_ip = client_ip
    session.battery_level = req.battery_level
    session.camera_active = req.camera_active or False
    session.mic_active = req.mic_active or False
    session.approved_at = now
    db.commit()

    # تسجيل في سجل الأمان
    audit = SecurityLog(
        event_type="GLASSES_PAIRED",
        severity="INFO",
        actor=session.device_name,
        target=client_ip,
        description=f"Smart Glasses Companion ({session.device_name}) successfully paired from IP {client_ip}."
    )
    db.add(audit)
    db.commit()

    return {
        "success": True,
        "status": "PAIRED",
        "device_name": session.device_name,
        "message": "Smart Glasses companion authenticated and connected to EDITH Core."
    }


@router.get("/status")
def get_glasses_connection_status(db: Session = Depends(get_db)):
    """
    التحقق الحقيقي من حالة النظارة الذكية المقترنة (بدون أي أجهزة وهمية)
    """
    now = datetime.datetime.now(datetime.timezone.utc)

    # جلب آخر جلسة مقترنة نشطة
    active_session = db.query(PairingSession).filter(
        PairingSession.status == "PAIRED"
    ).order_by(desc(PairingSession.approved_at)).first()

    if not active_session:
        return {
            "connected": False,
            "status": "No Device Paired",
            "device": None,
            "message": "No active Smart Glasses or iPhone companion paired."
        }

    return {
        "connected": True,
        "status": "Online (Active Companion)",
        "device": {
            "session_id": active_session.id,
            "name": active_session.device_name,
            "type": active_session.device_type,
            "client_ip": active_session.client_ip,
            "battery_level": active_session.battery_level,
            "camera_active": active_session.camera_active,
            "mic_active": active_session.mic_active,
            "paired_at": active_session.approved_at
        }
    }


@router.post("/disconnect")
def disconnect_glasses(db: Session = Depends(get_db)):
    """فصل النظارة الذكية وإنهاء الجلسة"""
    active_sessions = db.query(PairingSession).filter(PairingSession.status == "PAIRED").all()
    for s in active_sessions:
        s.status = "DISCONNECTED"
    db.commit()

    return {"success": True, "message": "Smart Glasses companion session terminated."}
