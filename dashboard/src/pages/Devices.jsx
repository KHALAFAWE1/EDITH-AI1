import { useEffect, useState } from "react";
import MainLayout from "../layouts/MainLayout";
import StatusCard from "../components/StatusCard";
import { api } from "../services/api";
import { useLanguage } from "../context/LanguageContext";
import {
  FaDesktop,
  FaMicrochip,
  FaMemory,
  FaHdd,
  FaClock,
  FaSync,
  FaTasks,
  FaBatteryFull,
  FaPlug,
  FaMobileAlt,
  FaTabletAlt,
  FaLaptop,
  FaGlasses,
  FaCamera,
  FaMicrophone,
  FaQrcode,
  FaTrash,
  FaWifi,
  FaCheckCircle,
  FaTimesCircle,
  FaBolt
} from "react-icons/fa";

export default function Devices() {
  const { t } = useLanguage();
  const [telemetry, setTelemetry] = useState(null);
  const [enrolledDevices, setEnrolledDevices] = useState([]);
  const [processes, setProcesses] = useState([]);
  const [procSort, setProcSort] = useState("cpu");
  const [loading, setLoading] = useState(true);
  const [syncing, setSyncing] = useState(false);

  // Pairing QR Modal State
  const [showPairModal, setShowPairModal] = useState(false);
  const [pairingData, setPairingData] = useState(null);
  const [generatingQR, setGeneratingQR] = useState(false);
  const [pingStatus, setPingStatus] = useState({});

  const fetchHostData = async () => {
    try {
      setLoading(true);
      const res = await api.get("/devices/telemetry");
      if (res.data && typeof res.data === "object" && !res.data.detail) {
        setTelemetry(res.data);
      }

      const devRes = await api.get("/devices");
      if (Array.isArray(devRes.data)) {
        setEnrolledDevices(devRes.data);
      }

      const procRes = await api.get(`/devices/processes?limit=30&sort_by=${procSort}`);
      if (procRes.data && Array.isArray(procRes.data.processes)) {
        setProcesses(procRes.data.processes);
      }
    } catch (err) {
      console.warn("Failed to fetch host health:", err.message);
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    fetchHostData();
    const interval = setInterval(fetchHostData, 4000);
    return () => clearInterval(interval);
  }, [procSort]);

  const handleSyncHost = async () => {
    try {
      setSyncing(true);
      await api.post("/devices/register-host");
      await fetchHostData();
    } catch (err) {
      console.error("Failed to sync host:", err);
    } finally {
      setSyncing(false);
    }
  };

  const handleGeneratePairingQR = async (deviceType = "PHONE") => {
    try {
      setGeneratingQR(true);
      const res = await api.post("/devices/pairing/generate", { device_type: deviceType });
      setPairingData(res.data);
      setShowPairModal(true);
    } catch (err) {
      console.warn("Pairing QR error:", err);
    } finally {
      setGeneratingQR(false);
    }
  };

  const handlePingDevice = async (deviceId) => {
    try {
      setPingStatus((prev) => ({ ...prev, [deviceId]: "PINGING..." }));
      const res = await api.post(`/devices/${deviceId}/command`, { command: "PING" });
      setPingStatus((prev) => ({
        ...prev,
        [deviceId]: res.data.success ? "PING SENT ⚡" : "OFFLINE"
      }));
      setTimeout(() => {
        setPingStatus((prev) => ({ ...prev, [deviceId]: null }));
      }, 3000);
    } catch (err) {
      setPingStatus((prev) => ({ ...prev, [deviceId]: "FAILED" }));
    }
  };

  const handleRevokeDevice = async (deviceId, name) => {
    if (!window.confirm(`Are you sure you want to revoke and disconnect '${name}'?`)) return;
    try {
      await api.delete(`/devices/${deviceId}`);
      await fetchHostData();
    } catch (err) {
      console.warn("Revoke error:", err);
    }
  };

  const getDeviceIcon = (type) => {
    const tLower = (type || "").toLowerCase();
    if (tLower.includes("phone") || tLower.includes("iphone") || tLower.includes("android")) return <FaMobileAlt color="#00d4ff" size={20} />;
    if (tLower.includes("tablet") || tLower.includes("ipad")) return <FaTabletAlt color="#00ff99" size={20} />;
    if (tLower.includes("glasses")) return <FaGlasses color="#ffd700" size={20} />;
    if (tLower.includes("laptop") || tLower.includes("mac")) return <FaLaptop color="#aa3bff" size={20} />;
    return <FaDesktop color="#00d4ff" size={20} />;
  };

  const cpuPercent = telemetry?.cpu?.percent || 0;
  const ramPercent = telemetry?.ram?.percent || 0;
  const storagePercent = telemetry?.storage?.percent || 0;

  const getProgressColor = (percent) => {
    if (percent > 85) return "#ff3b5c";
    if (percent > 65) return "#ffaa00";
    return "#00d4ff";
  };

  return (
    <MainLayout>
      {/* Header */}
      <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center", marginBottom: "22px", flexWrap: "wrap", gap: "10px" }}>
        <div>
          <h1 className="title" style={{ display: "flex", alignItems: "center", gap: "10px" }}>
            <FaDesktop style={{ color: "#00d4ff" }} /> {t("host.title")}
          </h1>
          <p className="subtitle">{t("host.subtitle")}</p>
        </div>

        <div style={{ display: "flex", gap: "10px", flexWrap: "wrap" }}>
          <button
            onClick={() => handleGeneratePairingQR("PHONE")}
            disabled={generatingQR}
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
              cursor: generatingQR ? "not-allowed" : "pointer"
            }}
          >
            <FaQrcode /> {t("devices_inventory.pair_device")}
          </button>

          <button
            onClick={handleSyncHost}
            disabled={syncing}
            style={{
              background: "#192033",
              color: "#00d4ff",
              border: "1px solid rgba(0, 212, 255, 0.3)",
              borderRadius: "10px",
              padding: "10px 16px",
              fontWeight: 700,
              fontSize: "13px",
              display: "flex",
              alignItems: "center",
              gap: "8px",
              cursor: syncing ? "not-allowed" : "pointer"
            }}
          >
            <FaSync className={syncing ? "spin" : ""} size={13} /> Sync Host State
          </button>
        </div>
      </div>

      {/* Real-Time Hardware Telemetry Gauges */}
      <div style={{ display: "grid", gridTemplateColumns: "repeat(auto-fit, minmax(220px, 1fr))", gap: "16px", marginBottom: "25px" }}>
        <StatusCard
          icon={<FaMicrochip />}
          title={t("host.cpu")}
          value={`${cpuPercent}%`}
          subtitle={`${telemetry?.cpu?.cores || "--"} Logical Cores (${telemetry?.cpu?.frequency_mhz || 0} MHz)`}
          accentColor={getProgressColor(cpuPercent)}
        />
        <StatusCard
          icon={<FaMemory />}
          title={t("host.ram")}
          value={`${ramPercent}%`}
          subtitle={`${telemetry?.ram?.used_gb || 0} / ${telemetry?.ram?.total_gb || 0} GB`}
          accentColor={getProgressColor(ramPercent)}
        />
        <StatusCard
          icon={<FaHdd />}
          title={t("host.storage")}
          value={`${storagePercent}%`}
          subtitle={`${telemetry?.storage?.used_gb || 0} / ${telemetry?.storage?.total_gb || 0} GB`}
          accentColor={getProgressColor(storagePercent)}
        />
        <StatusCard
          icon={<FaClock />}
          title={t("host.uptime")}
          value={telemetry?.uptime || "--"}
          subtitle={`Node: ${telemetry?.hostname || "Localhost"}`}
          accentColor="#00ff99"
        />
      </div>

      {/* ========================================================= */}
      {/* 📱 Universal Enrolled Devices Grid                         */}
      {/* ========================================================= */}
      <div style={{ background: "#111827", borderRadius: "16px", border: "1px solid rgba(0, 212, 255, 0.2)", padding: "22px", marginBottom: "25px" }}>
        <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center", marginBottom: "16px", flexWrap: "wrap", gap: "10px" }}>
          <div>
            <h3 style={{ color: "#fff", margin: 0, fontSize: "16px", display: "flex", alignItems: "center", gap: "8px" }}>
              <FaWifi color="#00d4ff" /> {t("devices_inventory.title")} ({enrolledDevices.length})
            </h3>
            <p style={{ color: "#8b9bb4", fontSize: "12px", margin: "4px 0 0 0" }}>
              {t("devices_inventory.subtitle")}
            </p>
          </div>
        </div>

        {enrolledDevices.length === 0 ? (
          <p style={{ color: "#8b9bb4", fontSize: "13px" }}>{t("devices_inventory.no_devices")}</p>
        ) : (
          <div style={{ display: "grid", gridTemplateColumns: "repeat(auto-fit, minmax(300px, 1fr))", gap: "16px" }}>
            {enrolledDevices.map((dev) => {
              const isOnline = dev.connection_status === "ONLINE";
              const caps = dev.capabilities || {};

              return (
                <div
                  key={dev.id}
                  style={{
                    background: "#192033",
                    borderRadius: "14px",
                    border: `1px solid ${isOnline ? "rgba(0, 255, 153, 0.3)" : "rgba(255,255,255,0.06)"}`,
                    padding: "16px",
                    display: "flex",
                    flexDirection: "column",
                    justifyContent: "space-between",
                    boxShadow: isOnline ? "0 4px 20px rgba(0, 255, 153, 0.08)" : "none"
                  }}
                >
                  <div>
                    {/* Header: Icon, Name, Online Badge */}
                    <div style={{ display: "flex", justifyContent: "space-between", alignItems: "flex-start", marginBottom: "10px" }}>
                      <div style={{ display: "flex", alignItems: "center", gap: "12px" }}>
                        <div style={{ width: "42px", height: "42px", borderRadius: "10px", background: "#111827", display: "flex", alignItems: "center", justifyContent: "center" }}>
                          {getDeviceIcon(dev.device_type)}
                        </div>
                        <div>
                          <h4 style={{ color: "#fff", margin: 0, fontSize: "14px", fontWeight: 700 }}>
                            {dev.device_name}
                          </h4>
                          <span style={{ color: "#8b9bb4", fontSize: "11px" }}>
                            {dev.platform} | {dev.operating_system}
                          </span>
                        </div>
                      </div>

                      <span
                        style={{
                          background: isOnline ? "rgba(0, 255, 153, 0.15)" : "rgba(255, 59, 92, 0.15)",
                          color: isOnline ? "#00ff99" : "#ff3b5c",
                          border: `1px solid ${isOnline ? "#00ff99" : "#ff3b5c"}`,
                          padding: "2px 8px",
                          borderRadius: "6px",
                          fontSize: "10px",
                          fontWeight: 700
                        }}
                      >
                        {isOnline ? "🟢 ONLINE" : "🔴 OFFLINE"}
                      </span>
                    </div>

                    {/* Metadata Strip */}
                    <div style={{ fontSize: "12px", color: "#8b9bb4", display: "flex", flexDirection: "column", gap: "4px", margin: "10px 0" }}>
                      <div>IP: <strong style={{ color: "#00d4ff", fontFamily: "monospace" }}>{dev.ip_address}</strong></div>
                      <div>Browser / App: <span>{dev.browser} (v{dev.client_version})</span></div>
                      {dev.battery_level !== null && dev.battery_level !== undefined ? (
                        <div>Battery: <strong style={{ color: "#00ff99" }}>{dev.battery_level}% {dev.battery_charging ? "⚡ (Charging)" : ""}</strong></div>
                      ) : (
                        <div>Battery: <span style={{ color: "#606f8b" }}>Unavailable</span></div>
                      )}
                    </div>

                    {/* Detected Real Capabilities Badges */}
                    <div style={{ display: "flex", gap: "6px", flexWrap: "wrap", marginTop: "10px" }}>
                      {caps.camera && <span style={{ background: "rgba(0, 212, 255, 0.15)", color: "#00d4ff", padding: "2px 6px", borderRadius: "4px", fontSize: "10px", fontWeight: 600 }}>📷 Camera</span>}
                      {caps.microphone && <span style={{ background: "rgba(0, 212, 255, 0.15)", color: "#00d4ff", padding: "2px 6px", borderRadius: "4px", fontSize: "10px", fontWeight: 600 }}>🎙️ Mic</span>}
                      {caps.hud && <span style={{ background: "rgba(255, 215, 0, 0.15)", color: "#ffd700", padding: "2px 6px", borderRadius: "4px", fontSize: "10px", fontWeight: 600 }}>🕶️ HUD</span>}
                      {caps.touch && <span style={{ background: "rgba(170, 59, 255, 0.15)", color: "#aa3bff", padding: "2px 6px", borderRadius: "4px", fontSize: "10px", fontWeight: 600 }}>👆 Touch</span>}
                      {caps.vibration && <span style={{ background: "rgba(0, 255, 153, 0.15)", color: "#00ff99", padding: "2px 6px", borderRadius: "4px", fontSize: "10px", fontWeight: 600 }}>📳 Haptic</span>}
                    </div>
                  </div>

                  {/* Actions Bar */}
                  <div style={{ marginTop: "14px", paddingTop: "10px", borderTop: "1px solid rgba(255,255,255,0.06)", display: "flex", justifyContent: "space-between", alignItems: "center" }}>
                    <button
                      onClick={() => handlePingDevice(dev.device_id)}
                      disabled={!isOnline}
                      style={{
                        background: "rgba(0, 212, 255, 0.15)",
                        border: "1px solid rgba(0, 212, 255, 0.4)",
                        color: "#00d4ff",
                        borderRadius: "6px",
                        padding: "4px 10px",
                        fontSize: "11px",
                        fontWeight: 700,
                        cursor: isOnline ? "pointer" : "not-allowed",
                        opacity: isOnline ? 1 : 0.5
                      }}
                    >
                      <FaBolt /> {pingStatus[dev.device_id] || t("devices_inventory.ping")}
                    </button>

                    {!dev.is_primary_host && (
                      <button
                        onClick={() => handleRevokeDevice(dev.device_id, dev.device_name)}
                        style={{
                          background: "none",
                          border: "none",
                          color: "#ff3b5c",
                          cursor: "pointer",
                          fontSize: "12px",
                          display: "flex",
                          alignItems: "center",
                          gap: "4px"
                        }}
                      >
                        <FaTrash size={11} /> {t("devices_inventory.revoke")}
                      </button>
                    )}
                  </div>
                </div>
              );
            })}
          </div>
        )}
      </div>

      {/* Task Manager Real Process Table */}
      <div style={{ background: "#111827", borderRadius: "16px", border: "1px solid rgba(255,255,255,0.08)", padding: "20px" }}>
        <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center", marginBottom: "16px", flexWrap: "wrap", gap: "10px" }}>
          <h3 style={{ color: "#fff", margin: 0, fontSize: "16px", display: "flex", alignItems: "center", gap: "8px" }}>
            <FaTasks color="#00ff99" /> {t("host.task_manager")} ({processes.length})
          </h3>

          <div style={{ display: "flex", alignItems: "center", gap: "8px", background: "#192033", padding: "4px 12px", borderRadius: "8px" }}>
            <span style={{ fontSize: "12px", color: "#8b9bb4" }}>Sort by:</span>
            <select
              value={procSort}
              onChange={(e) => setProcSort(e.target.value)}
              style={{ background: "transparent", color: "#00d4ff", border: "none", outline: "none", cursor: "pointer", fontSize: "12px", fontWeight: 700 }}
            >
              <option value="cpu">CPU Usage %</option>
              <option value="memory">RAM Usage %</option>
              <option value="name">Process Name</option>
              <option value="pid">PID</option>
            </select>
          </div>
        </div>

        {processes.length === 0 ? (
          <p style={{ color: "#8b9bb4", fontSize: "13px" }}>No active process information exposed by OS permissions.</p>
        ) : (
          <div style={{ overflowX: "auto" }}>
            <table style={{ width: "100%", borderCollapse: "collapse", fontSize: "13px", color: "#fff", textAlign: "left" }}>
              <thead>
                <tr style={{ borderBottom: "1px solid rgba(255,255,255,0.1)", color: "#8b9bb4" }}>
                  <th style={{ padding: "10px 12px" }}>{t("host.proc_name")}</th>
                  <th style={{ padding: "10px 12px" }}>{t("host.proc_pid")}</th>
                  <th style={{ padding: "10px 12px" }}>{t("host.proc_cpu")}</th>
                  <th style={{ padding: "10px 12px" }}>{t("host.proc_ram")}</th>
                  <th style={{ padding: "10px 12px" }}>Memory (MB)</th>
                  <th style={{ padding: "10px 12px" }}>{t("host.proc_user")}</th>
                  <th style={{ padding: "10px 12px" }}>{t("host.proc_status")}</th>
                </tr>
              </thead>
              <tbody>
                {processes.map((proc) => (
                  <tr key={proc.pid} style={{ borderBottom: "1px solid rgba(255,255,255,0.04)" }}>
                    <td style={{ padding: "10px 12px", fontWeight: 600 }}>{proc.name}</td>
                    <td style={{ padding: "10px 12px", fontFamily: "monospace", color: "#8b9bb4" }}>{proc.pid}</td>
                    <td style={{ padding: "10px 12px", color: proc.cpu_percent > 10 ? "#ff3b5c" : "#00ff99", fontWeight: 700 }}>
                      {proc.cpu_percent}%
                    </td>
                    <td style={{ padding: "10px 12px", color: "#00d4ff" }}>{proc.memory_percent}%</td>
                    <td style={{ padding: "10px 12px", color: "#8b9bb4" }}>{proc.memory_mb} MB</td>
                    <td style={{ padding: "10px 12px", color: "#8b9bb4" }}>{proc.username}</td>
                    <td style={{ padding: "10px 12px" }}>
                      <span style={{ background: "rgba(0, 255, 153, 0.1)", color: "#00ff99", padding: "2px 6px", borderRadius: "4px", fontSize: "11px" }}>
                        {proc.status}
                      </span>
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        )}
      </div>

      {/* ========================================================= */}
      {/* 📱 Ephemeral Pairing QR Code Modal                         */}
      {/* ========================================================= */}
      {showPairModal && pairingData && (
        <div style={{ position: "fixed", top: 0, left: 0, width: "100vw", height: "100vh", background: "rgba(0,0,0,0.85)", backdropFilter: "blur(8px)", display: "flex", alignItems: "center", justifyContent: "center", zIndex: 1000, padding: "20px" }}>
          <div style={{ background: "#111827", border: "1px solid rgba(0,212,255,0.4)", borderRadius: "20px", padding: "26px", maxWidth: "520px", width: "100%", textAlign: "center", position: "relative" }}>
            <h3 style={{ color: "#00d4ff", margin: "0 0 8px 0", fontSize: "18px", display: "flex", alignItems: "center", justifyContent: "center", gap: "8px" }}>
              <FaQrcode /> {t("devices_inventory.pair_device")}
            </h3>
            <p style={{ color: "#8b9bb4", fontSize: "13px", marginBottom: "20px" }}>
              {t("devices_inventory.scan_qr")}
            </p>

            <div style={{ background: "#ffffff", padding: "14px", borderRadius: "14px", display: "inline-block", marginBottom: "16px" }}>
              <img
                src={`https://api.qrserver.com/v1/create-qr-code/?size=180x180&data=${encodeURIComponent(pairingData.pairing_url)}`}
                alt="Universal Pairing QR Code"
                style={{ width: "180px", height: "180px", display: "block" }}
              />
              <span style={{ color: "#050816", fontSize: "10px", fontWeight: 800, marginTop: "6px", display: "block" }}>
                IPHONE / ANDROID / GLASSES
              </span>
            </div>

            <div style={{ background: "#192033", padding: "10px 14px", borderRadius: "8px", fontSize: "12px", color: "#00ff99", fontFamily: "monospace", marginBottom: "18px" }}>
              TTL: {pairingData.expires_in_seconds}s | Token: {pairingData.pairing_token.substring(0, 16)}...
            </div>

            <button
              onClick={() => setShowPairModal(false)}
              style={{
                background: "linear-gradient(135deg, #00d4ff 0%, #0077ff 100%)",
                color: "#050816",
                border: "none",
                borderRadius: "10px",
                padding: "10px 24px",
                fontWeight: 700,
                cursor: "pointer"
              }}
            >
              Done / Close
            </button>
          </div>
        </div>
      )}
    </MainLayout>
  );
}