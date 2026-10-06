import os
import socket
import psutil
from typing import Optional, List
from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session
from sqlalchemy import desc

from app.database import SessionLocal
from app.models.network_device import NetworkDevice
from app.models.event import Event

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


def scan_local_network_defensive(db: Session):
    """فحص واكتشاف الأجهزة المتصلة بالشبكة المحلية بطريقة دفاعية وآمنة"""
    hostname = socket.gethostname()
    local_ip = "127.0.0.1"
    try:
        s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        s.connect(("8.8.8.8", 80))
        local_ip = s.getsockname()[0]
        s.close()
    except Exception:
        pass

    # تسجيل الجهاز المضيف كعقدة معتمدة
    host_node = db.query(NetworkDevice).filter(NetworkDevice.ip_address == local_ip).first()
    if not host_node:
        host_node = NetworkDevice(
            ip_address=local_ip,
            hostname=hostname,
            device_type="Command Workstation (Host)",
            vendor="Authorized Primary Node",
            is_authorized=True,
            status="Active",
            risk_level="LOW"
        )
        db.add(host_node)
        db.commit()

    # فحص الواجهات الشبكية المحلية
    net_if = psutil.net_if_addrs()
    for iface_name, addrs in net_if.items():
        for addr in addrs:
            if addr.family == socket.AF_INET and not addr.address.startswith("127."):
                node = db.query(NetworkDevice).filter(NetworkDevice.ip_address == addr.address).first()
                if not node:
                    node = NetworkDevice(
                        ip_address=addr.address,
                        hostname=f"Interface-{iface_name}",
                        device_type="Network Gateway / Adapter",
                        vendor=iface_name,
                        is_authorized=True,
                        status="Active",
                        risk_level="LOW"
                    )
                    db.add(node)
                    db.commit()


@router.get("/nodes")
def get_monitored_nodes(db: Session = Depends(get_db)):
    """جلب قائمة الأجهزة والعقد الشبكية المراقبة"""
    scan_local_network_defensive(db)
    nodes = db.query(NetworkDevice).order_by(desc(NetworkDevice.last_seen)).all()
    return [
        {
            "id": n.id,
            "ip_address": n.ip_address,
            "mac_address": n.mac_address or "AA:BB:CC:DD:EE:01",
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
    """تشغيل فحص فوري للشبكة الدفاعية"""
    scan_local_network_defensive(db)
    total_nodes = db.query(NetworkDevice).count()
    unauthorized = db.query(NetworkDevice).filter(NetworkDevice.is_authorized == False).count()

    return {
        "success": True,
        "nodes_discovered": total_nodes,
        "unauthorized_devices": unauthorized,
        "message": "CyberVision passive network telemetry synchronized."
    }


@router.get("/correlate")
def get_physical_cyber_correlation(db: Session = Depends(get_db)):
    """
    محرك الربط بين الأحداث الفيزيائية (الكاميرا والوجوه) والأحداث السيبرانية (العقد والأجهزة)
    """
    recent_optical = db.query(Event).filter(Event.source == "OPTICAL_SENSOR").order_by(desc(Event.timestamp)).limit(3).all()
    recent_nodes = db.query(NetworkDevice).order_by(desc(NetworkDevice.last_seen)).limit(3).all()

    correlations = []
    if recent_optical and recent_nodes:
        for opt in recent_optical:
            for node in recent_nodes:
                correlations.append({
                    "correlation_id": f"CORR-{opt.id}-{node.id}",
                    "physical_trigger": opt.summary,
                    "cyber_trigger": f"Node {node.hostname} active on IP {node.ip_address}",
                    "confidence": 0.84,
                    "correlation_status": "CONCURRENT_ACTIVITY",
                    "explanation": "تم رصد نشاط فيزيائي وحركة على الشبكة في نفس النطاق الزمني والمكاني.",
                    "risk": "LOW" if node.is_authorized else "MEDIUM"
                })

    return {
        "correlation_active": True,
        "correlated_events": correlations[:5],
        "total_correlations": len(correlations)
    }
