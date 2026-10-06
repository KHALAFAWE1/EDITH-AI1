from sqlalchemy import Column, Integer, String, Text, Float, Boolean, DateTime
from sqlalchemy.sql import func
from app.database import Base


class Event(Base):
    __tablename__ = "events"

    id = Column(Integer, primary_key=True, index=True)
    event_type = Column(String(50), nullable=False, index=True)  # PERSON_DETECTED, PERSON_IDENTIFIED, OBJECT_DETECTED, NEW_DEVICE, ANOMALY, RISK_SPIKE
    source = Column(String(50), default="OPTICAL_SENSOR")        # OPTICAL_SENSOR, NETWORK_SCANNER, VOICE_TRIGGER, SYSTEM
    location_name = Column(String(100), default="Main Command Center", index=True)
    confidence = Column(Float, default=1.0)
    severity = Column(String(20), default="INFO", index=True)    # INFO, LOW, MEDIUM, HIGH, CRITICAL
    is_anomaly = Column(Boolean, default=False, index=True)
    summary = Column(String(255), nullable=False)
    details = Column(Text, nullable=True)
    metadata_json = Column(Text, nullable=True)
    timestamp = Column(DateTime(timezone=True), server_default=func.now(), index=True)
