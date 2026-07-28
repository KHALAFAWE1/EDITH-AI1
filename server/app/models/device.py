from sqlalchemy import Column, Integer, String, DateTime
from sqlalchemy.sql import func
from app.database import Base


class Device(Base):
    __tablename__ = "devices"

    id = Column(Integer, primary_key=True, index=True)

    hostname = Column(String(100), nullable=False)

    username = Column(String(100))

    operating_system = Column(String(100))

    ip_address = Column(String(100))

    cpu = Column(String(50))

    ram = Column(String(50))

    storage = Column(String(50))

    status = Column(String(20), default="Online")

    last_seen = Column(
        DateTime(timezone=True),
        server_default=func.now()
    )