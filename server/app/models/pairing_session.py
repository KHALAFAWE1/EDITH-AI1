from sqlalchemy import Column, Integer, String, Boolean, DateTime
from sqlalchemy.sql import func
from app.database import Base


class PairingSession(Base):
    __tablename__ = "pairing_sessions"

    id = Column(Integer, primary_key=True, index=True)
    token = Column(String(100), unique=True, index=True, nullable=False)
    device_type = Column(String(50), default="BROWSER")            # PHONE, TABLET, LAPTOP, DESKTOP, SMART_GLASSES, BROWSER, PWA, OTHER
    device_name = Column(String(100), nullable=True)
    status = Column(String(20), default="PENDING")                 # PENDING, CLAIMED, PAIRED, EXPIRED, REVOKED
    client_ip = Column(String(50), nullable=True)
    claimed_device_id = Column(String(64), nullable=True)
    auth_token = Column(String(128), nullable=True)
    battery_level = Column(Integer, nullable=True)                 # 0-100% reported by companion
    camera_active = Column(Boolean, default=False)
    mic_active = Column(Boolean, default=False)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    expires_at = Column(DateTime(timezone=True), nullable=False)
    approved_at = Column(DateTime(timezone=True), nullable=True)

