import React, { useEffect, useState, useRef, useCallback } from "react";
import { api } from "../services/api";
import {
  FaMobileAlt,
  FaTabletAlt,
  FaLaptop,
  FaDesktop,
  FaGlasses,
  FaCamera,
  FaMicrophone,
  FaBatteryFull,
  FaBatteryThreeQuarters,
  FaBatteryHalf,
  FaBatteryQuarter,
  FaPlug,
  FaWifi,
  FaQrcode,
  FaCheckCircle,
  FaTimesCircle,
  FaSync,
  FaShieldAlt,
  FaBroadcastTower,
  FaCrosshairs,
  FaVolumeUp,
  FaBolt,
  FaRedo
} from "react-icons/fa";

export default function UniversalClient() {
  const [deviceInfo, setDeviceInfo] = useState(null);
  const [enrolled, setEnrolled] = useState(false);
  const [pairingToken, setPairingToken] = useState("");
  const [loading, setLoading] = useState(false);
  const [errorMsg, setErrorMsg] = useState("");
  const [wsStatus, setWsStatus] = useState("DISCONNECTED"); // CONNECTED, CONNECTING, DISCONNECTED
  const [lastPing, setLastPing] = useState(null);
  const [alertBanner, setAlertBanner] = useState(null);

  // Live Hardware Telemetry
  const [batteryState, setBatteryState] = useState({ supported: false, level: null, charging: null });
  const [cameraActive, setCameraActive] = useState(false);
  const [facingMode, setFacingMode] = useState("environment"); // "user" or "environment"
  const [availableCameras, setAvailableCameras] = useState([]);
  const [selectedCameraId, setSelectedCameraId] = useState("");
  const [threatScore, setThreatScore] = useState(15);

  const videoRef = useRef(null);
  const streamRef = useRef(null);
  const wsRef = useRef(null);
  const heartbeatIntervalRef = useRef(null);

  // =========================================================
  // 🔍 Real Hardware Capability & Platform Detection
  // =========================================================
  const detectCapabilities = useCallback(async () => {
    const caps = {
      camera: false,
      microphone: false,
      speaker: false,
      display: true,
      hud: true,
      battery: false,
      gps: false,
      gyroscope: false,
      accelerometer: false,
      touch: false,
      vibration: false,
      websocket: false,
      webrtc: false
    };

    // WebSocket & WebRTC
    caps.websocket = "WebSocket" in window;
    caps.webrtc = "RTCPeerConnection" in window;
    caps.touch = "ontouchstart" in window || navigator.maxTouchPoints > 0;
    caps.vibration = "vibrate" in navigator;
    caps.gps = "geolocation" in navigator;
    caps.speaker = "AudioContext" in window || "webkitAudioContext" in window;

    // Sensors (Gyro / Accelerometer)
    if ("DeviceOrientationEvent" in window) caps.gyroscope = true;
    if ("DeviceMotionEvent" in window) caps.accelerometer = true;

    // Media Devices (Camera / Mic)
    if (navigator.mediaDevices && navigator.mediaDevices.getUserMedia) {
      try {
        const devices = await navigator.mediaDevices.enumerateDevices();
        const videoInputs = devices.filter((d) => d.kind === "videoinput");
        const audioInputs = devices.filter((d) => d.kind === "audioinput");
        caps.camera = videoInputs.length > 0;
        caps.microphone = audioInputs.length > 0;
        setAvailableCameras(videoInputs);
        if (videoInputs.length > 0 && !selectedCameraId) {
          setSelectedCameraId(videoInputs[0].deviceId);
        }
      } catch (e) {
        caps.camera = true; // API exists, permissions pending
      }
    }

    // Battery API (Gracefully unsupported on iOS Safari)
    if (navigator.getBattery) {
      try {
        const b = await navigator.getBattery();
        caps.battery = true;
        setBatteryState({
          supported: true,
          level: Math.round(b.level * 100),
          charging: b.charging
        });

        b.addEventListener("levelchange", () => {
          setBatteryState((prev) => ({ ...prev, level: Math.round(b.level * 100) }));
        });
        b.addEventListener("chargingchange", () => {
          setBatteryState((prev) => ({ ...prev, charging: b.charging }));
        });
      } catch (e) {
        caps.battery = false;
      }
    }

    return caps;
  }, [selectedCameraId]);

  // Determine Platform / Device Type accurately
  const getDeviceMeta = () => {
    const ua = navigator.userAgent || "";
    let platform = "Universal";
    let deviceType = "BROWSER";
    let os = "Web OS";

    if (/iPhone/i.test(ua)) {
      platform = "iOS";
      deviceType = "PHONE";
      os = "Apple iOS";
    } else if (/iPad/i.test(ua)) {
      platform = "iOS";
      deviceType = "TABLET";
      os = "Apple iPadOS";
    } else if (/Android/i.test(ua)) {
      platform = "Android";
      deviceType = /Mobile/i.test(ua) ? "PHONE" : "TABLET";
      os = "Google Android";
    } else if (/Windows/i.test(ua)) {
      platform = "Windows";
      deviceType = "DESKTOP";
      os = "Microsoft Windows";
    } else if (/Macintosh/i.test(ua)) {
      platform = "macOS";
      deviceType = "LAPTOP";
      os = "Apple macOS";
    } else if (/Linux/i.test(ua)) {
      platform = "Linux";
      deviceType = "DESKTOP";
      os = "GNU/Linux";
    }

    // Browser
    let browser = "Web Browser";
    if (/Chrome/i.test(ua) && !/Edge/i.test(ua)) browser = "Chrome";
    else if (/Safari/i.test(ua) && !/Chrome/i.test(ua)) browser = "Safari";
    else if (/Firefox/i.test(ua)) browser = "Firefox";
    else if (/Edge/i.test(ua)) browser = "Edge";

    return { platform, deviceType, os, browser };
  };

  // =========================================================
  // 🔐 Secure Device Enrollment & Pairing
  // =========================================================
  const handleClaimPairing = async (tokenToUse) => {
    const token = tokenToUse || pairingToken;
    if (!token.trim()) return;

    try {
      setLoading(true);
      setErrorMsg("");

      const caps = await detectCapabilities();
      const meta = getDeviceMeta();

      const res = await api.post("/devices/pairing/claim", {
        pairing_token: token.trim(),
        device_name: `${meta.platform} ${meta.deviceType} Client`,
        device_type: meta.deviceType,
        platform: meta.platform,
        operating_system: meta.os,
        browser: meta.browser,
        client_version: "2.5.0",
        capabilities: caps,
        battery_level: batteryState.level,
        battery_charging: batteryState.charging
      });

      if (res.data.success) {
        const stored = {
          device_id: res.data.device_id,
          auth_token: res.data.auth_token,
          device_name: res.data.device_name,
          device_type: res.data.device_type,
          platform: res.data.platform
        };
        localStorage.setItem("edith_device_auth", JSON.stringify(stored));
        setDeviceInfo(stored);
        setEnrolled(true);
        connectWebSocket(stored.device_id, stored.auth_token);
      }
    } catch (err) {
      setErrorMsg(err.response?.data?.detail || "Pairing failed. Token may be expired or invalid.");
    } finally {
      setLoading(false);
    }
  };

  // =========================================================
  // ⚡ WebSocket Real-time Gateway
  // =========================================================
  const connectWebSocket = useCallback((deviceId, authToken) => {
    if (!deviceId) return;

    try {
      const loc = window.location;
      const wsProtocol = loc.protocol === "https:" ? "wss:" : "ws:";
      const wsHost = loc.host;
      const wsUrl = `${wsProtocol}//${wsHost}/devices/${deviceId}/ws?token=${authToken || ""}`;

      setWsStatus("CONNECTING");
      const ws = new WebSocket(wsUrl);

      ws.onopen = () => {
        setWsStatus("CONNECTED");
        // Start periodic heartbeat
        if (heartbeatIntervalRef.current) clearInterval(heartbeatIntervalRef.current);
        heartbeatIntervalRef.current = setInterval(() => {
          if (ws.readyState === WebSocket.OPEN) {
            ws.send(
              JSON.stringify({
                type: "HEARTBEAT",
                battery_level: batteryState.level,
                battery_charging: batteryState.charging,
                timestamp: new Date().toISOString()
              })
            );
          }
        }, 12000);
      };

      ws.onmessage = (event) => {
        try {
          const msg = JSON.parse(event.data);
          if (msg.type === "COMMAND") {
            handleServerCommand(msg);
          } else if (msg.type === "HEARTBEAT_ACK") {
            setLastPing(new Date().toLocaleTimeString());
          }
        } catch (e) {
          console.warn("WS parse error:", e);
        }
      };

      ws.onclose = () => {
        setWsStatus("DISCONNECTED");
        if (heartbeatIntervalRef.current) clearInterval(heartbeatIntervalRef.current);
      };

      ws.onerror = () => {
        setWsStatus("DISCONNECTED");
      };

      wsRef.current = ws;
    } catch (e) {
      console.warn("WebSocket init error:", e);
    }
  }, [batteryState]);

  // Handle Commands dispatched from EDITH Dashboard
  const handleServerCommand = (cmdMsg) => {
    const cmd = cmdMsg.command;
    if (cmd === "PING") {
      if (navigator.vibrate) navigator.vibrate([100, 50, 100]);
      triggerHUDAlert("⚡ PING RECEIVED FROM EDITH CORE", "#00ff99");
    } else if (cmd === "HUD_ALERT") {
      triggerHUDAlert(cmdMsg.params?.text || "TACTICAL ALERT DISPATCHED", "#ff3b5c");
    } else if (cmd === "VIBRATE") {
      if (navigator.vibrate) navigator.vibrate(200);
    }
  };

  const triggerHUDAlert = (text, color = "#00d4ff") => {
    setAlertBanner({ text, color });
    setTimeout(() => setAlertBanner(null), 4000);
  };

  // =========================================================
  // 📷 Camera Optical Stream Management
  // =========================================================
  const startCamera = async () => {
    try {
      if (streamRef.current) {
        streamRef.current.getTracks().forEach((t) => t.stop());
      }

      const constraints = {
        video: selectedCameraId
          ? { deviceId: { exact: selectedCameraId } }
          : { facingMode: facingMode, width: { ideal: 1280 }, height: { ideal: 720 } },
        audio: false
      };

      const stream = await navigator.mediaDevices.getUserMedia(constraints);
      streamRef.current = stream;
      if (videoRef.current) {
        videoRef.current.srcObject = stream;
        setCameraActive(true);
      }
    } catch (e) {
      console.warn("Camera start error:", e);
      setCameraActive(false);
    }
  };

  const stopCamera = () => {
    if (streamRef.current) {
      streamRef.current.getTracks().forEach((t) => t.stop());
      streamRef.current = null;
    }
    setCameraActive(false);
  };

  const toggleFacingMode = () => {
    setFacingMode((prev) => (prev === "user" ? "environment" : "user"));
  };

  useEffect(() => {
    if (cameraActive) {
      startCamera();
    }
  }, [facingMode, selectedCameraId]);

  // Initial Load: check local credentials & URL query pair_token
  useEffect(() => {
    detectCapabilities();

    const urlParams = new URLSearchParams(window.location.search);
    const urlToken = urlParams.get("pair_token");

    const savedAuth = localStorage.getItem("edith_device_auth");
    if (savedAuth) {
      try {
        const parsed = JSON.parse(savedAuth);
        setDeviceInfo(parsed);
        setEnrolled(true);
        connectWebSocket(parsed.device_id, parsed.auth_token);
      } catch (e) {
        localStorage.removeItem("edith_device_auth");
      }
    } else if (urlToken) {
      setPairingToken(urlToken);
      handleClaimPairing(urlToken);
    }

    return () => {
      stopCamera();
      if (wsRef.current) wsRef.current.close();
      if (heartbeatIntervalRef.current) clearInterval(heartbeatIntervalRef.current);
    };
  }, []);

  const handleDisconnect = () => {
    localStorage.removeItem("edith_device_auth");
    setDeviceInfo(null);
    setEnrolled(false);
    if (wsRef.current) wsRef.current.close();
    stopCamera();
  };

  return (
    <div
      style={{
        minHeight: "100vh",
        width: "100vw",
        background: "#050816",
        color: "#fff",
        fontFamily: "'Segoe UI', Roboto, sans-serif",
        display: "flex",
        flexDirection: "column",
        overflowX: "hidden"
      }}
    >
      {/* Top Tactical Client Header Bar */}
      <header
        style={{
          padding: "12px 18px",
          background: "#0d1222",
          borderBottom: "1px solid rgba(0, 212, 255, 0.2)",
          display: "flex",
          justifyContent: "space-between",
          alignItems: "center",
          flexWrap: "wrap",
          gap: "10px"
        }}
      >
        <div style={{ display: "flex", alignItems: "center", gap: "10px" }}>
          <FaBroadcastTower color="#00d4ff" size={18} />
          <div>
            <h2 style={{ fontSize: "15px", margin: 0, fontWeight: 800, letterSpacing: "0.5px" }}>
              EDITH UNIVERSAL CLIENT
            </h2>
            <span style={{ fontSize: "11px", color: "#8b9bb4" }}>
              {deviceInfo ? deviceInfo.device_name : "Autonomous Optical Client"}
            </span>
          </div>
        </div>

        <div style={{ display: "flex", alignItems: "center", gap: "12px" }}>
          {/* Battery Status Indicator */}
          {batteryState.supported && batteryState.level !== null ? (
            <div style={{ display: "flex", alignItems: "center", gap: "5px", fontSize: "12px", color: "#00ff99" }}>
              {batteryState.charging ? <FaPlug /> : <FaBatteryFull />}
              <span>{batteryState.level}%</span>
            </div>
          ) : (
            <span style={{ fontSize: "11px", color: "#606f8b" }}>Battery: N/A</span>
          )}

          {/* Connection Status Badge */}
          <span
            style={{
              fontSize: "11px",
              padding: "4px 10px",
              borderRadius: "12px",
              fontWeight: 700,
              display: "flex",
              alignItems: "center",
              gap: "6px",
              background: wsStatus === "CONNECTED" ? "rgba(0, 255, 153, 0.15)" : "rgba(255, 59, 92, 0.15)",
              color: wsStatus === "CONNECTED" ? "#00ff99" : "#ff3b5c",
              border: `1px solid ${wsStatus === "CONNECTED" ? "#00ff99" : "#ff3b5c"}`
            }}
          >
            <span
              style={{
                width: "7px",
                height: "7px",
                borderRadius: "50%",
                background: wsStatus === "CONNECTED" ? "#00ff99" : "#ff3b5c"
              }}
            />
            {wsStatus}
          </span>
        </div>
      </header>

      {/* Main Container */}
      <main style={{ flex: 1, padding: "clamp(14px, 3vw, 24px)", maxWidth: "900px", margin: "0 auto", width: "100%" }}>
        {/* Banner Alert if triggered */}
        {alertBanner && (
          <div
            style={{
              background: alertBanner.color === "#ff3b5c" ? "rgba(255, 59, 92, 0.2)" : "rgba(0, 255, 153, 0.2)",
              border: `1px solid ${alertBanner.color}`,
              color: alertBanner.color,
              padding: "12px 18px",
              borderRadius: "12px",
              marginBottom: "18px",
              fontWeight: 700,
              fontSize: "13px",
              textAlign: "center",
              boxShadow: `0 0 20px ${alertBanner.color}40`
            }}
          >
            {alertBanner.text}
          </div>
        )}

        {!enrolled ? (
          /* Enrollment / Pairing Screen */
          <div
            style={{
              background: "#111827",
              borderRadius: "20px",
              border: "1px solid rgba(0, 212, 255, 0.3)",
              padding: "clamp(20px, 4vw, 32px)",
              textAlign: "center"
            }}
          >
            <FaQrcode size={48} color="#00d4ff" style={{ marginBottom: "16px" }} />
            <h2 style={{ fontSize: "20px", margin: "0 0 8px 0" }}>Pair Device with EDITH Defense Grid</h2>
            <p style={{ color: "#8b9bb4", fontSize: "13px", maxWidth: "460px", margin: "0 auto 20px auto" }}>
              Scan the ephemeral pairing QR code displayed on the EDITH Command Center or enter the 5-minute pairing token below:
            </p>

            <form
              onSubmit={(e) => {
                e.preventDefault();
                handleClaimPairing();
              }}
              style={{ display: "flex", flexDirection: "column", gap: "14px", maxWidth: "380px", margin: "0 auto" }}
            >
              <input
                type="text"
                placeholder="Enter Pairing Token (e.g. tkn_...)"
                value={pairingToken}
                onChange={(e) => setPairingToken(e.target.value)}
                style={{
                  width: "100%",
                  padding: "12px 16px",
                  background: "#192033",
                  border: "1px solid rgba(0, 212, 255, 0.4)",
                  borderRadius: "10px",
                  color: "#fff",
                  outline: "none",
                  fontSize: "14px",
                  textAlign: "center"
                }}
              />

              {errorMsg && <div style={{ color: "#ff3b5c", fontSize: "12px" }}>{errorMsg}</div>}

              <button
                type="submit"
                disabled={loading || !pairingToken.trim()}
                style={{
                  background: "linear-gradient(135deg, #00d4ff 0%, #0077ff 100%)",
                  color: "#050816",
                  border: "none",
                  borderRadius: "10px",
                  padding: "12px",
                  fontWeight: 700,
                  fontSize: "14px",
                  cursor: loading ? "not-allowed" : "pointer"
                }}
              >
                {loading ? "Authenticating Device..." : "Enroll Device Securely 📱"}
              </button>
            </form>
          </div>
        ) : (
          /* Active Client Dashboard & HUD */
          <div style={{ display: "flex", flexDirection: "column", gap: "20px" }}>
            {/* Viewport Box (Optical Camera Feed / AR HUD) */}
            <div
              style={{
                position: "relative",
                width: "100%",
                minHeight: "360px",
                background: "#000",
                borderRadius: "20px",
                overflow: "hidden",
                border: "2px solid rgba(0, 212, 255, 0.4)",
                boxShadow: "0 10px 40px rgba(0, 212, 255, 0.15)"
              }}
            >
              {cameraActive ? (
                <video
                  ref={videoRef}
                  autoPlay
                  playsInline
                  muted
                  style={{ width: "100%", height: "100%", objectFit: "cover", minHeight: "360px" }}
                />
              ) : (
                <div
                  style={{
                    width: "100%",
                    height: "360px",
                    display: "flex",
                    flexDirection: "column",
                    alignItems: "center",
                    justifyContent: "center",
                    color: "#8b9bb4"
                  }}
                >
                  <FaCamera size={44} color="#00d4ff" style={{ marginBottom: "12px" }} />
                  <h3 style={{ color: "#fff", margin: "0 0 6px 0" }}>Optical Stream Standby</h3>
                  <p style={{ fontSize: "13px", margin: 0 }}>Click "Start Camera Feed" below to enable live optical sensor.</p>
                </div>
              )}

              {/* AR Reticle Overlay */}
              <div
                style={{
                  position: "absolute",
                  top: "50%",
                  left: "50%",
                  transform: "translate(-50%, -50%)",
                  width: "160px",
                  height: "160px",
                  border: "2px dashed rgba(0, 212, 255, 0.5)",
                  borderRadius: "50%",
                  pointerEvents: "none",
                  display: "flex",
                  alignItems: "center",
                  justifyContent: "center"
                }}
              >
                <div style={{ width: "50px", height: "50px", border: "1px solid rgba(0, 255, 153, 0.8)", borderRadius: "6px" }} />
              </div>

              {/* Bottom HUD Telemetry Strip */}
              <div
                style={{
                  position: "absolute",
                  bottom: "12px",
                  left: "12px",
                  right: "12px",
                  display: "flex",
                  justifyContent: "space-between",
                  alignItems: "center",
                  background: "rgba(5, 8, 22, 0.85)",
                  backdropFilter: "blur(6px)",
                  padding: "8px 14px",
                  borderRadius: "10px",
                  fontSize: "12px",
                  pointerEvents: "none"
                }}
              >
                <span style={{ color: "#00d4ff", fontFamily: "monospace" }}>ID: {deviceInfo?.device_id}</span>
                <span style={{ color: "#00ff99" }}>SECTOR THREAT: {threatScore}/100</span>
              </div>
            </div>

            {/* Media Controls Bar */}
            <div style={{ display: "flex", gap: "10px", flexWrap: "wrap", justifyContent: "space-between" }}>
              <div style={{ display: "flex", gap: "10px" }}>
                {!cameraActive ? (
                  <button
                    onClick={startCamera}
                    style={{
                      background: "linear-gradient(135deg, #00d4ff 0%, #0077ff 100%)",
                      color: "#050816",
                      border: "none",
                      padding: "10px 18px",
                      borderRadius: "10px",
                      fontWeight: 700,
                      fontSize: "13px",
                      cursor: "pointer",
                      display: "flex",
                      alignItems: "center",
                      gap: "6px"
                    }}
                  >
                    <FaCamera /> Start Camera Feed
                  </button>
                ) : (
                  <>
                    <button
                      onClick={stopCamera}
                      style={{
                        background: "rgba(255, 59, 92, 0.2)",
                        color: "#ff3b5c",
                        border: "1px solid #ff3b5c",
                        padding: "10px 16px",
                        borderRadius: "10px",
                        fontWeight: 700,
                        fontSize: "13px",
                        cursor: "pointer"
                      }}
                    >
                      Stop Camera
                    </button>

                    <button
                      onClick={toggleFacingMode}
                      style={{
                        background: "#192033",
                        color: "#00d4ff",
                        border: "1px solid rgba(0, 212, 255, 0.3)",
                        padding: "10px 16px",
                        borderRadius: "10px",
                        fontWeight: 700,
                        fontSize: "13px",
                        cursor: "pointer",
                        display: "flex",
                        alignItems: "center",
                        gap: "6px"
                      }}
                    >
                      <FaRedo /> Switch Lens ({facingMode === "user" ? "Front" : "Back"})
                    </button>
                  </>
                )}
              </div>

              <button
                onClick={handleDisconnect}
                style={{
                  background: "#192033",
                  color: "#8b9bb4",
                  border: "1px solid rgba(255, 255, 255, 0.1)",
                  padding: "10px 16px",
                  borderRadius: "10px",
                  fontSize: "13px",
                  cursor: "pointer"
                }}
              >
                Disconnect Device
              </button>
            </div>
          </div>
        )}
      </main>
    </div>
  );
}
