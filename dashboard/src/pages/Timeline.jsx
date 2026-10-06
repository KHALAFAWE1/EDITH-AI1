import { useEffect, useState } from "react";
import MainLayout from "../layouts/MainLayout";
import { api } from "../services/api";
import {
  FaHistory,
  FaExclamationTriangle,
  FaShieldAlt,
  FaSync,
  FaFilter,
  FaCamera,
  FaNetworkWired,
  FaRobot,
  FaClock
} from "react-icons/fa";

export default function Timeline() {
  const [events, setEvents] = useState([]);
  const [stats, setStats] = useState({ total_events: 0, anomalies_detected: 0, critical_incidents: 0, baseline_conformity_percent: 100 });
  const [loading, setLoading] = useState(true);
  const [severityFilter, setSeverityFilter] = useState("ALL");
  const [anomaliesOnly, setAnomaliesOnly] = useState(false);

  const fetchTimeline = async () => {
    try {
      setLoading(true);
      const res = await api.get(`/events?severity=${severityFilter}&anomalies_only=${anomaliesOnly}`);
      if (Array.isArray(res.data)) {
        setEvents(res.data);
      }
      const statsRes = await api.get("/events/stats");
      if (statsRes.data) {
        setStats(statsRes.data);
      }
    } catch (err) {
      console.warn("Failed to fetch timeline:", err);
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    fetchTimeline();
    const interval = setInterval(fetchTimeline, 5000);
    return () => clearInterval(interval);
  }, [severityFilter, anomaliesOnly]);

  const getSeverityBadge = (severity) => {
    switch ((severity || "").toUpperCase()) {
      case "CRITICAL":
        return { bg: "rgba(255, 59, 92, 0.2)", border: "#ff3b5c", color: "#ff3b5c", label: "CRITICAL" };
      case "HIGH":
        return { bg: "rgba(255, 170, 0, 0.2)", border: "#ffaa00", color: "#ffaa00", label: "HIGH RISK" };
      case "MEDIUM":
        return { bg: "rgba(0, 212, 255, 0.2)", border: "#00d4ff", color: "#00d4ff", label: "MEDIUM" };
      default:
        return { bg: "rgba(0, 255, 153, 0.15)", border: "#00ff99", color: "#00ff99", label: "ROUTINE" };
    }
  };

  const getSourceIcon = (source) => {
    switch ((source || "").toUpperCase()) {
      case "NETWORK_SCANNER":
        return <FaNetworkWired color="#aa3bff" />;
      case "VOICE_TRIGGER":
        return <FaRobot color="#ffaa00" />;
      default:
        return <FaCamera color="#00d4ff" />;
    }
  };

  return (
    <MainLayout>
      {/* Header */}
      <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center", marginBottom: "22px", flexWrap: "wrap", gap: "10px" }}>
        <div>
          <h1 className="title" style={{ display: "flex", alignItems: "center", gap: "10px" }}>
            <FaHistory style={{ color: "#00d4ff" }} /> Episodic Memory & Event Timeline
          </h1>
          <p className="subtitle">Real-time chronologically sequenced situational events, triggers, and environmental anomalies</p>
        </div>

        <button
          onClick={fetchTimeline}
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
          <FaSync className={loading ? "spin" : ""} /> Refresh Timeline
        </button>
      </div>

      {/* Stats Metric Row */}
      <div style={{ display: "grid", gridTemplateColumns: "repeat(auto-fit, minmax(200px, 1fr))", gap: "15px", marginBottom: "25px" }}>
        <div style={{ background: "#111827", border: "1px solid rgba(0, 212, 255, 0.2)", padding: "16px", borderRadius: "12px" }}>
          <span style={{ fontSize: "12px", color: "#8b9bb4" }}>Total Recorded Events</span>
          <h2 style={{ color: "#fff", margin: "6px 0 0 0", fontSize: "22px" }}>{stats.total_events}</h2>
        </div>
        <div style={{ background: "#111827", border: "1px solid rgba(255, 170, 0, 0.2)", padding: "16px", borderRadius: "12px" }}>
          <span style={{ fontSize: "12px", color: "#8b9bb4" }}>Anomalies Flagged</span>
          <h2 style={{ color: "#ffaa00", margin: "6px 0 0 0", fontSize: "22px" }}>{stats.anomalies_detected}</h2>
        </div>
        <div style={{ background: "#111827", border: "1px solid rgba(255, 59, 92, 0.2)", padding: "16px", borderRadius: "12px" }}>
          <span style={{ fontSize: "12px", color: "#8b9bb4" }}>Critical Incidents</span>
          <h2 style={{ color: "#ff3b5c", margin: "6px 0 0 0", fontSize: "22px" }}>{stats.critical_incidents}</h2>
        </div>
        <div style={{ background: "#111827", border: "1px solid rgba(0, 255, 153, 0.2)", padding: "16px", borderRadius: "12px" }}>
          <span style={{ fontSize: "12px", color: "#8b9bb4" }}>Baseline Conformity</span>
          <h2 style={{ color: "#00ff99", margin: "6px 0 0 0", fontSize: "22px" }}>{stats.baseline_conformity_percent}%</h2>
        </div>
      </div>

      {/* Filter Controls Bar */}
      <div style={{ display: "flex", gap: "12px", marginBottom: "20px", flexWrap: "wrap", alignItems: "center" }}>
        <div style={{ display: "flex", alignItems: "center", gap: "8px", background: "#111827", padding: "8px 14px", borderRadius: "8px", border: "1px solid rgba(255,255,255,0.08)" }}>
          <FaFilter color="#8b9bb4" size={12} />
          <select
            value={severityFilter}
            onChange={(e) => setSeverityFilter(e.target.value)}
            style={{ background: "transparent", color: "#fff", border: "none", outline: "none", cursor: "pointer", fontSize: "13px" }}
          >
            <option value="ALL">All Severities</option>
            <option value="CRITICAL">Critical Only</option>
            <option value="HIGH">High Risk</option>
            <option value="MEDIUM">Medium Risk</option>
            <option value="INFO">Routine / Info</option>
          </select>
        </div>

        <button
          onClick={() => setAnomaliesOnly(!anomaliesOnly)}
          style={{
            background: anomaliesOnly ? "rgba(255, 170, 0, 0.2)" : "#111827",
            border: anomaliesOnly ? "1px solid #ffaa00" : "1px solid rgba(255,255,255,0.08)",
            color: anomaliesOnly ? "#ffaa00" : "#8b9bb4",
            padding: "8px 16px",
            borderRadius: "8px",
            fontSize: "13px",
            fontWeight: 600,
            cursor: "pointer",
            display: "flex",
            alignItems: "center",
            gap: "6px"
          }}
        >
          <FaExclamationTriangle size={12} />
          {anomaliesOnly ? "Showing Anomalies Only ⚠️" : "Filter Anomalies Only"}
        </button>
      </div>

      {/* Timeline Stream Feed */}
      <div style={{ display: "flex", flexDirection: "column", gap: "12px" }}>
        {events.length === 0 ? (
          <div style={{ textAlign: "center", padding: "60px 20px", background: "#111827", borderRadius: "16px", border: "1px dashed rgba(255,255,255,0.1)", color: "#8b9bb4" }}>
            <FaClock size={36} color="#00d4ff" style={{ marginBottom: "10px" }} />
            <h3>No Timeline Events Found</h3>
            <p style={{ fontSize: "13px" }}>Events from live camera recognition, network discovery, and voice assistant are logged here automatically.</p>
          </div>
        ) : (
          events.map((ev) => {
            const badge = getSeverityBadge(ev.severity);
            return (
              <div
                key={ev.id}
                style={{
                  background: "#111827",
                  borderRadius: "12px",
                  border: `1px solid ${ev.is_anomaly ? "rgba(255, 170, 0, 0.4)" : "rgba(0, 212, 255, 0.15)"}`,
                  padding: "16px 20px",
                  display: "flex",
                  justifyContent: "space-between",
                  alignItems: "center",
                  flexWrap: "wrap",
                  gap: "12px",
                  position: "relative"
                }}
              >
                <div style={{ display: "flex", alignItems: "center", gap: "14px" }}>
                  <div style={{ width: "40px", height: "40px", borderRadius: "10px", background: "#192033", display: "flex", alignItems: "center", justifyContent: "center" }}>
                    {getSourceIcon(ev.source)}
                  </div>
                  <div>
                    <div style={{ display: "flex", alignItems: "center", gap: "8px", marginBottom: "4px" }}>
                      <h4 style={{ color: "#fff", margin: 0, fontSize: "14px" }}>{ev.summary}</h4>
                      {ev.is_anomaly && (
                        <span style={{ background: "rgba(255, 170, 0, 0.2)", color: "#ffaa00", fontSize: "10px", padding: "2px 6px", borderRadius: "4px", fontWeight: 700 }}>
                          ANOMALY
                        </span>
                      )}
                    </div>
                    <span style={{ color: "#8b9bb4", fontSize: "12px" }}>
                      Sector: {ev.location} | Source: {ev.source} | Confidence: {(ev.confidence * 100).toFixed(0)}%
                    </span>
                  </div>
                </div>

                <div style={{ display: "flex", alignItems: "center", gap: "14px" }}>
                  <span style={{ background: badge.bg, border: `1px solid ${badge.border}`, color: badge.color, padding: "4px 10px", borderRadius: "6px", fontSize: "11px", fontWeight: 700 }}>
                    {badge.label}
                  </span>
                  <span style={{ color: "#606f8b", fontSize: "12px", fontFamily: "monospace" }}>
                    {new Date(ev.timestamp).toLocaleTimeString()}
                  </span>
                </div>
              </div>
            );
          })
        )}
      </div>
    </MainLayout>
  );
}
