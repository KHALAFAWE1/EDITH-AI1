import { useEffect, useRef, useState } from "react";
import MainLayout from "../layouts/MainLayout";
import { api } from "../services/api";
import {
  FaGlasses,
  FaShieldAlt,
  FaCrosshairs,
  FaBolt,
  FaMemory,
  FaUserCheck,
  FaExclamationTriangle,
  FaBroadcastTower
} from "react-icons/fa";

export default function GlassesHUD() {
  const videoRef = useRef(null);
  const [streamActive, setStreamActive] = useState(false);
  const [riskData, setRiskData] = useState({ risk_score: 15, severity: "LOW", explainable_ai: {} });
  const [telemetry, setTelemetry] = useState({ cpu_percent: 0, ram_used_gb: 0, ram_total_gb: 0 });
  const [opticalScanStatus, setOpticalScanStatus] = useState("SCANNING ENVIRONMENT");

  useEffect(() => {
    let mediaStream = null;
    async function startHUDCamera() {
      try {
        mediaStream = await navigator.mediaDevices.getUserMedia({
          video: { width: { ideal: 1280 }, height: { ideal: 720 }, facingMode: "user" },
          audio: false
        });
        if (videoRef.current) {
          videoRef.current.srcObject = mediaStream;
          setStreamActive(true);
        }
      } catch (err) {
        console.warn("Glasses HUD Camera access:", err);
      }
    }
    startHUDCamera();

    const fetchHUDData = async () => {
      try {
        const riskRes = await api.get("/risk/current");
        if (riskRes.data) setRiskData(riskRes.data);

        const telemRes = await api.get("/ai/telemetry");
        if (telemRes.data) setTelemetry(telemRes.data);
      } catch (e) {
        // quiet
      }
    };

    fetchHUDData();
    const interval = setInterval(fetchHUDData, 3000);

    return () => {
      if (mediaStream) mediaStream.getTracks().forEach((t) => t.stop());
      clearInterval(interval);
    };
  }, []);

  return (
    <MainLayout>
      {/* Header */}
      <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center", marginBottom: "18px", flexWrap: "wrap", gap: "10px" }}>
        <div>
          <h1 className="title" style={{ display: "flex", alignItems: "center", gap: "10px" }}>
            <FaGlasses style={{ color: "#00d4ff" }} /> EDITH Smart Glasses Tactical HUD
          </h1>
          <p className="subtitle">Real-time Heads-Up Display simulation mode: AR Target Locks, Biometrics, and Perimeter Risk</p>
        </div>
        <div style={{ display: "flex", alignItems: "center", gap: "8px" }}>
          <span className="badge badge-green" style={{ display: "flex", alignItems: "center", gap: "6px" }}>
            <FaBroadcastTower /> HUD LINK: ACTIVE
          </span>
        </div>
      </div>

      {/* Main HUD Viewport */}
      <div
        style={{
          position: "relative",
          width: "100%",
          minHeight: "560px",
          background: "#050816",
          borderRadius: "20px",
          overflow: "hidden",
          border: "2px solid rgba(0, 212, 255, 0.4)",
          boxShadow: "0 20px 60px rgba(0, 212, 255, 0.2)"
        }}
      >
        {/* Background Camera Feed */}
        <video
          ref={videoRef}
          autoPlay
          playsInline
          muted
          style={{ width: "100%", height: "100%", objectFit: "cover", minHeight: "560px", filter: "contrast(1.05) brightness(0.95)" }}
        />

        {/* HUD Overlay Vignette / Grid */}
        <div
          style={{
            position: "absolute",
            top: 0,
            left: 0,
            width: "100%",
            height: "100%",
            background: "radial-gradient(circle at center, transparent 40%, rgba(5, 8, 22, 0.7) 100%)",
            pointerEvents: "none"
          }}
        />

        {/* Top HUD Bar */}
        <div
          style={{
            position: "absolute",
            top: "20px",
            left: "20px",
            right: "20px",
            display: "flex",
            justifyContent: "space-between",
            alignItems: "center",
            pointerEvents: "none",
            flexWrap: "wrap",
            gap: "10px"
          }}
        >
          <div style={{ background: "rgba(11, 18, 32, 0.85)", backdropFilter: "blur(8px)", border: "1px solid rgba(0, 212, 255, 0.5)", padding: "8px 16px", borderRadius: "10px" }}>
            <span style={{ fontSize: "11px", color: "#8b9bb4", letterSpacing: "1px" }}>OPTICAL RECOGNITION STATUS</span>
            <div style={{ color: "#00d4ff", fontWeight: 700, fontSize: "14px", display: "flex", alignItems: "center", gap: "6px" }}>
              <FaCrosshairs className="spin" size={12} /> {opticalScanStatus}
            </div>
          </div>

          <div style={{ background: "rgba(11, 18, 32, 0.85)", backdropFilter: "blur(8px)", border: "1px solid rgba(0, 255, 153, 0.5)", padding: "8px 16px", borderRadius: "10px", display: "flex", gap: "16px" }}>
            <div>
              <span style={{ fontSize: "10px", color: "#8b9bb4" }}>CPU</span>
              <div style={{ color: "#00ff99", fontWeight: 700, fontSize: "13px" }}>{telemetry.cpu_percent}%</div>
            </div>
            <div>
              <span style={{ fontSize: "10px", color: "#8b9bb4" }}>RAM</span>
              <div style={{ color: "#00d4ff", fontWeight: 700, fontSize: "13px" }}>{telemetry.ram_used_gb} GB</div>
            </div>
          </div>
        </div>

        {/* Center Target Reticle Crosshair */}
        <div
          style={{
            position: "absolute",
            top: "50%",
            left: "50%",
            transform: "translate(-50%, -50%)",
            width: "220px",
            height: "220px",
            border: "2px dashed rgba(0, 212, 255, 0.6)",
            borderRadius: "50%",
            pointerEvents: "none",
            display: "flex",
            alignItems: "center",
            justifyContent: "center"
          }}
        >
          <div style={{ width: "80px", height: "80px", border: "1px solid rgba(0, 255, 153, 0.8)", borderRadius: "8px", position: "relative" }}>
            <span style={{ position: "absolute", top: "-18px", left: "0", fontSize: "9px", color: "#00ff99", fontWeight: 700, letterSpacing: "1px" }}>
              TARGET LOCK
            </span>
          </div>
        </div>

        {/* Bottom Left: Risk Gauge Card */}
        <div
          style={{
            position: "absolute",
            bottom: "20px",
            left: "20px",
            background: "rgba(11, 18, 32, 0.9)",
            backdropFilter: "blur(10px)",
            border: `1px solid ${riskData.risk_score > 50 ? "#ff3b5c" : "#00d4ff"}`,
            borderRadius: "14px",
            padding: "16px 20px",
            maxWidth: "360px",
            pointerEvents: "none"
          }}
        >
          <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center", marginBottom: "6px" }}>
            <span style={{ fontSize: "11px", color: "#8b9bb4", fontWeight: 700 }}>SECTOR THREAT ASSESSMENT</span>
            <span style={{
              background: riskData.risk_score > 50 ? "rgba(255, 59, 92, 0.2)" : "rgba(0, 255, 153, 0.2)",
              color: riskData.risk_score > 50 ? "#ff3b5c" : "#00ff99",
              padding: "2px 8px",
              borderRadius: "4px",
              fontSize: "10px",
              fontWeight: 700
            }}>
              {riskData.severity}
            </span>
          </div>
          <div style={{ fontSize: "24px", color: "#fff", fontWeight: 800, fontFamily: "monospace" }}>
            {riskData.risk_score} <span style={{ fontSize: "13px", color: "#8b9bb4" }}>/ 100</span>
          </div>
          <p style={{ color: "#00d4ff", fontSize: "11px", margin: "6px 0 0 0" }}>
            {riskData.explainable_ai?.what || "All systems operating within baseline parameters."}
          </p>
        </div>

        {/* Bottom Right: Biometric Lock Card */}
        <div
          style={{
            position: "absolute",
            bottom: "20px",
            right: "20px",
            background: "rgba(11, 18, 32, 0.9)",
            backdropFilter: "blur(10px)",
            border: "1px solid rgba(0, 255, 153, 0.4)",
            borderRadius: "14px",
            padding: "14px 18px",
            pointerEvents: "none",
            textAlign: "right"
          }}
        >
          <div style={{ color: "#00ff99", fontSize: "12px", fontWeight: 700, display: "flex", alignItems: "center", gap: "6px", justifyContent: "flex-end" }}>
            <FaUserCheck /> BIOMETRIC SCANNER ACTIVE
          </div>
          <div style={{ color: "#fff", fontSize: "13px", fontWeight: 600, marginTop: "4px" }}>
            ArcFace 512D Embedding
          </div>
          <div style={{ color: "#8b9bb4", fontSize: "11px", marginTop: "2px" }}>
            Threshold: 70% Match Rate
          </div>
        </div>
      </div>
    </MainLayout>
  );
}
