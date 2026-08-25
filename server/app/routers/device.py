import platform
import socket
import psutil
from datetime import datetime
from typing import List, Optional

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from app.database import SessionLocal
from app.models.device import Device

router = APIRouter(
    prefix="/devices",
    tags=["Devices"]
)


def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


def get_system_ip():
    try:
        s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        s.connect(("8.8.8.8", 80))
        ip = s.getsockname()[0]
        s.close()
        return ip
    except Exception:
        return "127.0.0.1"


@router.get("/telemetry")
def get_live_telemetry():
    """جلب إحصائيات حية ومباشرة لموارد الجهاز والمكونات المادية"""
    cpu_percent = psutil.cpu_percent(interval=0.2)
    cpu_count = psutil.cpu_count(logical=True)
    cpu_freq = psutil.cpu_freq()

    ram = psutil.virtual_memory()
    disk = psutil.disk_usage("/")

    boot_time = datetime.fromtimestamp(psutil.boot_time())
    uptime_seconds = (datetime.now() - boot_time).total_seconds()
    hours = int(uptime_seconds // 3600)
    minutes = int((uptime_seconds % 3600) // 60)

    return {
        "hostname": platform.node(),
        "os": f"{platform.system()} {platform.release()}",
        "os_version": platform.version(),
        "machine": platform.machine(),
        "processor": platform.processor(),
        "ip_address": get_system_ip(),
        "cpu": {
            "percent": cpu_percent,
            "cores": cpu_count,
            "frequency_mhz": round(cpu_freq.current, 1) if cpu_freq else 0
        },
        "ram": {
            "total_gb": round(ram.total / (1024 ** 3), 2),
            "used_gb": round(ram.used / (1024 ** 3), 2),
            "free_gb": round(ram.available / (1024 ** 3), 2),
            "percent": ram.percent
        },
        "storage": {
            "total_gb": round(disk.total / (1024 ** 3), 2),
            "used_gb": round(disk.used / (1024 ** 3), 2),
            "free_gb": round(disk.free / (1024 ** 3), 2),
            "percent": disk.percent
        },
        "uptime": f"{hours}h {minutes}m",
        "status": "Online",
        "timestamp": datetime.now().isoformat()
    }


@router.get("/")
def get_devices(db: Session = Depends(get_db)):
    """جلب قائمة الأجهزة المسجلة في النظام"""
    devices = db.query(Device).all()
    return devices


@router.post("/register-host")
def register_or_update_host(db: Session = Depends(get_db)):
    """تسجيل أو تحديث حالة جهاز السيرفر الحالي في قاعدة البيانات"""
    hostname = platform.node()
    ip_address = get_system_ip()
    os_name = f"{platform.system()} {platform.release()}"
    
    cpu_percent = psutil.cpu_percent(interval=0.1)
    ram = psutil.virtual_memory()
    disk = psutil.disk_usage("/")

    cpu_info = f"{psutil.cpu_count(logical=True)} Cores ({cpu_percent}%)"
    ram_info = f"{round(ram.used / (1024**3), 1)}/{round(ram.total / (1024**3), 1)} GB ({ram.percent}%)"
    storage_info = f"{round(disk.used / (1024**3), 1)}/{round(disk.total / (1024**3), 1)} GB ({disk.percent}%)"

    device = db.query(Device).filter(Device.hostname == hostname).first()
    if not device:
        device = Device(
            hostname=hostname,
            username=platform.uname().node,
            operating_system=os_name,
            ip_address=ip_address,
            cpu=cpu_info,
            ram=ram_info,
            storage=storage_info,
            status="Online"
        )
        db.add(device)
    else:
        device.ip_address = ip_address
        device.cpu = cpu_info
        device.ram = ram_info
        device.storage = storage_info
        device.status = "Online"
        device.last_seen = datetime.now()

    db.commit()
    db.refresh(device)
    return device


@router.delete("/{device_id}")
def delete_device(device_id: int, db: Session = Depends(get_db)):
    """حذف جهاز من قاعدة البيانات"""
    device = db.query(Device).filter(Device.id == device_id).first()
    if not device:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Device not found"
        )
    db.delete(device)
    db.commit()
    return {"success": True, "message": f"Device {device.hostname} deleted successfully"}