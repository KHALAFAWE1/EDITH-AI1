from sqlalchemy import Column, Integer, String, Text, DateTime
from sqlalchemy.sql import func
from app.database import Base


class SecurityLog(Base):
    __tablename__ = "security_logs"

    id = Column(Integer, primary_key=True, index=True)
    event_type = Column(String(50), nullable=False, index=True)  # AUTH_LOGIN, FACE_RECOGNITION, ACCESS_DENIED, ANOMALY_TRIGGER, RISK_ALERT
    severity = Column(String(20), default="INFO", index=True)   # INFO, LOW, MEDIUM, HIGH, CRITICAL
    actor = Column(String(100), nullable=True)                  # Username or Subject ID
    target = Column(String(100), nullable=True)                 # IP, Room, or Device
    description = Column(Text, nullable=False)
    ip_address = Column(String(50), nullable=True)
    metadata_json = Column(Text, nullable=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now(), index=True)
