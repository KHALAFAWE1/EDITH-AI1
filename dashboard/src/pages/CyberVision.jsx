import { useEffect, useState } from "react";
import MainLayout from "../layouts/MainLayout";
import { api } from "../services/api";
import {
  FaNetworkWired,
  FaShieldAlt,
  FaSync,
  FaDesktop,
  FaLink,
  FaExclamationTriangle,
  FaCheckCircle,
  FaServer,
  FaWifi
} from "react-icons/fa";

export default function CyberVision() {
  const [nodes, setNodes] = useState([]);
  const [correlations, setCorrelations] = useState([]);
  const [loading, setLoading] = useState(true);
  const [scanning, setScanning] = useState(false);

  const fetchCyberData = async () => {
    try {
      setLoading(true);
      const res = await api.get("/cyber/nodes");
      if (Array.isArray(res.data)) {
        setNodes(res.data);
      }
      const corrRes = await api.get("/cyber/correlate");
      if (corrRes.data && corrRes.data.correlated_events) {
        setCorrelations(corrRes.data.correlated_events);
      }
    } catch (err) {
      console.warn("Failed to fetch cyber nodes:", err);
    } finally {
      setLoading(false);
    }
  };

  const handleScan = async () => {
    try {
      setScanning(true);
      await api.post("/cyber/scan");
      await fetchCyberData();
    } catch (err) {
      console.warn("Scan failed:", err);
    } finally {
      setScanning(false);
    }
  };

  useEffect(() => {
    fetchCyberData();
    const interval = setInterval(fetchCyberData, 10000);
    return () => clearInterval(interval);
  }, []);

  return (
    <MainLayout>
      {/* Header */}
      <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center", marginBottom: "22px", flexWrap: "wrap", gap: "10px" }}>
        <div>
          <h1 className="title" style={{ display: "flex", alignItems: "center", gap: "10px" }}>
            <FaNetworkWired style={{ color: "#00d4ff" }} /> CyberVision & Defensive Telemetry
          </h1>
          <p className="subtitle">Passive network node discovery, unauthorized device detection & physical-cyber correlation</p>
        </div>

        <button
          onClick={handleScan}
          disabled={scanning}
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
            cursor: scanning ? "not-allowed" : "pointer"
          }}
        >
          <FaSync className={scanning ? "spin" : ""} /> Scan Local Perimeter
        </button>
      </div>

      {/* Correlation Hub */}
      {correlations.length > 0 && (
        <div style={{ background: "#111827", border: "1px solid rgba(170, 59, 255, 0.4)", borderRadius: "16px", padding: "20px", marginBottom: "25px" }}>
          <h3 style={{ color: "#aa3bff", margin: "0 0 12px 0", display: "flex", alignItems: "center", gap: "8px", fontSize: "16px" }}>
            <FaLink /> Physical + Cyber Event Correlation
          </h3>
          <div style={{ display: "grid", gridTemplateColumns: "repeat(auto-fit, minmax(280px, 1fr))", gap: "12px" }}>
            {correlations.map((c, idx) => (
              <div key={idx} style={{ background: "#192033", borderRadius: "10px", padding: "14px", border: "1px solid rgba(255,255,255,0.06)" }}>
                <div style={{ display: "flex", justifyContent: "space-between", marginBottom: "6px" }}>
                  <span style={{ fontSize: "11px", color: "#aa3bff", fontWeight: 700 }}>{c.correlation_id}</span>
                  <span style={{ fontSize: "11px", color: "#00ff99" }}>Confidence: {(c.confidence * 100).toFixed(0)}%</span>
                </div>
                <p style={{ color: "#fff", fontSize: "13px", margin: "4px 0", fontWeight: 600 }}>👁️ {c.physical_trigger}</p>
                <p style={{ color: "#00d4ff", fontSize: "12px", margin: "4px 0", fontFamily: "monospace" }}>🌐 {c.cyber_trigger}</p>
                <p style={{ color: "#8b9bb4", fontSize: "11px", margin: "6px 0 0 0" }}>{c.explanation}</p>
              </div>
            ))}
          </div>
        </div>
      )}

      {/* Discovered Nodes Grid */}
      <div style={{ background: "#111827", borderRadius: "16px", border: "1px solid rgba(0, 212, 255, 0.15)", padding: "22px" }}>
        <h3 style={{ color: "#fff", margin: "0 0 16px 0", display: "flex", alignItems: "center", gap: "8px", fontSize: "16px" }}>
          <FaServer color="#00d4ff" /> Monitored Perimeter Nodes ({nodes.length})
        </h3>

        {nodes.length === 0 ? (
          <p style={{ color: "#8b9bb4", fontSize: "13px" }}>No network nodes detected. Click "Scan Local Perimeter" to run discovery.</p>
        ) : (
          <div style={{ display: "grid", gridTemplateColumns: "repeat(auto-fit, minmax(300px, 1fr))", gap: "14px" }}>
            {nodes.map((node) => (
              <div
                key={node.id}
                style={{
                  background: "#192033",
                  borderRadius: "12px",
                  padding: "16px",
                  border: `1px solid ${node.is_authorized ? "rgba(0, 212, 255, 0.15)" : "rgba(255, 59, 92, 0.4)"}`,
                  display: "flex",
                  flexDirection: "column",
                  justifyContent: "space-between"
                }}
              >
                <div>
                  <div style={{ display: "flex", justifyContent: "space-between", alignItems: "flex-start", marginBottom: "10px" }}>
                    <div style={{ display: "flex", alignItems: "center", gap: "10px" }}>
                      <FaDesktop color="#00d4ff" size={18} />
                      <div>
                        <h4 style={{ color: "#fff", margin: 0, fontSize: "14px" }}>{node.hostname}</h4>
                        <span style={{ color: "#8b9bb4", fontSize: "11px" }}>{node.device_type}</span>
                      </div>
                    </div>
                    <span style={{
                      background: node.is_authorized ? "rgba(0, 255, 153, 0.15)" : "rgba(255, 59, 92, 0.2)",
                      color: node.is_authorized ? "#00ff99" : "#ff3b5c",
                      border: `1px solid ${node.is_authorized ? "#00ff99" : "#ff3b5c"}`,
                      padding: "2px 8px",
                      borderRadius: "6px",
                      fontSize: "10px",
                      fontWeight: 700
                    }}>
                      {node.is_authorized ? "AUTHORIZED" : "SUSPECT NODE"}
                    </span>
                  </div>

                  <div style={{ fontSize: "12px", color: "#8b9bb4", display: "flex", flexDirection: "column", gap: "4px", marginTop: "8px" }}>
                    <div>IP: <strong style={{ color: "#00d4ff", fontFamily: "monospace" }}>{node.ip_address}</strong></div>
                    <div>MAC: <span style={{ fontFamily: "monospace" }}>{node.mac_address}</span></div>
                    <div>Vendor / Adapter: <span>{node.vendor}</span></div>
                  </div>
                </div>

                <div style={{ marginTop: "12px", paddingTop: "8px", borderTop: "1px solid rgba(255,255,255,0.06)", display: "flex", justifyContent: "space-between", fontSize: "11px", color: "#606f8b" }}>
                  <span>Status: <strong style={{ color: "#00ff99" }}>{node.status}</strong></span>
                  <span>Risk: <strong style={{ color: node.risk_level === "LOW" ? "#00ff99" : "#ffaa00" }}>{node.risk_level}</strong></span>
                </div>
              </div>
            ))}
          </div>
        )}
      </div>
    </MainLayout>
  );
}
