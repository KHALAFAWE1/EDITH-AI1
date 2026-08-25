import os
from sqlalchemy import create_engine
from sqlalchemy.orm import declarative_base, sessionmaker

RAW_DB_URL = os.getenv("DATABASE_URL", "postgresql://postgres:Edith-ai.x0@localhost:5432/edith_ai")
if RAW_DB_URL.startswith("postgres://"):
    DATABASE_URL = RAW_DB_URL.replace("postgres://", "postgresql://", 1)
else:
    DATABASE_URL = RAW_DB_URL

engine = create_engine(DATABASE_URL)


SessionLocal = sessionmaker(
    autocommit=False,
    autoflush=False,
    bind=engine
)

Base = declarative_base()


def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()