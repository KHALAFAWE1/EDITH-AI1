import { useEffect, useRef, useState } from "react";
import MainLayout from "../layouts/MainLayout";
import { api } from "../services/api";
import { useLanguage } from "../context/LanguageContext";
import {
  FaGlasses,
  FaShieldAlt,
  FaCrosshairs,
  FaQrcode,
  FaMobileAlt,
  FaCheckCircle,
  FaTimesCircle,
  FaSync,
  FaBatteryFull,
  FaPlug,
  FaUserCheck,
  FaBroadcastTower
} from "react-icons/fa";

export default function GlassesHUD() {
  const { t } = useLanguage();
  const videoRef = useRef(null);
  const [streamActive, setStreamActive] = useState(false);
  const [riskData, setRiskData] = useState({ risk_score: 15, severity: "LOW", explainable_ai: {} });
  const [telemetry, setTelemetry] = useState({ cpu_percent: 0, ram_used_gb: 0 });
  const [glassesStatus, setGlassesStatus] = useState({ connected: false, status: "No Device Paired", device: null });
  const [pairingData, setPairingData] = useState(null);
  const [loadingQR, setLoadingQR] = useState(false);
  const [cameraPermissionError, setCameraPermissionError] = useState(false);

  // Check if opened with pair_token on mobile
  useEffect(() => {
    const urlParams = new URLSearchParams(window.location.search);
    const token = urlParams.get("pair_token");
    if (token) {
      // Automatic client companion pairing
      async function autoPairCompanion() {
        try {
          const battery = navigator.getBattery ? await navigator.getBattery() : null;
          const batteryLevel = battery ? Math.round(battery.level * 100) : null;
          await api.post("/glasses/pair-client", {
            token: token,
            device_name: navigator.userAgent.includes("iPhone") ? "iPhone EDITH Glasses Companion" : "Mobile Smart Glasses Client",
            device_type: "iPhone_Companion",
            battery_level: batteryLevel,
            camera_active: true,
            mic_active: true
          });
          alert("✅ Paired Successfully as EDITH Smart Glasses Companion!");
        } catch (e) {
          console.warn("Auto pair error:", e);
        }
      }
      autoPairCompanion();
    }
  }, []);

  // Fetch telemetry and status
  const fetchStatus = async () => {
    try {
      const gRes = await api.get("/glasses/status");
      if (gRes.data) setGlassesStatus(gRes.data);

      const rRes = await api.get("/risk/current");
      if (rRes.data) setRiskData(rRes.data);

      const tRes = await api.get("/ai/telemetry");
      if (tRes.data) setTelemetry(tRes.data);
    } catch (err) {
      console.warn("HUD fetch error:", err);
    }
  };

  useEffect(() => {
    let mediaStream = null;
    async function startHUDCamera() {
      try {
        setCameraPermissionError(false);
        mediaStream = await navigator.mediaDevices.getUserMedia({
          video: { width: { ideal: 1280 }, height: { ideal: 720 }, facingMode: "user" },
          audio: false
        });
        if (videoRef.current) {
          videoRef.current.srcObject = mediaStream;
          setStreamActive(true);
        }
      } catch (err) {
        setCameraPermissionError(true);
      }
    }

    startHUDCamera();
    fetchStatus();
    const interval = setInterval(fetchStatus, 4000);

    return () => {
      if (mediaStream) mediaStream.getTracks().forEach((t) => t.stop());
      clearInterval(interval);
    };
  }, []);

  const handleGenerateQR = async () => {
    try {
      setLoadingQR(true);
      const res = await api.post("/glasses/generate-pairing-qr");
      setPairingData(res.data);
    } catch (e) {
      console.warn("Failed to generate pairing QR:", e);
    } finally {
      setLoadingQR(false);
    }
  };

  const handleDisconnect = async () => {
    try {
      await api.post("/glasses/disconnect");
      setPairingData(null);
      fetchStatus();
    } catch (e) {
      console.warn("Disconnect error:", e);
    }
  };

  return (
    <MainLayout>
      {/* Header */}
      <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center", marginBottom: "20px", flexWrap: "wrap", gap: "10px" }}>
        <div>
          <h1 className="title" style={{ display: "flex", alignItems: "center", gap: "10px" }}>
            <FaGlasses style={{ color: "#00d4ff" }} /> {t("glasses.title")}
          </h1>
          <p className="subtitle">{t("glasses.subtitle")}</p>
        </div>

        <div style={{ display: "flex", gap: "10px", alignItems: "center" }}>
          {glassesStatus.connected ? (
            <button
              onClick={handleDisconnect}
              style={{ background: "rgba(255, 59, 92, 0.15)", border: "1px solid #ff3b5c", color: "#ff3b5c", padding: "8px 14px", borderRadius: "8px", fontWeight: 700, cursor: "pointer", fontSize: "12px" }}
            >
              {t("glasses.disconnect")}
            </button>
          ) : (
            <button
              onClick={handleGenerateQR}
              disabled={loadingQR}
              style={{
                background: "linear-gradient(135deg, #00d4ff 0%, #0077ff 100%)",
                color: "#050816",
                border: "none",
                borderRadius: "10px",
                padding: "10px 18px",
                fontWeight: 700,
                fontSize: "13px",
                display: "flex",
                alignItems: "center",
                gap: "8px",
                cursor: "pointer"
              }}
            >
              <FaQrcode /> {t("glasses.generate_qr")}
            </button>
          )}
        </div>
      </div>

      {/* QR Pairing Modal */}
      {pairingData && (
        <div style={{ background: "#111827", border: "1px solid rgba(0, 212, 255, 0.4)", borderRadius: "16px", padding: "20px", marginBottom: "20px", display: "flex", alignItems: "center", justifyContent: "space-between", flexWrap: "wrap", gap: "20px" }}>
          <div>
            <h3 style={{ color: "#00d4ff", margin: "0 0 6px 0", display: "flex", alignItems: "center", gap: "8px" }}>
              <FaMobileAlt /> {t("glasses.qr_title")}
            </h3>
            <p style={{ color: "#8b9bb4", fontSize: "13px", margin: 0, maxWidth: "500px" }}>
              {t("glasses.qr_desc")}
            </p>
            <div style={{ marginTop: "10px", color: "#00ff99", fontSize: "12px", fontFamily: "monospace" }}>
              {t("glasses.expires_in")} 300s | Token: {pairingData.pairing_token.substring(0, 12)}...
            </div>
          </div>

          <div style={{ background: "#fff", padding: "12px", borderRadius: "12px", display: "flex", flexDirection: "column", alignItems: "center" }}>
            <img
              src={`https://api.qrserver.com/v1/create-qr-code/?size=140x140&data=${encodeURIComponent(pairingData.pairing_url)}`}
              alt="Pairing QR Code"
              style={{ width: "140px", height: "140px" }}
            />
            <span style={{ color: "#000", fontSize: "10px", fontWeight: 700, marginTop: "4px" }}>SCAN WITH IPHONE / GLASSES</span>
          </div>
        </div>
      )}

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
        {cameraPermissionError ? (
          <div style={{ width: "100%", height: "100%", minHeight: "560px", display: "flex", flexDirection: "column", alignItems: "center", justifyContent: "center", color: "#8b9bb4" }}>
            <FaCrosshairs size={48} color="#ff3b5c" style={{ marginBottom: "12px" }} />
            <h3 style={{ color: "#fff" }}>Camera Stream Offline</h3>
            <p style={{ fontSize: "13px" }}>Please grant browser camera permission or pair iPhone companion camera.</p>
          </div>
        ) : (
          <video
            ref={videoRef}
            autoPlay
            playsInline
            muted
            style={{ width: "100%", height: "100%", objectFit: "cover", minHeight: "560px", filter: "contrast(1.05) brightness(0.95)" }}
          />
        )}

        {/* HUD Overlay Vignette */}
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
            <span style={{ fontSize: "11px", color: "#8b9bb4", letterSpacing: "1px" }}>{t("glasses.optical_status")}</span>
            <div style={{ color: "#00d4ff", fontWeight: 700, fontSize: "13px", display: "flex", alignItems: "center", gap: "6px" }}>
              <FaBroadcastTower className="spin" size={12} /> {glassesStatus.connected ? glassesStatus.device?.name : "ACTIVE LOCAL OPTICAL SENSOR"}
            </div>
          </div>

          <div style={{ background: "rgba(11, 18, 32, 0.85)", backdropFilter: "blur(8px)", border: `1px solid ${glassesStatus.connected ? "#00ff99" : "#ffaa00"}`, padding: "8px 16px", borderRadius: "10px", display: "flex", alignItems: "center", gap: "10px" }}>
            <span style={{ width: "8px", height: "8px", borderRadius: "50%", background: glassesStatus.connected ? "#00ff99" : "#ffaa00", display: "inline-block" }}></span>
            <span style={{ color: "#fff", fontSize: "12px", fontWeight: 600 }}>
              {glassesStatus.connected ? t("glasses.status_connected") : t("glasses.status_disconnected")}
            </span>
          </div>
        </div>

        {/* Center Target Reticle */}
        <div
          style={{
            position: "absolute",
            top: "50%",
            left: "50%",
            transform: "translate(-50%, -50%)",
            width: "200px",
            height: "200px",
            border: "2px dashed rgba(0, 212, 255, 0.6)",
            borderRadius: "50%",
            pointerEvents: "none",
            display: "flex",
            alignItems: "center",
            justifyContent: "center"
          }}
        >
          <div style={{ width: "70px", height: "70px", border: "1px solid rgba(0, 255, 153, 0.8)", borderRadius: "8px", position: "relative" }}>
            <span style={{ position: "absolute", top: "-18px", left: "0", fontSize: "9px", color: "#00ff99", fontWeight: 700, letterSpacing: "1px" }}>
              {t("glasses.target_lock")}
            </span>
          </div>
        </div>

        {/* Bottom Left: Threat Assessment */}
        <div
          style={{
            position: "absolute",
            bottom: "20px",
            left: "20px",
            background: "rgba(11, 18, 32, 0.9)",
            backdropFilter: "blur(10px)",
            border: `1px solid ${riskData.risk_score > 50 ? "#ff3b5c" : "#00d4ff"}`,
            borderRadius: "14px",
            padding: "14px 18px",
            maxWidth: "340px",
            pointerEvents: "none"
          }}
        >
          <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center", marginBottom: "4px" }}>
            <span style={{ fontSize: "11px", color: "#8b9bb4", fontWeight: 700 }}>{t("glasses.threat_assessment")}</span>
            <span style={{ background: riskData.risk_score > 50 ? "rgba(255,59,92,0.2)" : "rgba(0,255,153,0.2)", color: riskData.risk_score > 50 ? "#ff3b5c" : "#00ff99", padding: "2px 8px", borderRadius: "4px", fontSize: "10px", fontWeight: 700 }}>
              {riskData.severity}
            </span>
          </div>
          <div style={{ fontSize: "22px", color: "#fff", fontWeight: 800, fontFamily: "monospace" }}>
            {riskData.risk_score} <span style={{ fontSize: "12px", color: "#8b9bb4" }}>/ 100</span>
          </div>
          <p style={{ color: "#00d4ff", fontSize: "11px", margin: "4px 0 0 0" }}>
            {riskData.explainable_ai?.what || "All systems operating within baseline parameters."}
          </p>
        </div>

        {/* Bottom Right: Telemetry Mini-Gauge */}
        <div
          style={{
            position: "absolute",
            bottom: "20px",
            right: "20px",
            background: "rgba(11, 18, 32, 0.9)",
            backdropFilter: "blur(10px)",
            border: "1px solid rgba(0, 255, 153, 0.4)",
            borderRadius: "14px",
            padding: "12px 16px",
            pointerEvents: "none",
            textAlign: "right"
          }}
        >
          <div style={{ color: "#00ff99", fontSize: "12px", fontWeight: 700, display: "flex", alignItems: "center", gap: "6px", justifyContent: "flex-end" }}>
            <FaUserCheck /> BIOMETRIC SCANNER ACTIVE
          </div>
          <div style={{ color: "#fff", fontSize: "12px", fontWeight: 600, marginTop: "4px" }}>
            ArcFace 512D Embedding
          </div>
          <div style={{ color: "#8b9bb4", fontSize: "11px", marginTop: "2px" }}>
            CPU: {telemetry.cpu_percent}% | RAM: {telemetry.ram_used_gb} GB
          </div>
        </div>
      </div>
    </MainLayout>
  );
}
