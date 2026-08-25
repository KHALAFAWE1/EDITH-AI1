from sqlalchemy import Column, Integer, ForeignKey, Text
from sqlalchemy.orm import relationship
from app.database import Base


class FaceEmbedding(Base):
    __tablename__ = "face_embeddings"

    id = Column(Integer, primary_key=True, index=True)

    person_id = Column(
        Integer,
        ForeignKey("people.id", ondelete="CASCADE")
    )

    embedding = Column(Text, nullable=False)

    person = relationship(
        "Person",
        back_populates="embeddings"
    )