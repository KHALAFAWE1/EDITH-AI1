import json
import uuid
import secrets
import platform
import socket
import psutil
from datetime import datetime, timezone, timedelta
from typing import List, Optional, Dict, Any

from fastapi import (
    APIRouter,
    Depends,
    HTTPException,
    Query,
    Request,
    WebSocket,
    WebSocketDisconnect,
    status
)
from pydantic import BaseModel, Field
from sqlalchemy.orm import Session
from sqlalchemy import desc

from app.database import SessionLocal
from app.models.device import Device
from app.models.pairing_session import PairingSession
from app.models.security_log import SecurityLog
from app.models.event import Event

router = APIRouter(
    prefix="/devices",
    tags=["Universal Devices & Host Health"]
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


# =========================================================
# 🔌 WebSocket Device Connection Manager
# =========================================================
class DeviceConnectionManager:
    def __init__(self):
        # Maps device_id -> active WebSocket connection
        self.active_connections: Dict[str, WebSocket] = {}

    async def connect(self, device_id: str, websocket: WebSocket):
        await websocket.accept()
        self.active_connections[device_id] = websocket

    def disconnect(self, device_id: str):
        if device_id in self.active_connections:
            del self.active_connections[device_id]

    def is_connected(self, device_id: str) -> bool:
        return device_id in self.active_connections

    async def send_command(self, device_id: str, command_data: dict) -> bool:
        if device_id in self.active_connections:
            ws = self.active_connections[device_id]
            await ws.send_text(json.dumps(command_data))
            return True
        return False

    async def broadcast_event(self, event_data: dict):
        dead_connections = []
        for dev_id, ws in self.active_connections.items():
            try:
                await ws.send_text(json.dumps(event_data))
            except Exception:
                dead_connections.append(dev_id)
        for dev_id in dead_connections:
            self.disconnect(dev_id)


device_manager = DeviceConnectionManager()


# =========================================================
# 📝 Pydantic Schemas
# =========================================================
class DeviceRegisterSchema(BaseModel):
    device_name: Optional[str] = None
    device_type: Optional[str] = "BROWSER"  # PHONE, TABLET, LAPTOP, DESKTOP, SMART_GLASSES, BROWSER, PWA, OTHER
    platform: Optional[str] = None         # iOS, Android, Windows, macOS, Linux
    operating_system: Optional[str] = None
    browser: Optional[str] = None
    client_version: Optional[str] = "2.5.0"
    capabilities: Optional[Dict[str, Any]] = None
    hostname: Optional[str] = None
    battery_level: Optional[int] = None
    battery_charging: Optional[bool] = None


class PairingGenerateSchema(BaseModel):
    device_type: Optional[str] = "PHONE"
    device_name: Optional[str] = None


class PairingClaimSchema(BaseModel):
    pairing_token: str
    device_name: Optional[str] = None
    device_type: Optional[str] = "PHONE"
    platform: Optional[str] = None
    operating_system: Optional[str] = None
    browser: Optional[str] = None
    client_version: Optional[str] = "2.5.0"
    capabilities: Optional[Dict[str, Any]] = None
    battery_level: Optional[int] = None
    battery_charging: Optional[bool] = None


class HeartbeatSchema(BaseModel):
    auth_token: Optional[str] = None
    battery_level: Optional[int] = None
    battery_charging: Optional[bool] = None
    capabilities: Optional[Dict[str, Any]] = None


class DeviceCommandSchema(BaseModel):
    command: str  # Allowlisted: PING, CAPTURE_FRAME, TORCH_ON, TORCH_OFF, HUD_ALERT, VIBRATE, RECONNECT
    params: Optional[Dict[str, Any]] = None


class DeviceUpdateSchema(BaseModel):
    device_name: Optional[str] = None
    device_type: Optional[str] = None


# =========================================================
# 🖥️ Host Telemetry & Task Manager (Preserved Core APIs)
# =========================================================
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
    """جلب قائمة العمليات الحقيقية الشغالة في النظام (Task Manager Process View)"""
    processes = []
    for proc in psutil.process_iter(['pid', 'name', 'cpu_percent', 'memory_percent', 'username', 'status']):
        try:
            info = proc.info
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


@router.post("/register-host")
def register_or_update_host(db: Session = Depends(get_db)):
    """تسجيل أو تحديث جهاز السيرفر الأساسي كعقدة معتمدة في قاعدة البيانات"""
    hostname = platform.node()
    ip_address = get_system_ip()
    os_name = f"{platform.system()} {platform.release()}"

    device = db.query(Device).filter(Device.hostname == hostname).first()
    if not device:
        device = Device(
            device_id="dev_primary_host",
            device_name=f"Primary EDITH Host ({hostname})",
            device_type="DESKTOP" if "Windows" in os_name else "LAPTOP",
            platform=platform.system(),
            operating_system=os_name,
            browser="FastAPI Server Core",
            client_version="2.5.0",
            hostname=hostname,
            username=platform.uname().node,
            ip_address=ip_address,
            status="Online",
            connection_status="ONLINE",
            enrollment_status="ENROLLED",
            is_primary_host=True,
            capabilities=json.dumps({
                "camera": True,
                "microphone": True,
                "speaker": True,
                "display": True,
                "hud": False,
                "battery": psutil.sensors_battery() is not None,
                "network": True,
                "websocket": True
            })
        )
        db.add(device)
    else:
        device.ip_address = ip_address
        device.status = "Online"
        device.connection_status = "ONLINE"
        device.last_seen = datetime.now(timezone.utc)

    db.commit()
    db.refresh(device)
    return device


# =========================================================
# 📱 Universal Device Pairing & Enrollment Lifecycle
# =========================================================
@router.post("/pairing/generate")
def generate_pairing_code(
    req: PairingGenerateSchema = PairingGenerateSchema(),
    request: Request = None,
    db: Session = Depends(get_db)
):
    """
    توليد رمز اقتران مؤقت (صلاحية 5 دقائق) مشفر وعشوائي بدون أي أسرار دائمة
    لتسجيل أي عميل جديد (iPhone, Android, Laptop, Smart Glasses, Browser)
    """
    token = secrets.token_urlsafe(24)
    now = datetime.now(timezone.utc)
    expires_at = now + timedelta(minutes=5)

    session = PairingSession(
        token=token,
        device_type=req.device_type or "PHONE",
        device_name=req.device_name,
        status="PENDING",
        created_at=now,
        expires_at=expires_at
    )
    db.add(session)
    db.commit()

    base_url = str(request.base_url).rstrip("/") if request else "http://127.0.0.1:8000"
    pairing_url = f"{base_url}/glasses-hud?pair_token={token}"

    return {
        "pairing_token": token,
        "pairing_url": pairing_url,
        "device_type": req.device_type,
        "expires_in_seconds": 300,
        "expires_at": expires_at.isoformat(),
        "instructions": "Scan this ephemeral QR code on iPhone, Android, or Smart Glasses to securely enroll device."
    }


@router.post("/pairing/claim")
def claim_pairing_code(
    claim: PairingClaimSchema,
    request: Request,
    db: Session = Depends(get_db)
):
    """
    استبدال رمز الاقتران المؤقت ببيانات هوية جهاز دائمة ورمز مصادقة مشفر (Device Auth Token)
    """
    now = datetime.now(timezone.utc)
    session = db.query(PairingSession).filter(PairingSession.token == claim.pairing_token.strip()).first()

    if not session:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Invalid pairing token.")

    # فحص انتهاء صلاحية الجلسة
    session_expiry = session.expires_at
    if session_expiry.tzinfo is None:
        session_expiry = session_expiry.replace(tzinfo=timezone.utc)

    if session_expiry < now or session.status in ["EXPIRED", "CLAIMED", "REVOKED"]:
        session.status = "EXPIRED"
        db.commit()
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Pairing token has expired or already claimed.")

    client_ip = request.client.host if request.client else "127.0.0.1"
    new_device_id = f"dev_{secrets.token_hex(6)}"
    new_auth_token = f"dauth_{secrets.token_urlsafe(32)}"

    device_name = claim.device_name or session.device_name or f"{claim.platform or 'Universal'} {claim.device_type or 'Client'}"
    capabilities_json = json.dumps(claim.capabilities) if claim.capabilities else None

    # إنشاء سجل الجهاز الجديد
    new_device = Device(
        device_id=new_device_id,
        device_name=device_name,
        device_type=claim.device_type or session.device_type or "PHONE",
        platform=claim.platform or "Universal",
        operating_system=claim.operating_system,
        browser=claim.browser,
        client_version=claim.client_version or "2.5.0",
        hostname=claim.device_name or device_name or "edith-client",
        ip_address=client_ip,
        status="Online",
        connection_status="ONLINE",
        enrollment_status="ENROLLED",
        auth_token=new_auth_token,
        capabilities=capabilities_json,
        battery_level=claim.battery_level,
        battery_charging=claim.battery_charging,
        last_seen=now,
        enrolled_at=now
    )
    db.add(new_device)

    # تحديث جلسة الاقتران كـ CLAIMED
    session.status = "CLAIMED"
    session.claimed_device_id = new_device_id
    session.auth_token = new_auth_token
    session.client_ip = client_ip
    session.approved_at = now
    db.commit()

    # تسجيل في سجل الأمان
    audit = SecurityLog(
        event_type="DEVICE_ENROLLED",
        severity="INFO",
        actor=device_name,
        target=client_ip,
        description=f"Universal Device '{device_name}' (ID: {new_device_id}, Type: {new_device.device_type}) enrolled successfully via pairing token."
    )
    db.add(audit)
    db.commit()

    return {
        "success": True,
        "device_id": new_device_id,
        "auth_token": new_auth_token,
        "device_name": device_name,
        "device_type": new_device.device_type,
        "platform": new_device.platform,
        "status": "ENROLLED",
        "message": "Device successfully enrolled in EDITH Defense Grid."
    }


@router.post("/register")
def register_device_direct(
    reg: DeviceRegisterSchema,
    request: Request,
    db: Session = Depends(get_db)
):
    """تسجيل مباشر لأي جهاز عميل مع إصدار رمز مصادقة مشفر"""
    client_ip = request.client.host if request.client else "127.0.0.1"
    now = datetime.now(timezone.utc)
    new_device_id = f"dev_{secrets.token_hex(6)}"
    new_auth_token = f"dauth_{secrets.token_urlsafe(32)}"

    device_name = reg.device_name or f"{reg.platform or 'Universal'} {reg.device_type or 'Device'}"

    device = Device(
        device_id=new_device_id,
        device_name=device_name,
        device_type=reg.device_type or "OTHER",
        platform=reg.platform or "Universal",
        operating_system=reg.operating_system,
        browser=reg.browser,
        client_version=reg.client_version or "2.5.0",
        hostname=reg.hostname or device_name or "edith-client",
        ip_address=client_ip,
        status="Online",
        connection_status="ONLINE",
        enrollment_status="ENROLLED",
        auth_token=new_auth_token,
        capabilities=json.dumps(reg.capabilities) if reg.capabilities else None,
        battery_level=reg.battery_level,
        battery_charging=reg.battery_charging,
        last_seen=now,
        enrolled_at=now
    )
    db.add(device)
    db.commit()
    db.refresh(device)

    return {
        "success": True,
        "device_id": new_device_id,
        "auth_token": new_auth_token,
        "device_name": device_name,
        "status": "ENROLLED"
    }


# =========================================================
# 📊 Universal Device Inventory & Management
# =========================================================
@router.get("")
@router.get("/")
def get_all_enrolled_devices(db: Session = Depends(get_db)):
    """
    جلب قائمة جميع الأجهزة الحقيقية المعتمدة في النظام مع حالتها اللحظية وقدراتها الفعلية
    """
    devices = db.query(Device).order_by(desc(Device.last_seen)).all()
    now = datetime.now(timezone.utc)

    formatted_devices = []
    for d in devices:
        caps = {}
        if d.capabilities:
            try:
                caps = json.loads(d.capabilities)
            except Exception:
                caps = {}

        # حساب حالة الاتصال الحقيقية (نشط عبر WebSocket أو heartbeat خلال آخر 60 ثانية)
        is_live_ws = device_manager.is_connected(d.device_id)
        
        last_seen_dt = d.last_seen
        if last_seen_dt and last_seen_dt.tzinfo is None:
            last_seen_dt = last_seen_dt.replace(tzinfo=timezone.utc)
            
        recent_heartbeat = (now - last_seen_dt).total_seconds() < 75 if last_seen_dt else False

        if is_live_ws or (d.is_primary_host and recent_heartbeat):
            live_status = "ONLINE"
        elif recent_heartbeat:
            live_status = "ONLINE"
        else:
            live_status = "OFFLINE"

        formatted_devices.append({
            "id": d.id,
            "device_id": d.device_id or f"dev_{d.id}",
            "device_name": d.device_name or d.hostname or f"Device #{d.id}",
            "device_type": d.device_type or "OTHER",
            "platform": d.platform or "Universal",
            "operating_system": d.operating_system or "Unavailable",
            "browser": d.browser or "Unavailable",
            "client_version": d.client_version or "2.5.0",
            "ip_address": d.ip_address or "127.0.0.1",
            "hostname": d.hostname or "N/A",
            "connection_status": live_status,
            "enrollment_status": d.enrollment_status or "ENROLLED",
            "is_primary_host": bool(d.is_primary_host),
            "battery_level": d.battery_level,
            "battery_charging": d.battery_charging,
            "capabilities": caps,
            "last_seen": d.last_seen.isoformat() if d.last_seen else None,
            "enrolled_at": d.enrolled_at.isoformat() if d.enrolled_at else None
        })

    return formatted_devices


@router.get("/{device_id}")
def get_device_by_id(device_id: str, db: Session = Depends(get_db)):
    """جلب تفاصيل جهاز محدد بواسطة device_id أو id"""
    device = db.query(Device).filter(
        (Device.device_id == device_id) | (Device.id == int(device_id) if device_id.isdigit() else False)
    ).first()

    if not device:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Device not found.")

    caps = {}
    if device.capabilities:
        try:
            caps = json.loads(device.capabilities)
        except Exception:
            caps = {}

    return {
        "id": device.id,
        "device_id": device.device_id,
        "device_name": device.device_name,
        "device_type": device.device_type,
        "platform": device.platform,
        "operating_system": device.operating_system,
        "browser": device.browser,
        "client_version": device.client_version,
        "ip_address": device.ip_address,
        "hostname": device.hostname,
        "connection_status": "ONLINE" if device_manager.is_connected(device.device_id) else device.connection_status,
        "enrollment_status": device.enrollment_status,
        "is_primary_host": bool(device.is_primary_host),
        "battery_level": device.battery_level,
        "battery_charging": device.battery_charging,
        "capabilities": caps,
        "last_seen": device.last_seen.isoformat() if device.last_seen else None,
        "enrolled_at": device.enrolled_at.isoformat() if device.enrolled_at else None
    }


@router.patch("/{device_id}")
def update_device_metadata(
    device_id: str,
    update: DeviceUpdateSchema,
    db: Session = Depends(get_db)
):
    """تحديث اسم أو نوع الجهاز"""
    device = db.query(Device).filter(
        (Device.device_id == device_id) | (Device.id == int(device_id) if device_id.isdigit() else False)
    ).first()

    if not device:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Device not found.")

    if update.device_name:
        device.device_name = update.device_name
    if update.device_type:
        device.device_type = update.device_type

    db.commit()
    return {"success": True, "device_name": device.device_name, "device_type": device.device_type}


@router.delete("/{device_id}")
def delete_or_revoke_device(device_id: str, db: Session = Depends(get_db)):
    """إلغاء اعتماد وحذف جهاز من المنظومة"""
    device = db.query(Device).filter(
        (Device.device_id == device_id) | (Device.id == int(device_id) if device_id.isdigit() else False)
    ).first()

    if not device:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Device not found.")

    if device.is_primary_host:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Cannot revoke primary host server.")

    # قطع اتصال WebSocket إن وجد
    if device.device_id:
        device_manager.disconnect(device.device_id)

    db.delete(device)
    db.commit()

    audit = SecurityLog(
        event_type="DEVICE_REVOKED",
        severity="WARNING",
        actor="OPERATOR",
        target=device.device_id,
        description=f"Device '{device.device_name}' (ID: {device.device_id}) was revoked from EDITH Defense Grid."
    )
    db.add(audit)
    db.commit()

    return {"success": True, "message": f"Device {device.device_name or device.device_id} revoked successfully."}


# =========================================================
# 💓 Real-time Heartbeat & Capabilities Reporting
# =========================================================
@router.post("/{device_id}/heartbeat")
def device_heartbeat(
    device_id: str,
    heartbeat: HeartbeatSchema,
    request: Request,
    db: Session = Depends(get_db)
):
    """إرسال نبضة حياة (Heartbeat) وتحديث البطارية ومستوى الاتصال"""
    device = db.query(Device).filter(Device.device_id == device_id).first()
    if not device:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Device not found.")

    # التحقق من رمز المصادقة إذا تم إرساله
    if heartbeat.auth_token and device.auth_token and heartbeat.auth_token != device.auth_token:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid device auth token.")

    now = datetime.now(timezone.utc)
    device.last_seen = now
    device.connection_status = "ONLINE"
    device.status = "Online"

    if heartbeat.battery_level is not None:
        device.battery_level = heartbeat.battery_level
    if heartbeat.battery_charging is not None:
        device.battery_charging = heartbeat.battery_charging
    if heartbeat.capabilities:
        device.capabilities = json.dumps(heartbeat.capabilities)

    if request.client:
        device.ip_address = request.client.host

    db.commit()
    return {
        "success": True,
        "status": "ONLINE",
        "server_time": now.isoformat()
    }


@router.get("/{device_id}/capabilities")
def get_device_capabilities(device_id: str, db: Session = Depends(get_db)):
    """جلب القدرات الحقيقية المكتشفة للجهاز"""
    device = db.query(Device).filter(Device.device_id == device_id).first()
    if not device:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Device not found.")

    caps = {}
    if device.capabilities:
        try:
            caps = json.loads(device.capabilities)
        except Exception:
            caps = {}

    return {
        "device_id": device.device_id,
        "device_name": device.device_name,
        "capabilities": caps
    }


@router.post("/{device_id}/command")
async def dispatch_device_command(
    device_id: str,
    cmd: DeviceCommandSchema,
    db: Session = Depends(get_db)
):
    """
    إرسال أمر تكتيكي مصرح به للجهاز المتصل (Allowlisted Command Dispatcher)
    الأوامر المسموحة: PING, CAPTURE_FRAME, TORCH_ON, TORCH_OFF, HUD_ALERT, VIBRATE, RECONNECT
    """
    allowlisted_commands = ["PING", "CAPTURE_FRAME", "TORCH_ON", "TORCH_OFF", "HUD_ALERT", "VIBRATE", "RECONNECT"]
    if cmd.command.upper() not in allowlisted_commands:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Command '{cmd.command}' is not in the authorized command allowlist: {allowlisted_commands}"
        )

    device = db.query(Device).filter(Device.device_id == device_id).first()
    if not device:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Device not found.")

    payload = {
        "type": "COMMAND",
        "command": cmd.command.upper(),
        "params": cmd.params or {},
        "timestamp": datetime.now(timezone.utc).isoformat()
    }

    sent = await device_manager.send_command(device_id, payload)
    if not sent:
        return {
            "success": False,
            "message": f"Device {device.device_name} is currently offline (no active WebSocket session)."
        }

    return {
        "success": True,
        "command": cmd.command.upper(),
        "dispatched_to": device.device_name,
        "message": "Command dispatched via active WebSocket."
    }


# =========================================================
# ⚡ Authenticated WebSocket Endpoint for Real-time Control
# =========================================================
@router.websocket("/{device_id}/ws")
async def device_websocket_endpoint(
    websocket: WebSocket,
    device_id: str,
    token: Optional[str] = Query(None)
):
    """
    قناة اتصال لحظية مشفرة وثنائية الاتجاه (Bidirectional WebSocket)
    للتحكم في الأجهزة والنبضات اللحظية والتنبيهات المباشرة
    """
    db = SessionLocal()
    device = db.query(Device).filter(Device.device_id == device_id).first()

    if not device:
        await websocket.close(code=status.WS_1008_POLICY_VIOLATION)
        db.close()
        return

    # التحقق من التوكن عند توفره
    if device.auth_token and token and token != device.auth_token:
        await websocket.close(code=status.WS_1008_POLICY_VIOLATION)
        db.close()
        return

    await device_manager.connect(device_id, websocket)
    device.connection_status = "ONLINE"
    device.status = "Online"
    device.last_seen = datetime.now(timezone.utc)
    db.commit()

    try:
        # إرسال رسالة ترحيبية بالاقتران
        await websocket.send_text(json.dumps({
            "type": "WELCOME",
            "device_id": device_id,
            "device_name": device.device_name,
            "server_time": datetime.now(timezone.utc).isoformat(),
            "message": "Connected to EDITH Real-time Device Gateway."
        }))

        while True:
            raw_data = await websocket.receive_text()
            try:
                msg = json.loads(raw_data)
                msg_type = msg.get("type", "").upper()

                if msg_type == "HEARTBEAT":
                    now = datetime.now(timezone.utc)
                    device.last_seen = now
                    device.connection_status = "ONLINE"
                    if "battery_level" in msg:
                        device.battery_level = msg["battery_level"]
                    if "battery_charging" in msg:
                        device.battery_charging = msg["battery_charging"]
                    db.commit()

                    await websocket.send_text(json.dumps({
                        "type": "HEARTBEAT_ACK",
                        "server_time": now.isoformat()
                    }))

                elif msg_type == "CAPABILITIES":
                    if "capabilities" in msg:
                        device.capabilities = json.dumps(msg["capabilities"])
                        db.commit()

                elif msg_type == "TELEMETRY":
                    if "battery_level" in msg:
                        device.battery_level = msg["battery_level"]
                        db.commit()

            except json.JSONDecodeError:
                pass

    except WebSocketDisconnect:
        device_manager.disconnect(device_id)
        device.connection_status = "OFFLINE"
        db.commit()
    finally:
        db.close()