from sqlalchemy import Column, Integer, String, Boolean, DateTime, Text
from sqlalchemy.sql import func
import uuid
from app.database import Base


class Device(Base):
    __tablename__ = "devices"

    id = Column(Integer, primary_key=True, index=True)
    device_id = Column(String(64), unique=True, index=True, default=lambda: f"dev_{uuid.uuid4().hex[:12]}")
    device_name = Column(String(100), nullable=True)
    device_type = Column(String(30), default="OTHER")  # PHONE, TABLET, LAPTOP, DESKTOP, SMART_GLASSES, BROWSER, PWA, OTHER
    platform = Column(String(50), nullable=True)        # iOS, Android, Windows, macOS, Linux
    operating_system = Column(String(100), nullable=True)
    browser = Column(String(100), nullable=True)
    client_version = Column(String(30), default="2.5.0")
    
    # Network & Identity
    hostname = Column(String(100), nullable=True)
    username = Column(String(100), nullable=True)
    ip_address = Column(String(100), nullable=True)
    
    # Status & Auth
    status = Column(String(20), default="Online")       # Online, Offline, Connecting, Unknown
    connection_status = Column(String(20), default="OFFLINE") # ONLINE, CONNECTING, OFFLINE, UNKNOWN
    enrollment_status = Column(String(20), default="ENROLLED") # ENROLLED, PENDING, REVOKED
    auth_token = Column(String(128), unique=True, index=True, nullable=True)
    is_primary_host = Column(Boolean, default=False)
    
    # Real Capabilities (JSON serialized dictionary of detected hardware capabilities)
    capabilities = Column(Text, nullable=True)
    
    # Telemetry
    cpu = Column(String(50), nullable=True)
    ram = Column(String(50), nullable=True)
    storage = Column(String(50), nullable=True)
    battery_level = Column(Integer, nullable=True)      # Real battery percentage 0-100%
    battery_charging = Column(Boolean, nullable=True)
    
    # Timestamps
    last_seen = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now())
    enrolled_at = Column(DateTime(timezone=True), server_default=func.now())