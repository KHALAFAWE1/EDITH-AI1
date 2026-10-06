import os
import socket
import psutil
import datetime
import subprocess
import re
from typing import Optional, List
from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel
from sqlalchemy.orm import Session
from sqlalchemy import desc

from app.database import SessionLocal
from app.models.network_device import NetworkDevice
from app.models.event import Event
from app.models.security_log import SecurityLog

router = APIRouter(
    prefix="/cyber",
    tags=["CyberVision & Defensive Network Telemetry"]
)


def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


def get_real_interface_mac(target_ip: str) -> Optional[str]:
    """استخراج عنوان MAC الحقيقي للواجهة الشبكية بدون أي قيم وهمية"""
    try:
        net_if = psutil.net_if_addrs()
        for iface_name, addrs in net_if.items():
            ip_matched = False
            mac_found = None
            for addr in addrs:
                if addr.family == socket.AF_INET and addr.address == target_ip:
                    ip_matched = True
                # AF_LINK on Unix or -1 on Windows represents MAC
                if hasattr(psutil, "AF_LINK") and addr.family == psutil.AF_LINK:
                    mac_found = addr.address
                elif addr.family == -1 or (hasattr(socket, "AF_LINK") and addr.family == socket.AF_LINK):
                    mac_found = addr.address
                elif len(addr.address.split("-")) == 6 or len(addr.address.split(":")) == 6:
                    mac_found = addr.address
            if ip_matched and mac_found:
                return mac_found
    except Exception:
        pass
    return None


def scan_local_network_defensive(db: Session):
    """فحص واكتشاف الأجهزة والواجهات المتصلة بالشبكة الحقيقية"""
    hostname = socket.gethostname()
    local_ip = "127.0.0.1"
    try:
        s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        s.connect(("8.8.8.8", 80))
        local_ip = s.getsockname()[0]
        s.close()
    except Exception:
        pass

    # تسجيل الجهاز المضيف الحقيقي
    host_node = db.query(NetworkDevice).filter(NetworkDevice.ip_address == local_ip).first()
    real_host_mac = get_real_interface_mac(local_ip)
    
    if not host_node:
        host_node = NetworkDevice(
            ip_address=local_ip,
            mac_address=real_host_mac,
            hostname=hostname,
            device_type="Command Workstation (Host)",
            vendor="Primary Operating Node",
            is_authorized=True,
            status="Active",
            risk_level="LOW"
        )
        db.add(host_node)
        db.commit()
    else:
        if real_host_mac and not host_node.mac_address:
            host_node.mac_address = real_host_mac
        host_node.last_seen = datetime.datetime.now(datetime.timezone.utc)
        db.commit()

    # فحص الواجهات الشبكية الحقيقية
    net_if = psutil.net_if_addrs()
    for iface_name, addrs in net_if.items():
        mac_addr = None
        for addr in addrs:
            if len(addr.address.split("-")) == 6 or len(addr.address.split(":")) == 6:
                mac_addr = addr.address

        for addr in addrs:
            if addr.family == socket.AF_INET and not addr.address.startswith("127."):
                node = db.query(NetworkDevice).filter(NetworkDevice.ip_address == addr.address).first()
                if not node:
                    node = NetworkDevice(
                        ip_address=addr.address,
                        mac_address=mac_addr,
                        hostname=f"{iface_name}",
                        device_type="Network Interface Adapter",
                        vendor=iface_name,
                        is_authorized=True,
                        status="Active",
                        risk_level="LOW"
                    )
                    db.add(node)
                    db.commit()
                else:
                    if mac_addr and not node.mac_address:
                        node.mac_address = mac_addr
                    node.last_seen = datetime.datetime.now(datetime.timezone.utc)
                    db.commit()


class DeviceEnrollSchema(BaseModel):
    ip_address: str
    hostname: str
    device_type: Optional[str] = "Managed Station"
    vendor: Optional[str] = "Authorized Node"
    is_authorized: Optional[bool] = True


@router.get("/nodes")
def get_monitored_nodes(db: Session = Depends(get_db)):
    """جلب قائمة الأجهزة والعقد الشبكية الحقيقية المراقبة"""
    scan_local_network_defensive(db)
    nodes = db.query(NetworkDevice).order_by(desc(NetworkDevice.last_seen)).all()
    return [
        {
            "id": n.id,
            "ip_address": n.ip_address,
            "mac_address": n.mac_address,  # null if not discovered, never fake
            "hostname": n.hostname,
            "vendor": n.vendor,
            "device_type": n.device_type,
            "is_authorized": n.is_authorized,
            "status": n.status,
            "risk_level": n.risk_level,
            "last_seen": n.last_seen
        }
        for n in nodes
    ]


@router.post("/scan")
def trigger_network_scan(db: Session = Depends(get_db)):
    """تشغيل فحص فوري للواجهات والعقد الدفاعية الحقيقية"""
    scan_local_network_defensive(db)
    total_nodes = db.query(NetworkDevice).count()
    unauthorized = db.query(NetworkDevice).filter(NetworkDevice.is_authorized == False).count()

    # تسجيل الفحص في سجل الأمان
    log_entry = SecurityLog(
        event_type="CYBER_SCAN",
        severity="INFO",
        actor="SYSTEM",
        description=f"Passive network scan discovered {total_nodes} nodes with {unauthorized} unauthorized."
    )
    db.add(log_entry)
    db.commit()

    return {
        "success": True,
        "nodes_discovered": total_nodes,
        "unauthorized_devices": unauthorized,
        "message": "CyberVision network discovery synchronized with real OS telemetry."
    }


@router.post("/enroll")
def enroll_device(req: DeviceEnrollSchema, db: Session = Depends(get_db)):
    """تسجيل جهاز أو عقدة شبكية جديدة في نطاق الإدارة المعتمد"""
    existing = db.query(NetworkDevice).filter(NetworkDevice.ip_address == req.ip_address.strip()).first()
    if existing:
        existing.hostname = req.hostname.strip()
        existing.device_type = req.device_type or existing.device_type
        existing.is_authorized = req.is_authorized
        existing.last_seen = datetime.datetime.now(datetime.timezone.utc)
        db.commit()
        return {"success": True, "message": f"Updated configuration for node {existing.ip_address}."}

    new_device = NetworkDevice(
        ip_address=req.ip_address.strip(),
        mac_address=get_real_interface_mac(req.ip_address.strip()),
        hostname=req.hostname.strip(),
        device_type=req.device_type or "Managed Station",
        vendor=req.vendor or "Enrolled Node",
        is_authorized=req.is_authorized,
        status="Active",
        risk_level="LOW" if req.is_authorized else "HIGH"
    )
    db.add(new_device)
    db.commit()
    db.refresh(new_device)

    # تسجيل في سجل التدقيق
    audit = SecurityLog(
        event_type="DEVICE_ENROLL",
        severity="INFO",
        actor="ADMIN",
        target=new_device.ip_address,
        description=f"Device {new_device.hostname} ({new_device.ip_address}) enrolled under management."
    )
    db.add(audit)
    db.commit()

    return {"success": True, "device_id": new_device.id, "message": "Device successfully enrolled."}


@router.delete("/nodes/{device_id}")
def remove_device_from_management(device_id: int, db: Session = Depends(get_db)):
    """إلغاء إدارة العقدة وحذفها من سجل المراقبة"""
    device = db.query(NetworkDevice).filter(NetworkDevice.id == device_id).first()
    if not device:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Device not found.")

    ip_info = device.ip_address
    host_info = device.hostname
    db.delete(device)
    db.commit()

    audit = SecurityLog(
        event_type="DEVICE_REMOVE",
        severity="WARNING",
        actor="ADMIN",
        target=ip_info,
        description=f"Device {host_info} ({ip_info}) removed from EDITH management."
    )
    db.add(audit)
    db.commit()

    return {"success": True, "message": f"Device {host_info} removed."}


@router.get("/correlate")
def get_physical_cyber_correlation(db: Session = Depends(get_db)):
    """
    الربط الحقيقي بين الأحداث الفيزيائية (الكاميرا) والأحداث الشبكية عند حدوثها الفعلي
    """
    now = datetime.datetime.now(datetime.timezone.utc)
    five_min_ago = now - datetime.timedelta(minutes=5)

    recent_optical = db.query(Event).filter(
        Event.source == "OPTICAL_SENSOR",
        Event.timestamp >= five_min_ago
    ).order_by(desc(Event.timestamp)).limit(5).all()

    recent_network_events = db.query(Event).filter(
        Event.source == "NETWORK_SCANNER",
        Event.timestamp >= five_min_ago
    ).order_by(desc(Event.timestamp)).limit(5).all()

    correlations = []
    if recent_optical and recent_network_events:
        for opt in recent_optical:
            for net in recent_network_events:
                # تحقق من فارق التوقيت الحقيقي (خلال دقيقة واحدة)
                time_diff = abs((opt.timestamp - net.timestamp).total_seconds()) if opt.timestamp and net.timestamp else 999
                if time_diff <= 60:
                    correlations.append({
                        "correlation_id": f"CORR-{opt.id}-{net.id}",
                        "physical_trigger": opt.summary,
                        "cyber_trigger": net.summary,
                        "confidence": 0.88,
                        "correlation_status": "REAL_CONCURRENT_EVENT",
                        "time_delta_seconds": int(time_diff),
                        "explanation": f"تم رصد نشاط فيزيائي وبصري متزامن مع نشاط شبكي بفارق {int(time_diff)} ثوانٍ.",
                        "risk": "HIGH" if (opt.is_anomaly or net.is_anomaly) else "LOW"
                    })

    return {
        "correlation_active": True,
        "correlated_events": correlations,
        "total_correlations": len(correlations),
        "message": "No concurrent physical-cyber anomalies in the last 5 minutes." if not correlations else None
    }
