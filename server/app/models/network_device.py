from sqlalchemy import Column, Integer, String, Boolean, DateTime
from sqlalchemy.sql import func
from app.database import Base


class NetworkDevice(Base):
    __tablename__ = "network_devices"

    id = Column(Integer, primary_key=True, index=True)
    ip_address = Column(String(50), unique=True, index=True, nullable=False)
    mac_address = Column(String(50), nullable=True, index=True)
    hostname = Column(String(100), default="UNKNOWN")
    vendor = Column(String(100), default="Generic Network Adapter")
    device_type = Column(String(50), default="Unknown Node")  # Workstation, Server, Mobile, IoT, Rogue AP
    is_authorized = Column(Boolean, default=True)
    status = Column(String(20), default="Active")            # Active, Offline, Suspect
    risk_level = Column(String(20), default="LOW")           # LOW, MEDIUM, HIGH, CRITICAL
    first_seen = Column(DateTime(timezone=True), server_default=func.now())
    last_seen = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now())
