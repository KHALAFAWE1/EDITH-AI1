from sqlalchemy import Column, Integer, String, Text, Float, DateTime
from sqlalchemy.sql import func
from app.database import Base


class RiskAssessment(Base):
    __tablename__ = "risk_assessments"

    id = Column(Integer, primary_key=True, index=True)
    risk_score = Column(Float, nullable=False, index=True)  # 0 to 100
    severity = Column(String(20), nullable=False, index=True)  # LOW, MEDIUM, HIGH, CRITICAL
    location = Column(String(100), default="Sector A - Command Center")
    reasons_json = Column(Text, nullable=False)     # Array of strings
    evidence_json = Column(Text, nullable=True)     # Detailed telemetry/visual evidence
    recommended_action = Column(Text, nullable=False)
    confidence = Column(Float, default=0.85)
    created_at = Column(DateTime(timezone=True), server_default=func.now(), index=True)
