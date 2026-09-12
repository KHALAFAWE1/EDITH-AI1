import { useEffect, useState } from "react";
import MainLayout from "../layouts/MainLayout";
import StatusCard from "../components/StatusCard";
import { api } from "../services/api";
import { FaDesktop, FaMicrochip, FaMemory, FaHdd, FaNetworkWired, FaServer, FaSync, FaClock, FaCheckCircle, FaTrash } from "react-icons/fa";

export default function Devices() {
  const [telemetry, setTelemetry] = useState(null);
  const [devicesList, setDevicesList] = useState([]);
  const [loading, setLoading] = useState(true);
  const [syncing, setSyncing] = useState(false);

  const fetchTelemetry = async () => {
    try {
      const res = await api.get("/devices/telemetry");
      setTelemetry(res.data);
    } catch (err) {
      console.warn("Failed to fetch telemetry:", err.message);
    }
  };

  const fetchDevices = async () => {
    try {
      const res = await api.get("/devices");
      setDevicesList(res.data);
    } catch (err) {
      console.warn("Failed to fetch devices list:", err.message);
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    fetchTelemetry();
    fetchDevices();
    const interval = setInterval(fetchTelemetry, 3000);
    return () => clearInterval(interval);
  }, []);

  const handleSyncHost = async () => {
    try {
      setSyncing(true);
      await api.post("/devices/register-host");
      await fetchDevices();
    } catch (err) {
      console.error("Failed to sync host:", err);
    } finally {
      setSyncing(false);
    }
  };

  const handleDeleteDevice = async (id) => {
    if (!window.confirm("هل تريد حذف هذا الجهاز من قائمة المراقبة؟")) return;
    try {
      await api.delete(`/devices/${id}`);
      fetchDevices();
    } catch (err) {
      console.error("Failed to delete device:", err);
    }
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
      <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center", marginBottom: "22px" }}>
        <div>
          <h1 className="title" style={{ display: "flex", alignItems: "center", gap: "10px" }}>
            <FaDesktop style={{ color: "#00d4ff" }} /> System Telemetry & Device Monitoring
          </h1>
          <p className="subtitle">Real-time hardware resource telemetry, host health, and connected infrastructure</p>
        </div>

        <button
          onClick={handleSyncHost}
          disabled={syncing}
          style={{
            background: "linear-gradient(135deg, #00d4ff 0%, #0077ff 100%)",
            color: "#050816",
            border: "none",
            borderRadius: "10px",
            padding: "12px 20px",
            fontWeight: 700,
            fontSize: "14px",
            display: "flex",
            alignItems: "center",
            gap: "8px",
            cursor: syncing ? "not-allowed" : "pointer",
            boxShadow: "0 4px 15px rgba(0, 212, 255, 0.4)"
          }}
        >
          <FaSync className={syncing ? "spin" : ""} size={14} /> Sync Host Telemetry
        </button>
      </div>

      {/* Real-time Hardware Telemetry Bar */}
      <div
        style={{
          display: "grid",
          gridTemplateColumns: "repeat(auto-fit, minmax(220px, 1fr))",
          gap: "18px",
          marginBottom: "25px"
        }}
      >
        <StatusCard
          icon={<FaMicrochip />}
          title="CPU Utilization"
          value={`${cpuPercent}%`}
          subtitle={`${telemetry?.cpu?.cores || "--"} Logical Cores`}
          accentColor={getProgressColor(cpuPercent)}
        />
        <StatusCard
          icon={<FaMemory />}
          title="Memory (RAM)"
          value={`${ramPercent}%`}
          subtitle={`${telemetry?.ram?.used_gb || 0} / ${telemetry?.ram?.total_gb || 0} GB`}
          accentColor={getProgressColor(ramPercent)}
        />
        <StatusCard
          icon={<FaHdd />}
          title="Primary Storage"
          value={`${storagePercent}%`}
          subtitle={`${telemetry?.storage?.used_gb || 0} / ${telemetry?.storage?.total_gb || 0} GB`}
          accentColor={getProgressColor(storagePercent)}
        />
        <StatusCard
          icon={<FaClock />}
          title="System Uptime"
          value={telemetry?.uptime || "--"}
          subtitle={`Node: ${telemetry?.hostname || "Localhost"}`}
          accentColor="#00ff99"
        />
      </div>

      {/* Main Hardware Resource Panels */}
      <div style={{ display: "grid", gridTemplateColumns: "repeat(auto-fit, minmax(320px, 1fr))", gap: "20px", marginBottom: "25px" }}>
        {/* Host Node Specs */}
        <div
          style={{
            background: "#111827",
            borderRadius: "16px",
            border: "1px solid rgba(0, 212, 255, 0.15)",
            padding: "24px",
            boxShadow: "0 10px 30px rgba(0,0,0,0.4)"
          }}
        >
          <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center", marginBottom: "18px" }}>
            <h2 style={{ fontSize: "18px", color: "#fff", margin: 0, display: "flex", alignItems: "center", gap: "8px" }}>
              <FaServer color="#00d4ff" /> Host Machine Specifications
            </h2>
            <span className="badge badge-green" style={{ display: "flex", alignItems: "center", gap: "6px" }}>

              <FaCheckCircle /> ONLINE
            </span>
          </div>

          <div style={{ display: "grid", gridTemplateColumns: "1fr 1fr", gap: "14px", fontSize: "13px" }}>
            <div style={{ background: "#192033", padding: "12px", borderRadius: "10px" }}>
              <span style={{ color: "#8b9bb4" }}>Hostname</span>
              <p style={{ color: "#fff", fontWeight: 600, marginTop: "4px", fontSize: "14px" }}>
                {telemetry?.hostname || "--"}
              </p>
            </div>

            <div style={{ background: "#192033", padding: "12px", borderRadius: "10px" }}>
              <span style={{ color: "#8b9bb4" }}>IP Address</span>
              <p style={{ color: "#00d4ff", fontWeight: 600, marginTop: "4px", fontSize: "14px", fontFamily: "monospace" }}>
                {telemetry?.ip_address || "--"}
              </p>
            </div>

            <div style={{ background: "#192033", padding: "12px", borderRadius: "10px" }}>
              <span style={{ color: "#8b9bb4" }}>Operating System</span>
              <p style={{ color: "#fff", fontWeight: 600, marginTop: "4px", fontSize: "14px" }}>
                {telemetry?.os || "--"}
              </p>
            </div>

            <div style={{ background: "#192033", padding: "12px", borderRadius: "10px" }}>
              <span style={{ color: "#8b9bb4" }}>Architecture</span>
              <p style={{ color: "#fff", fontWeight: 600, marginTop: "4px", fontSize: "14px" }}>
                {telemetry?.machine || "--"}
              </p>
            </div>

            <div style={{ background: "#192033", padding: "12px", borderRadius: "10px", gridColumn: "1 / -1" }}>
              <span style={{ color: "#8b9bb4" }}>Processor Model</span>
              <p style={{ color: "#fff", fontWeight: 600, marginTop: "4px", fontSize: "13px" }}>
                {telemetry?.processor || "Intel / AMD Processor"}
              </p>
            </div>
          </div>
        </div>

        {/* Live Gauges Progress Bars */}
        <div
          style={{
            background: "#111827",
            borderRadius: "16px",
            border: "1px solid rgba(0, 212, 255, 0.15)",
            padding: "24px",
            boxShadow: "0 10px 30px rgba(0,0,0,0.4)",
            display: "flex",
            flexDirection: "column",
            justifyContent: "space-around",
            gap: "18px"
          }}
        >
          {/* CPU Bar */}
          <div>
            <div style={{ display: "flex", justifyContent: "space-between", marginBottom: "6px", fontSize: "13px" }}>
              <span style={{ color: "#fff", fontWeight: 600, display: "flex", alignItems: "center", gap: "6px" }}>
                <FaMicrochip color="#00d4ff" /> CPU Load
              </span>
              <span style={{ color: getProgressColor(cpuPercent), fontWeight: 700, fontFamily: "monospace" }}>
                {cpuPercent}%
              </span>
            </div>
            <div style={{ width: "100%", height: "10px", background: "#192033", borderRadius: "5px", overflow: "hidden" }}>
              <div
                style={{
                  width: `${cpuPercent}%`,
                  height: "100%",
                  background: `linear-gradient(90deg, #00d4ff, ${getProgressColor(cpuPercent)})`,
                  borderRadius: "5px",
                  transition: "width 0.4s ease"
                }}
              />
            </div>
          </div>

          {/* RAM Bar */}
          <div>
            <div style={{ display: "flex", justifyContent: "space-between", marginBottom: "6px", fontSize: "13px" }}>
              <span style={{ color: "#fff", fontWeight: 600, display: "flex", alignItems: "center", gap: "6px" }}>
                <FaMemory color="#aa3bff" /> RAM Usage ({telemetry?.ram?.used_gb || 0} GB)
              </span>
              <span style={{ color: getProgressColor(ramPercent), fontWeight: 700, fontFamily: "monospace" }}>
                {ramPercent}%
              </span>
            </div>
            <div style={{ width: "100%", height: "10px", background: "#192033", borderRadius: "5px", overflow: "hidden" }}>
              <div
                style={{
                  width: `${ramPercent}%`,
                  height: "100%",
                  background: `linear-gradient(90deg, #aa3bff, ${getProgressColor(ramPercent)})`,
                  borderRadius: "5px",
                  transition: "width 0.4s ease"
                }}
              />
            </div>
          </div>

          {/* Storage Bar */}
          <div>
            <div style={{ display: "flex", justifyContent: "space-between", marginBottom: "6px", fontSize: "13px" }}>
              <span style={{ color: "#fff", fontWeight: 600, display: "flex", alignItems: "center", gap: "6px" }}>
                <FaHdd color="#00ff99" /> Disk Storage ({telemetry?.storage?.used_gb || 0} GB)
              </span>
              <span style={{ color: getProgressColor(storagePercent), fontWeight: 700, fontFamily: "monospace" }}>
                {storagePercent}%
              </span>
            </div>
            <div style={{ width: "100%", height: "10px", background: "#192033", borderRadius: "5px", overflow: "hidden" }}>
              <div
                style={{
                  width: `${storagePercent}%`,
                  height: "100%",
                  background: `linear-gradient(90deg, #00ff99, ${getProgressColor(storagePercent)})`,
                  borderRadius: "5px",
                  transition: "width 0.4s ease"
                }}
              />
            </div>
          </div>
        </div>
      </div>

      {/* Monitored Devices List */}
      <div
        style={{
          background: "#111827",
          borderRadius: "16px",
          border: "1px solid rgba(255,255,255,0.08)",
          padding: "22px",
          boxShadow: "0 10px 30px rgba(0,0,0,0.4)"
        }}
      >
        <h2 style={{ fontSize: "18px", color: "#fff", marginBottom: "16px", display: "flex", alignItems: "center", gap: "8px" }}>
          <FaNetworkWired color="#00d4ff" /> Registered Infrastructure Nodes ({devicesList.length})
        </h2>

        {devicesList.length === 0 ? (
          <p style={{ color: "#8b9bb4", fontSize: "13px" }}>
            No registered devices found. Click "Sync Host Telemetry" to add this machine.
          </p>
        ) : (
          <div style={{ display: "flex", flexDirection: "column", gap: "10px" }}>
            {devicesList.map((dev) => (
              <div
                key={dev.id}
                style={{
                  display: "flex",
                  justifyContent: "space-between",
                  alignItems: "center",
                  background: "#192033",
                  padding: "14px 18px",
                  borderRadius: "12px",
                  border: "1px solid rgba(0, 212, 255, 0.1)"
                }}
              >
                <div style={{ display: "flex", alignItems: "center", gap: "14px" }}>
                  <FaDesktop size={20} color="#00d4ff" />
                  <div>
                    <h4 style={{ color: "#fff", margin: 0, fontSize: "15px" }}>{dev.hostname}</h4>
                    <span style={{ color: "#8b9bb4", fontSize: "12px" }}>
                      {dev.operating_system} | IP: {dev.ip_address}
                    </span>
                  </div>
                </div>

                <div style={{ display: "flex", alignItems: "center", gap: "20px" }}>
                  <div style={{ textAlign: "right", fontSize: "12px", color: "#8b9bb4" }}>
                    <div>CPU: <strong style={{ color: "#fff" }}>{dev.cpu}</strong></div>
                    <div>RAM: <strong style={{ color: "#fff" }}>{dev.ram}</strong></div>
                  </div>

                  <span className="badge badge-green">{dev.status || "Online"}</span>

                  <button
                    onClick={() => handleDeleteDevice(dev.id)}
                    style={{ background: "none", border: "none", color: "#ff3b5c", cursor: "pointer", padding: "6px" }}
                  >
                    <FaTrash size={12} />
                  </button>
                </div>
              </div>
            ))}
          </div>
        )}
      </div>
    </MainLayout>
  );
}