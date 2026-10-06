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


def run_auto_migrations():
    """Dynamically ensures all expected columns exist across SQLite and PostgreSQL databases."""
    from sqlalchemy import inspect, text
    inspector = inspect(engine)
    existing_tables = inspector.get_table_names()

    # Migrate devices table
    if "devices" in existing_tables:
        existing_cols = {col["name"] for col in inspector.get_columns("devices")}
        device_cols = [
            ("device_id", "VARCHAR(64)"),
            ("device_name", "VARCHAR(100)"),
            ("device_type", "VARCHAR(30) DEFAULT 'OTHER'"),
            ("platform", "VARCHAR(50) DEFAULT 'Universal'"),
            ("operating_system", "VARCHAR(100)"),
            ("browser", "VARCHAR(100)"),
            ("client_version", "VARCHAR(30) DEFAULT '2.5.0'"),
            ("hostname", "VARCHAR(100)"),
            ("username", "VARCHAR(100)"),
            ("ip_address", "VARCHAR(100)"),
            ("status", "VARCHAR(20) DEFAULT 'Online'"),
            ("connection_status", "VARCHAR(20) DEFAULT 'OFFLINE'"),
            ("enrollment_status", "VARCHAR(20) DEFAULT 'ENROLLED'"),
            ("auth_token", "VARCHAR(128)"),
            ("is_primary_host", "BOOLEAN DEFAULT 0"),
            ("capabilities", "TEXT"),
            ("cpu", "VARCHAR(50)"),
            ("ram", "VARCHAR(50)"),
            ("storage", "VARCHAR(50)"),
            ("battery_level", "INTEGER"),
            ("battery_charging", "BOOLEAN"),
            ("last_seen", "DATETIME"),
            ("enrolled_at", "DATETIME"),
        ]
        with engine.begin() as conn:
            for col_name, col_type in device_cols:
                if col_name not in existing_cols:
                    try:
                        conn.execute(text(f"ALTER TABLE devices ADD COLUMN {col_name} {col_type}"))
                    except Exception as e:
                        pass

    # Migrate pairing_sessions table
    if "pairing_sessions" in existing_tables:
        existing_cols = {col["name"] for col in inspector.get_columns("pairing_sessions")}
        pairing_cols = [
            ("token", "VARCHAR(100)"),
            ("device_type", "VARCHAR(50) DEFAULT 'BROWSER'"),
            ("device_name", "VARCHAR(100)"),
            ("status", "VARCHAR(20) DEFAULT 'PENDING'"),
            ("client_ip", "VARCHAR(50)"),
            ("claimed_device_id", "VARCHAR(64)"),
            ("auth_token", "VARCHAR(128)"),
            ("battery_level", "INTEGER"),
            ("camera_active", "BOOLEAN DEFAULT 0"),
            ("mic_active", "BOOLEAN DEFAULT 0"),
            ("created_at", "DATETIME"),
            ("expires_at", "DATETIME"),
            ("approved_at", "DATETIME"),
        ]
        with engine.begin() as conn:
            for col_name, col_type in pairing_cols:
                if col_name not in existing_cols:
                    try:
                        conn.execute(text(f"ALTER TABLE pairing_sessions ADD COLUMN {col_name} {col_type}"))
                    except Exception as e:
                        pass

