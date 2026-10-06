import sys
import os

# إضافة مجلد server إلى مسارات بايثون تلقائياً لتفادي ModuleNotFoundError
SERVER_DIR = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
if SERVER_DIR not in sys.path:
    sys.path.insert(0, SERVER_DIR)

from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.middleware.trustedhost import TrustedHostMiddleware
from fastapi.staticfiles import StaticFiles
from starlette.middleware.base import BaseHTTPMiddleware

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

from app.database import Base, engine
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

# إنشاء كافة الجداول في قاعدة البيانات تلقائياً
Base.metadata.create_all(bind=engine)

app = FastAPI(
    title="EDITH AI Situational Awareness Core",
    version="2.5",
    docs_url="/docs",
    redoc_url=None
)

# ميدلوير الحماية والأمان ضد الهجمات والاختراق (Security Headers)
class SecurityHeadersMiddleware(BaseHTTPMiddleware):
    async def dispatch(self, request: Request, call_next):
        response = await call_next(request)
        response.headers["X-Content-Type-Options"] = "nosniff"
        response.headers["X-Frame-Options"] = "SAMEORIGIN"
        response.headers["X-XSS-Protection"] = "1; mode=block"
        response.headers["Referrer-Policy"] = "strict-origin-when-cross-origin"
        response.headers["Permissions-Policy"] = "camera=*, microphone=*, geolocation=()"
        response.headers["Server"] = "EDITH-Defense-Grid"
        return response

app.add_middleware(SecurityHeadersMiddleware)

# إعدادات CORS للسماح لجميع الواجهات بالاتصال المشفر
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

from fastapi.responses import FileResponse
from fastapi import HTTPException

# مسار مجلد الـ uploads لتقديم الصور الثابتة للفرونت إند
UPLOADS_PATH = os.path.abspath(
    os.path.join(os.path.dirname(__file__), "..", "uploads")
)
os.makedirs(UPLOADS_PATH, exist_ok=True)
app.mount("/uploads", StaticFiles(directory=UPLOADS_PATH), name="uploads")

# تسجيل الموجهات التكتيكية
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
def health_check():
    return {
        "status": "online",
        "system": "EDITH AI Situational Awareness Core",
        "security": "Grid Shield Active",
        "message": "EDITH AI Defense Platform is fully operational and encrypted."
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
        # منع اعتراض مسارات الـ API أو التوثيق
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
            "system": "EDITH AI Core",
            "message": "EDITH AI Backend System is operational."
        }