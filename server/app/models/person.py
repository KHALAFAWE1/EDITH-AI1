from sqlalchemy import Column, Integer, String, DateTime
from sqlalchemy.sql import func
from sqlalchemy.orm import relationship

from app.database import Base


class Person(Base):
    __tablename__ = "people"

    id = Column(Integer, primary_key=True, index=True)

    full_name = Column(String(150), nullable=False)

    person_type = Column(String(50))

    department = Column(String(100))

    position = Column(String(100))

    subjects = Column(String(300))

    phone = Column(String(50))

    email = Column(String(150))

    office = Column(String(100))

    photo_path = Column(String(300))

    notes = Column(String(500))

    created_at = Column(
        DateTime(timezone=True),
        server_default=func.now()
    )

    embeddings = relationship(
        "FaceEmbedding",
        back_populates="person",
        cascade="all, delete"
    )