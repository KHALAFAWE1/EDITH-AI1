from fastapi import FastAPI
from app.routers import device
from app.routers import vision
from app.routers import people

from app.database import Base, engine
from app.models.device import Device
from app.models.person import Person

# إنشاء الجداول في قاعدة البيانات
Base.metadata.create_all(bind=engine)

app = FastAPI(
    title="EDITH AI",
    version="1.0"
)

app.include_router(device.router)
app.include_router(vision.router)
app.include_router(people.router)

@app.get("/")
def home():
    return {
        "message": "Welcome to EDITH AI"
    }