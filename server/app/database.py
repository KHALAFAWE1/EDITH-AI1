import os
from sqlalchemy import create_engine
from sqlalchemy.orm import declarative_base, sessionmaker

RAW_DB_URL = os.getenv("DATABASE_URL", "").strip()
if RAW_DB_URL:
    if RAW_DB_URL.startswith("postgres://"):
        DATABASE_URL = RAW_DB_URL.replace("postgres://", "postgresql://", 1)
    else:
        DATABASE_URL = RAW_DB_URL
else:
    # استرجاع تلقائي لـ SQLite في السحابة ليعمل فوراً بدون إعدادات معقدة
    DATABASE_URL = "sqlite:///./edith_ai.db"

connect_args = {"check_same_thread": False} if DATABASE_URL.startswith("sqlite") else {}
engine = create_engine(DATABASE_URL, connect_args=connect_args)



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
