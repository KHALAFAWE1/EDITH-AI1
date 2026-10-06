import cv2
import datetime
from typing import Optional, List
from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel
from sqlalchemy.orm import Session

from app.database import SessionLocal
from app.models.camera import Camera
from app.models.security_log import SecurityLog

router = APIRouter(
    prefix="/cameras",
    tags=["Camera Management System"]
)


def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


def probe_local_opencv_cameras() -> List[dict]:
    """فحص واكتشاف الكاميرات الحقيقية المتصلة بجهاز السيرفر عبر OpenCV بدون تزييف"""
    detected = []
    # فحص المنافذ 0, 1
    for index in range(2):
        cap = cv2.VideoCapture(index, cv2.CAP_DSHOW if hasattr(cv2, "CAP_DSHOW") else cv2.CAP_ANY)
        if cap.isOpened():
            is_reading, frame = cap.read()
            width = int(cap.get(cv2.CAP_PROP_FRAME_WIDTH)) or 640
            height = int(cap.get(cv2.CAP_PROP_FRAME_HEIGHT)) or 480
            fps = int(cap.get(cv2.CAP_PROP_FPS)) or 30
            cap.release()
            
            detected.append({
                "id": f"local_{index}",
                "name": f"Integrated / USB Optical Sensor (Device #{index})",
                "type": "USB_LOCAL",
                "source": f"device://{index}",
                "resolution": f"{width}x{height}",
                "fps": fps if fps > 0 else 30,
                "status": "Online" if is_reading else "Connected (Idle)",
                "is_local": True
            })
        else:
            cap.release()
    return detected


class AddNetworkCameraSchema(BaseModel):
    name: str
    camera_type: str = "RTSP_STREAM"  # RTSP_STREAM, HTTP_MJPEG, WI_FI_CAM
    source_url: str
    resolution: Optional[str] = "1920x1080"
    fps: Optional[int] = 30


class TestCameraSchema(BaseModel):
    source_url: str


@router.get("")
@router.get("/")
def list_available_cameras(db: Session = Depends(get_db)):
    """جلب قائمة الكاميرات الحقيقية المتصلة (محلية وشبكية)"""
    local_cams = probe_local_opencv_cameras()
    
    # الكاميرات الشبكية المسجلة في قاعدة البيانات
    enrolled_cams = db.query(Camera).filter(Camera.is_active == True).all()
    enrolled_list = [
        {
            "id": f"net_{c.id}",
            "db_id": c.id,
            "name": c.name,
            "type": c.camera_type,
            "source": c.source_url,
            "resolution": c.resolution,
            "fps": c.fps,
            "status": c.status,
            "is_local": False,
            "last_seen": c.last_seen
        }
        for c in enrolled_cams
    ]

    combined = local_cams + enrolled_list

    return {
        "total_detected": len(combined),
        "local_sensors_count": len(local_cams),
        "network_cameras_count": len(enrolled_list),
        "cameras": combined,
        "message": "No cameras detected on host." if not combined else None
    }


@router.post("/test-connection")
def test_camera_connection(req: TestCameraSchema):
    """التحقق الحقيقي من إمكانية الاتصال بكاميرا الشبكة قبل حفظها"""
    url = req.source_url.strip()
    if not url:
        raise HTTPException(status_code=400, detail="Camera source URL is required.")

    cap = cv2.VideoCapture(url)
    if not cap.isOpened():
        return {
            "success": False,
            "message": "Connection Failed: Unable to establish RTSP/HTTP video handshake."
        }

    success, frame = cap.read()
    width = int(cap.get(cv2.CAP_PROP_FRAME_WIDTH)) or 0
    height = int(cap.get(cv2.CAP_PROP_FRAME_HEIGHT)) or 0
    cap.release()

    if not success:
        return {
            "success": False,
            "message": "Stream Handshake Connected, but frame decode failed or authentication rejected."
        }

    return {
        "success": True,
        "message": f"Connection Verified: Stream resolution {width}x{height}.",
        "resolution": f"{width}x{height}"
    }


@router.post("/add")
def add_network_camera(req: AddNetworkCameraSchema, db: Session = Depends(get_db)):
    """تسجيل كاميرا شبكية حقيقية في النظام"""
    new_cam = Camera(
        name=req.name.strip(),
        camera_type=req.camera_type,
        source_url=req.source_url.strip(),
        resolution=req.resolution or "1920x1080",
        fps=req.fps or 30,
        status="Online"
    )
    db.add(new_cam)
    db.commit()
    db.refresh(new_cam)

    audit = SecurityLog(
        event_type="CAMERA_ADDED",
        severity="INFO",
        actor="ADMIN",
        target=new_cam.name,
        description=f"Network Camera {new_cam.name} ({new_cam.camera_type}) enrolled."
    )
    db.add(audit)
    db.commit()

    return {"success": True, "camera_id": new_cam.id, "message": "Camera added successfully."}


@router.delete("/{camera_id}")
def delete_network_camera(camera_id: int, db: Session = Depends(get_db)):
    """حذف كاميرا شبكية"""
    cam = db.query(Camera).filter(Camera.id == camera_id).first()
    if not cam:
        raise HTTPException(status_code=404, detail="Camera not found.")
    
    name = cam.name
    db.delete(cam)
    db.commit()

    return {"success": True, "message": f"Camera {name} removed."}
