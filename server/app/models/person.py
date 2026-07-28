from sqlalchemy import Column, Integer, String, DateTime
from sqlalchemy.sql import func

from app.database import Base


class Person(Base):
    __tablename__ = "people"

    id = Column(Integer, primary_key=True, index=True)

    full_name = Column(String(150), nullable=False)

    person_type = Column(String(50))      # Student / Teacher

    department = Column(String(100))

    position = Column(String(100))

    subjects = Column(String(300))

    phone = Column(String(50))

    email = Column(String(150))

    office = Column(String(100))

    photo_path = Column(String(300))

    face_embedding = Column(String)

    notes = Column(String(500))

    created_at = Column(
        DateTime(timezone=True),
        server_default=func.now()
    )