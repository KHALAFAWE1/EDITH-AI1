import platform
import socket
import psutil
from datetime import datetime
from typing import List, Optional

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.orm import Session

from app.database import SessionLocal
from app.models.device import Device

router = APIRouter(
    prefix="/devices",
    tags=["Devices & Host Health"]
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
    """جلب إحصائيات حية ومباشرة لموارد الجهاز والمكونات المادية بدون أي قيم وهمية"""
    cpu_percent = psutil.cpu_percent(interval=0.2)
    cpu_count = psutil.cpu_count(logical=True)
    cpu_freq = psutil.cpu_freq()

    ram = psutil.virtual_memory()
    disk = psutil.disk_usage("/")

    # بطارية الجهاز إن وجدت
    battery_info = None
    try:
        battery = psutil.sensors_battery()
        if battery:
            battery_info = {
                "percent": battery.percent,
                "power_plugged": battery.power_plugged,
                "secsleft": battery.secsleft
            }
    except Exception:
        pass

    # شبكة I/O الحقيقية
    net_io = psutil.net_io_counters()

    boot_time = datetime.fromtimestamp(psutil.boot_time())
    uptime_seconds = (datetime.now() - boot_time).total_seconds()
    hours = int(uptime_seconds // 3600)
    minutes = int((uptime_seconds % 3600) // 60)

    return {
        "hostname": platform.node(),
        "os": f"{platform.system()} {platform.release()}",
        "os_version": platform.version(),
        "machine": platform.machine(),
        "processor": platform.processor() or "Generic x86_64 / ARM",
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
        "network_io": {
            "bytes_sent_mb": round(net_io.bytes_sent / (1024 ** 2), 2),
            "bytes_recv_mb": round(net_io.bytes_recv / (1024 ** 2), 2)
        },
        "battery": battery_info,
        "uptime": f"{hours}h {minutes}m",
        "status": "Online",
        "timestamp": datetime.now().isoformat()
    }


@router.get("/processes")
def get_running_processes(
    limit: int = Query(25, ge=5, le=100),
    sort_by: str = Query("cpu", enum=["cpu", "memory", "name", "pid"])
):
    """
    جلب قائمة العمليات الحقيقية الشغالة في النظام (Task Manager Process View)
    مع التحقق من الصلاحيات والتعامل مع العمليات المحمية
    """
    processes = []
    for proc in psutil.process_iter(['pid', 'name', 'cpu_percent', 'memory_percent', 'username', 'status', 'create_time']):
        try:
            info = proc.info
            # تنظيف وتنسيق القيم
            mem_mb = round((proc.memory_info().rss / (1024 * 1024)), 1) if hasattr(proc, "memory_info") else 0
            processes.append({
                "pid": info['pid'],
                "name": info['name'] or "System Process",
                "cpu_percent": info['cpu_percent'] or 0.0,
                "memory_percent": round(info['memory_percent'] or 0.0, 1),
                "memory_mb": mem_mb,
                "username": info['username'] or "SYSTEM",
                "status": info['status'] or "running"
            })
        except (psutil.NoSuchProcess, psutil.AccessDenied, psutil.ZombieProcess):
            continue

    if sort_by == "cpu":
        processes.sort(key=lambda x: x["cpu_percent"], reverse=True)
    elif sort_by == "memory":
        processes.sort(key=lambda x: x["memory_percent"], reverse=True)
    elif sort_by == "name":
        processes.sort(key=lambda x: x["name"].lower())
    elif sort_by == "pid":
        processes.sort(key=lambda x: x["pid"])

    return {
        "total_active_processes": len(processes),
        "processes": processes[:limit]
    }


@router.get("")
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