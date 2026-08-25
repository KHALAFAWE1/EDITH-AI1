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

from app.database import Base, engine
from app.models.device import Device
from app.models.person import Person
from app.models.face_embedding import FaceEmbedding

# إنشاء الجداول في قاعدة البيانات
Base.metadata.create_all(bind=engine)

app = FastAPI(
    title="EDITH AI Secure Core",
    version="2.0",
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

# مسار مجلد الـ uploads لتقديم الصور الثابتة للفرونت إند
UPLOADS_PATH = os.path.abspath(
    os.path.join(os.path.dirname(__file__), "..", "uploads")
)
os.makedirs(UPLOADS_PATH, exist_ok=True)
app.mount("/uploads", StaticFiles(directory=UPLOADS_PATH), name="uploads")

app.include_router(device.router)
app.include_router(vision.router)
app.include_router(people.router)
app.include_router(recognition.router)
app.include_router(ai.router)


@app.get("/api/health")
def health_check():
    return {
        "status": "online",
        "system": "EDITH AI Core",
        "security": "Grid Shield Active",
        "message": "EDITH AI System is fully operational and encrypted."
    }


# تقديم واجهة المستخدم React (Dashboard) مباشرة من السيرفر كـ Single Page Application
DIST_DIR = os.path.abspath(os.path.join(SERVER_DIR, "..", "dashboard", "dist"))

if os.path.exists(DIST_DIR):
    assets_dir = os.path.join(DIST_DIR, "assets")
    if os.path.exists(assets_dir):
        app.mount("/assets", StaticFiles(directory=assets_dir), name="assets")

    @app.get("/{full_path:path}")
    async def serve_spa(full_path: str):
        if full_path.startswith("api/") or full_path in ["docs", "openapi.json"]:
            return None
        target_file = os.path.join(DIST_DIR, full_path)
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