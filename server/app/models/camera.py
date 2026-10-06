from sqlalchemy import Column, Integer, String, Boolean, DateTime
from sqlalchemy.sql import func
from app.database import Base


class Camera(Base):
    __tablename__ = "cameras"

    id = Column(Integer, primary_key=True, index=True)
    name = Column(String(100), nullable=False)
    camera_type = Column(String(50), default="USB_LOCAL")  # USB_LOCAL, RTSP_STREAM, HTTP_MJPEG, SMART_GLASSES
    source_url = Column(String(300), nullable=True)        # RTSP/HTTP URL if network camera
    resolution = Column(String(50), default="1280x720")
    fps = Column(Integer, default=30)
    status = Column(String(20), default="Online")          # Online, Disconnected, Offline
    is_active = Column(Boolean, default=True)
    last_seen = Column(DateTime(timezone=True), server_default=func.now())
    created_at = Column(DateTime(timezone=True), server_default=func.now())
