import { useEffect, useState } from "react";
import MainLayout from "../layouts/MainLayout";
import { api } from "../services/api";
import {
  FaShieldAlt,
  FaExclamationTriangle,
  FaLock,
  FaUserShield,
  FaSync,
  FaCheckCircle,
  FaTimesCircle,
  FaEye
} from "react-icons/fa";

export default function Security() {
  const [summary, setSummary] = useState({ status: "SHIELD_ACTIVE", threat_level: "NORMAL", security_score: 100, total_audit_events: 0, critical_alerts_count: 0, recent_alerts: [] });
  const [logs, setLogs] = useState([]);
  const [riskAssessment, setRiskAssessment] = useState(null);
  const [loading, setLoading] = useState(true);

  const fetchSecurityData = async () => {
    try {
      setLoading(true);
      const sumRes = await api.get("/security/summary");
      if (sumRes.data) setSummary(sumRes.data);

      const logsRes = await api.get("/security/audit-logs?limit=40");
      if (Array.isArray(logsRes.data)) setLogs(logsRes.data);

      const riskRes = await api.get("/risk/current");
      if (riskRes.data) setRiskAssessment(riskRes.data);
    } catch (err) {
      console.warn("Failed to fetch security data:", err);
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    fetchSecurityData();
    const interval = setInterval(fetchSecurityData, 8000);
    return () => clearInterval(interval);
  }, []);

  return (
    <MainLayout>
      {/* Header */}
      <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center", marginBottom: "22px", flexWrap: "wrap", gap: "10px" }}>
        <div>
          <h1 className="title" style={{ display: "flex", alignItems: "center", gap: "10px" }}>
            <FaShieldAlt style={{ color: "#00d4ff" }} /> SOC Security Operations Center
          </h1>
          <p className="subtitle">Real-time threat monitoring, audit trails, and Explainable AI risk assessment</p>
        </div>

        <button
          onClick={fetchSecurityData}
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
          <FaSync className={loading ? "spin" : ""} /> Refresh SOC Grid
        </button>
      </div>

      {/* Top Metrics Bar */}
      <div style={{ display: "grid", gridTemplateColumns: "repeat(auto-fit, minmax(220px, 1fr))", gap: "16px", marginBottom: "25px" }}>
        <div style={{ background: "#111827", border: "1px solid rgba(0, 255, 153, 0.3)", padding: "18px", borderRadius: "14px" }}>
          <span style={{ fontSize: "12px", color: "#8b9bb4" }}>Defense Grid Status</span>
          <div style={{ color: "#00ff99", fontWeight: 700, fontSize: "18px", marginTop: "4px", display: "flex", alignItems: "center", gap: "6px" }}>
            <FaCheckCircle /> {summary.status}
          </div>
        </div>

        <div style={{ background: "#111827", border: `1px solid ${summary.threat_level === "NORMAL" ? "rgba(0, 212, 255, 0.3)" : "#ff3b5c"}`, padding: "18px", borderRadius: "14px" }}>
          <span style={{ fontSize: "12px", color: "#8b9bb4" }}>Perimeter Threat Level</span>
          <div style={{ color: summary.threat_level === "NORMAL" ? "#00d4ff" : "#ff3b5c", fontWeight: 700, fontSize: "18px", marginTop: "4px" }}>
            {summary.threat_level}
          </div>
        </div>

        <div style={{ background: "#111827", border: "1px solid rgba(170, 59, 255, 0.3)", padding: "18px", borderRadius: "14px" }}>
          <span style={{ fontSize: "12px", color: "#8b9bb4" }}>Security Integrity Score</span>
          <div style={{ color: "#aa3bff", fontWeight: 700, fontSize: "18px", marginTop: "4px" }}>
            {summary.security_score} / 100
          </div>
        </div>

        <div style={{ background: "#111827", border: "1px solid rgba(255, 255, 255, 0.1)", padding: "18px", borderRadius: "14px" }}>
          <span style={{ fontSize: "12px", color: "#8b9bb4" }}>Total Audit Events</span>
          <div style={{ color: "#fff", fontWeight: 700, fontSize: "18px", marginTop: "4px" }}>
            {summary.total_audit_events}
          </div>
        </div>
      </div>

      {/* Explainable AI Decision Card */}
      {riskAssessment && (
        <div style={{ background: "#111827", borderRadius: "16px", border: "1px solid rgba(0, 212, 255, 0.3)", padding: "22px", marginBottom: "25px" }}>
          <h3 style={{ color: "#00d4ff", margin: "0 0 14px 0", display: "flex", alignItems: "center", gap: "8px", fontSize: "16px" }}>
            <FaEye /> Explainable AI Decision Breakdown
          </h3>

          <div style={{ background: "#192033", borderRadius: "12px", padding: "16px", border: "1px solid rgba(255,255,255,0.06)" }}>
            <div style={{ marginBottom: "12px" }}>
              <span style={{ fontSize: "11px", color: "#8b9bb4", textTransform: "uppercase", letterSpacing: "1px" }}>WHAT EDITH OBSERVED</span>
              <p style={{ color: "#fff", fontWeight: 600, fontSize: "14px", margin: "4px 0 0 0" }}>
                {riskAssessment.explainable_ai?.what}
              </p>
            </div>

            <div style={{ marginBottom: "12px" }}>
              <span style={{ fontSize: "11px", color: "#8b9bb4", textTransform: "uppercase", letterSpacing: "1px" }}>WHY (REASONING)</span>
              <ul style={{ color: "#00d4ff", margin: "4px 0 0 0", paddingLeft: "20px", fontSize: "13px" }}>
                {riskAssessment.explainable_ai?.why?.map((r, i) => (
                  <li key={i} style={{ marginBottom: "2px" }}>{r}</li>
                ))}
              </ul>
            </div>

            <div>
              <span style={{ fontSize: "11px", color: "#8b9bb4", textTransform: "uppercase", letterSpacing: "1px" }}>RECOMMENDED ACTION</span>
              <p style={{ color: "#00ff99", fontWeight: 600, fontSize: "13px", margin: "4px 0 0 0" }}>
                ⚡ {riskAssessment.explainable_ai?.recommended_action}
              </p>
            </div>
          </div>
        </div>
      )}

      {/* Audit Log Stream */}
      <div style={{ background: "#111827", borderRadius: "16px", border: "1px solid rgba(255, 255, 255, 0.08)", padding: "22px" }}>
        <h3 style={{ color: "#fff", margin: "0 0 16px 0", display: "flex", alignItems: "center", gap: "8px", fontSize: "16px" }}>
          <FaUserShield color="#00d4ff" /> Security Audit Log Stream ({logs.length})
        </h3>

        {logs.length === 0 ? (
          <p style={{ color: "#8b9bb4", fontSize: "13px" }}>No audit events recorded yet.</p>
        ) : (
          <div style={{ display: "flex", flexDirection: "column", gap: "8px" }}>
            {logs.map((log) => (
              <div
                key={log.id}
                style={{
                  background: "#192033",
                  borderRadius: "10px",
                  padding: "12px 16px",
                  display: "flex",
                  justifyContent: "space-between",
                  alignItems: "center",
                  flexWrap: "wrap",
                  gap: "10px",
                  border: `1px solid ${log.severity === "CRITICAL" ? "#ff3b5c" : "rgba(255,255,255,0.06)"}`
                }}
              >
                <div>
                  <div style={{ display: "flex", alignItems: "center", gap: "8px" }}>
                    <span style={{ color: "#00d4ff", fontWeight: 700, fontSize: "12px" }}>[{log.event_type}]</span>
                    <span style={{ color: "#fff", fontSize: "13px" }}>{log.description}</span>
                  </div>
                  <span style={{ color: "#8b9bb4", fontSize: "11px" }}>
                    Actor: {log.actor || "SYSTEM"} | Target: {log.target || "PERIMETER"}
                  </span>
                </div>

                <div style={{ display: "flex", alignItems: "center", gap: "10px" }}>
                  <span style={{
                    background: log.severity === "CRITICAL" ? "rgba(255, 59, 92, 0.2)" : "rgba(0, 255, 153, 0.15)",
                    color: log.severity === "CRITICAL" ? "#ff3b5c" : "#00ff99",
                    padding: "2px 8px",
                    borderRadius: "4px",
                    fontSize: "10px",
                    fontWeight: 700
                  }}>
                    {log.severity}
                  </span>
                  <span style={{ color: "#606f8b", fontSize: "11px", fontFamily: "monospace" }}>
                    {new Date(log.created_at).toLocaleTimeString()}
                  </span>
                </div>
              </div>
            ))}
          </div>
        )}
      </div>
    </MainLayout>
  );
}