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
  FaNetworkWired,
  FaCheckCircle
} from "react-icons/fa";

export default function Devices() {
  const { t } = useLanguage();
  const [telemetry, setTelemetry] = useState(null);
  const [processes, setProcesses] = useState([]);
  const [procSort, setProcSort] = useState("cpu");
  const [loading, setLoading] = useState(true);
  const [syncing, setSyncing] = useState(false);

  const fetchHostData = async () => {
    try {
      setLoading(true);
      const res = await api.get("/devices/telemetry");
      if (res.data && typeof res.data === "object" && !res.data.detail) {
        setTelemetry(res.data);
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

        <button
          onClick={handleSyncHost}
          disabled={syncing}
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
            cursor: syncing ? "not-allowed" : "pointer"
          }}
        >
          <FaSync className={syncing ? "spin" : ""} size={13} /> Sync Host State
        </button>
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

      {/* Host Machine Specifications Panel */}
      <div style={{ background: "#111827", borderRadius: "16px", border: "1px solid rgba(0, 212, 255, 0.15)", padding: "20px", marginBottom: "25px" }}>
        <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center", marginBottom: "16px" }}>
          <h3 style={{ color: "#fff", margin: 0, fontSize: "16px", display: "flex", alignItems: "center", gap: "8px" }}>
            <FaDesktop color="#00d4ff" /> Host Machine Architecture & Network
          </h3>
          <span className="badge badge-green" style={{ display: "flex", alignItems: "center", gap: "6px" }}>
            <FaCheckCircle /> {telemetry?.status || "Online"}
          </span>
        </div>

        <div style={{ display: "grid", gridTemplateColumns: "repeat(auto-fit, minmax(200px, 1fr))", gap: "12px", fontSize: "13px" }}>
          <div style={{ background: "#192033", padding: "12px", borderRadius: "10px" }}>
            <span style={{ color: "#8b9bb4" }}>Hostname</span>
            <p style={{ color: "#fff", fontWeight: 600, margin: "4px 0 0 0" }}>{telemetry?.hostname || "--"}</p>
          </div>
          <div style={{ background: "#192033", padding: "12px", borderRadius: "10px" }}>
            <span style={{ color: "#8b9bb4" }}>Primary IP</span>
            <p style={{ color: "#00d4ff", fontWeight: 600, margin: "4px 0 0 0", fontFamily: "monospace" }}>{telemetry?.ip_address || "--"}</p>
          </div>
          <div style={{ background: "#192033", padding: "12px", borderRadius: "10px" }}>
            <span style={{ color: "#8b9bb4" }}>Operating System</span>
            <p style={{ color: "#fff", fontWeight: 600, margin: "4px 0 0 0" }}>{telemetry?.os || "--"}</p>
          </div>
          <div style={{ background: "#192033", padding: "12px", borderRadius: "10px" }}>
            <span style={{ color: "#8b9bb4" }}>Architecture / Processor</span>
            <p style={{ color: "#fff", fontWeight: 600, margin: "4px 0 0 0", fontSize: "12px" }}>{telemetry?.processor || "--"}</p>
          </div>
        </div>
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
    </MainLayout>
  );
}