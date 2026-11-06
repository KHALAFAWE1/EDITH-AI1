import sys
import os

# إضافة مجلد server إلى مسارات بايثون تلقائياً لتفادي ModuleNotFoundError
SERVER_DIR = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
if SERVER_DIR not in sys.path:
    sys.path.insert(0, SERVER_DIR)

from fastapi import FastAPI, Request, Depends, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse
from starlette.middleware.base import BaseHTTPMiddleware
from sqlalchemy.orm import Session
from sqlalchemy import text

from app.routers import device
from app.routers import vision
from app.routers import people
from app.routers import recognition
from app.routers import ai
from app.routers import auth
from app.routers import security
from app.routers import events
from app.routers import cyber
from app.routers import risk
from app.routers import cameras
from app.routers import glasses

from app.database import Base, engine, get_db, run_auto_migrations
from app.config import get_gemini_api_key
from app.models.device import Device
from app.models.person import Person
from app.models.face_embedding import FaceEmbedding
from app.models.user import User
from app.models.security_log import SecurityLog
from app.models.event import Event
from app.models.risk_assessment import RiskAssessment
from app.models.network_device import NetworkDevice
from app.models.camera import Camera
from app.models.pairing_session import PairingSession

# إنشاء كافة الجداول وتطبيق التحديثات الهيكلية تلقائياً
Base.metadata.create_all(bind=engine)
run_auto_migrations()

app = FastAPI(
    title="TARS AI — Autonomous Spacecraft & Tactical Intelligence Core",
    version="3.0",
    docs_url="/docs",
    redoc_url=None
)


class SecurityHeadersMiddleware(BaseHTTPMiddleware):
    async def dispatch(self, request: Request, call_next):
        response = await call_next(request)
        response.headers["X-Content-Type-Options"] = "nosniff"
        response.headers["X-Frame-Options"] = "SAMEORIGIN"
        response.headers["X-XSS-Protection"] = "1; mode=block"
        response.headers["Referrer-Policy"] = "strict-origin-when-cross-origin"
        response.headers["Permissions-Policy"] = "camera=*, microphone=*, geolocation=()"
        response.headers["Server"] = "TARS-Monolith-Core"
        return response


app.add_middleware(SecurityHeadersMiddleware)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

UPLOADS_PATH = os.path.abspath(
    os.path.join(os.path.dirname(__file__), "..", "uploads")
)
os.makedirs(UPLOADS_PATH, exist_ok=True)
app.mount("/uploads", StaticFiles(directory=UPLOADS_PATH), name="uploads")

app.include_router(auth.router)
app.include_router(security.router)
app.include_router(events.router)
app.include_router(cyber.router)
app.include_router(risk.router)
app.include_router(device.router)
app.include_router(vision.router)
app.include_router(people.router)
app.include_router(recognition.router)
app.include_router(ai.router)
app.include_router(cameras.router)
app.include_router(glasses.router)


@app.get("/api/health")
def health_check(db: Session = Depends(get_db)):
    db_ok = False
    people_count = 0
    devices_count = 0
    try:
        db.execute(text("SELECT 1"))
        db_ok = True
        people_count = db.query(Person).count()
        devices_count = db.query(Device).filter(Device.enrollment_status == "ENROLLED").count()
    except Exception:
        db_ok = False

    has_gemini = bool(get_gemini_api_key() and len(get_gemini_api_key()) > 10)

    return {
        "status": "online",
        "system": "TARS AI Autonomous Intelligence Core",
        "assistant": "TARS",
        "version": "3.0.0",
        "security": "Grid Shield Active",
        "database_connected": db_ok,
        "recognition_service": "ONLINE (InsightFace buffalo_l 512D)",
        "ai_service": "ONLINE (Gemini Connected)" if has_gemini else "LOCAL_MODE (API Key Optional)",
        "has_gemini_key": has_gemini,
        "registered_people_count": people_count,
        "enrolled_devices_count": devices_count,
        "message": "TARS AI Onboard System is operational."
    }


SERVER_DIR = os.path.dirname(os.path.abspath(__file__))
DIST_DIR = os.path.abspath(os.path.join(SERVER_DIR, "..", "..", "dashboard", "dist"))
API_PREFIX_TUPLE = (
    "api", "auth", "security", "events", "cyber", "risk",
    "people", "devices", "vision", "recognition", "ai",
    "cameras", "glasses", "uploads", "docs", "openapi.json", "redoc"
)


if os.path.exists(DIST_DIR):
    assets_dir = os.path.join(DIST_DIR, "assets")
    if os.path.exists(assets_dir):
        app.mount("/assets", StaticFiles(directory=assets_dir), name="assets")

    @app.get("/{full_path:path}")
    async def serve_spa(full_path: str):
        clean_path = full_path.lstrip("/")
        if any(clean_path == p or clean_path.startswith(f"{p}/") for p in API_PREFIX_TUPLE):
            raise HTTPException(status_code=404, detail="API route not found")

        target_file = os.path.join(DIST_DIR, clean_path)
        if os.path.exists(target_file) and os.path.isfile(target_file):
            return FileResponse(target_file)
        return FileResponse(os.path.join(DIST_DIR, "index.html"))

else:
    @app.get("/")
    def home():
        return {
            "status": "online",
            "system": "TARS AI Core",
            "message": "TARS AI Backend System is operational."
        }
