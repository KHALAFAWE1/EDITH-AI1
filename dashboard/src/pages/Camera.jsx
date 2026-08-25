import { useState } from "react";
import MainLayout from "../layouts/MainLayout";
import CameraView from "../components/CameraView";
import { FaUserCheck, FaUserSlash, FaShieldAlt, FaIdCard, FaBuilding, FaBriefcase, FaEnvelope, FaPhone } from "react-icons/fa";

export default function Camera() {
  const [latestRecognition, setLatestRecognition] = useState(null);
  const [detectionHistory, setDetectionHistory] = useState([]);

  const handleRecognized = (data) => {
    setLatestRecognition(data);

    if (data.found && data.person) {
      setDetectionHistory((prev) => {
        // تجنب التكرار المتتالي لنفس الشخص
        if (prev.length > 0 && prev[0].person?.id === data.person.id && Date.now() - prev[0].time < 5000) {
          return prev;
        }
        return [{ ...data, time: Date.now() }, ...prev.slice(0, 7)];
      });
    }
  };

  const person = latestRecognition?.person;
  const isFound = latestRecognition?.found && person;
  const score = latestRecognition?.score || 0;
  const confidence = latestRecognition?.confidence || "Low";

  return (
    <MainLayout>
      <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center", marginBottom: "20px" }}>
        <div>
          <h1 className="title" style={{ display: "flex", alignItems: "center", gap: "10px" }}>
            <FaShieldAlt style={{ color: "#00d4ff" }} /> EDITH Optical Target Recognition
          </h1>
          <p className="subtitle">Real-time biometric facial recognition and identity verification stream</p>
        </div>
        <div style={{ display: "flex", gap: "10px" }}>
          <span className={`badge ${isFound ? "badge-green" : "badge-cyan"}`}>
            {isFound ? "TARGET IDENTIFIED" : "SURVEILLANCE MODE"}
          </span>
        </div>
      </div>

      <div style={{ display: "grid", gridTemplateColumns: "1.6fr 1fr", gap: "25px", height: "calc(100vh - 180px)" }}>
        {/* Live Camera Feed */}
        <div
          style={{
            background: "#111827",
            borderRadius: "16px",
            border: "1px solid rgba(0, 212, 255, 0.2)",
            display: "flex",
            flexDirection: "column",
            overflow: "hidden",
            boxShadow: "0 10px 30px rgba(0, 0, 0, 0.5)"
          }}
        >
          <div style={{ padding: "14px 20px", borderBottom: "1px solid rgba(255,255,255,0.06)", display: "flex", justifyContent: "space-between", alignItems: "center" }}>
            <span style={{ fontSize: "14px", fontWeight: 600, color: "#fff" }}>PRIMARY OPTICAL SENSOR (LIVE)</span>
            <span style={{ fontSize: "12px", color: "#00d4ff", fontFamily: "monospace" }}>BUFFALO_L / 640x640 DET</span>
          </div>
          <div style={{ flex: 1, position: "relative", padding: "12px" }}>
            <CameraView onRecognized={handleRecognized} scanIntervalMs={2000} />
          </div>
        </div>

        {/* Target Profile Card & History */}
        <div style={{ display: "flex", flexDirection: "column", gap: "20px", overflowY: "auto" }}>
          {/* Target Verification Card */}
          <div
            style={{
              background: "#111827",
              borderRadius: "16px",
              border: `1px solid ${isFound ? "rgba(0, 255, 153, 0.4)" : "rgba(255, 59, 92, 0.3)"}`,
              padding: "22px",
              boxShadow: "0 10px 30px rgba(0, 0, 0, 0.4)"
            }}
          >
            <div style={{ display: "flex", alignItems: "center", justifyContent: "space-between", marginBottom: "16px" }}>
              <h2 style={{ fontSize: "17px", color: "#fff", margin: 0, display: "flex", alignItems: "center", gap: "8px" }}>
                {isFound ? <FaUserCheck style={{ color: "#00ff99" }} /> : <FaUserSlash style={{ color: "#ff3b5c" }} />}
                Target Information
              </h2>
              {latestRecognition && (
                <span className={`badge ${isFound ? "badge-green" : "badge-red"}`}>
                  {isFound ? `${confidence} Conf (${(score * 100).toFixed(1)}%)` : "UNKNOWN"}
                </span>
              )}
            </div>

            {!latestRecognition && (
              <div style={{ textAlign: "center", padding: "30px 0", color: "#8b9bb4" }}>
                <p>Awaiting optical target detection...</p>
              </div>
            )}

            {latestRecognition && !isFound && (
              <div style={{ textAlign: "center", padding: "25px 0", background: "rgba(255, 59, 92, 0.05)", borderRadius: "10px", border: "1px dashed rgba(255, 59, 92, 0.3)" }}>
                <h3 style={{ color: "#ff3b5c", marginBottom: "6px" }}>Unregistered Subject</h3>
                <p style={{ color: "#8b9bb4", fontSize: "13px" }}>
                  Face detected, but no matching biometric profile was found in the database.
                </p>
              </div>
            )}

            {isFound && (
              <div style={{ display: "flex", flexDirection: "column", gap: "14px" }}>
                <div style={{ display: "flex", gap: "16px", alignItems: "center" }}>
                  <div
                    style={{
                      width: "68px",
                      height: "68px",
                      borderRadius: "12px",
                      background: "#192033",
                      border: "2px solid #00ff99",
                      display: "flex",
                      alignItems: "center",
                      justifyContent: "center",
                      overflow: "hidden"
                    }}
                  >
                    {person.photo_path ? (
                      <img
                        src={`http://127.0.0.1:8000/${person.photo_path}`}
                        alt={person.full_name}
                        style={{ width: "100%", height: "100%", objectFit: "cover" }}
                        onError={(e) => { e.target.style.display = "none"; }}
                      />
                    ) : (
                      <FaIdCard size={28} color="#00ff99" />
                    )}
                  </div>
                  <div>
                    <h3 style={{ color: "#fff", fontSize: "20px", marginBottom: "4px" }}>{person.full_name}</h3>
                    <span className="badge badge-cyan">{person.person_type || "Registered Person"}</span>
                  </div>
                </div>

                <div style={{ display: "grid", gridTemplateColumns: "1fr 1fr", gap: "10px", marginTop: "8px" }}>
                  <div style={{ background: "#192033", padding: "10px 12px", borderRadius: "8px", fontSize: "13px" }}>
                    <span style={{ color: "#8b9bb4", display: "flex", alignItems: "center", gap: "6px" }}>
                      <FaBuilding color="#00d4ff" /> Department
                    </span>
                    <strong style={{ color: "#fff" }}>{person.department || "N/A"}</strong>
                  </div>
                  <div style={{ background: "#192033", padding: "10px 12px", borderRadius: "8px", fontSize: "13px" }}>
                    <span style={{ color: "#8b9bb4", display: "flex", alignItems: "center", gap: "6px" }}>
                      <FaBriefcase color="#00d4ff" /> Position
                    </span>
                    <strong style={{ color: "#fff" }}>{person.position || "N/A"}</strong>
                  </div>
                  <div style={{ background: "#192033", padding: "10px 12px", borderRadius: "8px", fontSize: "13px" }}>
                    <span style={{ color: "#8b9bb4", display: "flex", alignItems: "center", gap: "6px" }}>
                      <FaEnvelope color="#00d4ff" /> Email
                    </span>
                    <strong style={{ color: "#fff", wordBreak: "break-all" }}>{person.email || "N/A"}</strong>
                  </div>
                  <div style={{ background: "#192033", padding: "10px 12px", borderRadius: "8px", fontSize: "13px" }}>
                    <span style={{ color: "#8b9bb4", display: "flex", alignItems: "center", gap: "6px" }}>
                      <FaPhone color="#00d4ff" /> Phone
                    </span>
                    <strong style={{ color: "#fff" }}>{person.phone || "N/A"}</strong>
                  </div>
                </div>

                {person.notes && (
                  <div style={{ background: "rgba(0, 212, 255, 0.05)", padding: "10px 12px", borderRadius: "8px", borderLeft: "3px solid #00d4ff", fontSize: "13px" }}>
                    <span style={{ color: "#8b9bb4", fontSize: "11px", textTransform: "uppercase" }}>Special Notes:</span>
                    <p style={{ color: "#fff", marginTop: "2px" }}>{person.notes}</p>
                  </div>
                )}
              </div>
            )}
          </div>

          {/* Recent Detections Stream */}
          <div style={{ background: "#111827", borderRadius: "16px", border: "1px solid rgba(255,255,255,0.08)", padding: "18px", flex: 1 }}>
            <h3 style={{ fontSize: "15px", color: "#8b9bb4", marginBottom: "12px", textTransform: "uppercase", letterSpacing: "0.5px" }}>
              Recent Detections Log
            </h3>
            {detectionHistory.length === 0 ? (
              <p style={{ color: "#606f8b", fontSize: "13px" }}>No recent verified detections.</p>
            ) : (
              <div style={{ display: "flex", flexDirection: "column", gap: "8px" }}>
                {detectionHistory.map((item, idx) => (
                  <div
                    key={idx}
                    style={{
                      display: "flex",
                      justifyContent: "space-between",
                      alignItems: "center",
                      background: "#192033",
                      padding: "8px 12px",
                      borderRadius: "8px",
                      fontSize: "13px"
                    }}
                  >
                    <span style={{ color: "#fff", fontWeight: 600 }}>{item.person?.full_name}</span>
                    <span style={{ color: "#00ff99", fontFamily: "monospace", fontSize: "12px" }}>
                      {(item.score * 100).toFixed(1)}% match
                    </span>
                  </div>
                ))}
              </div>
            )}
          </div>
        </div>
      </div>
    </MainLayout>
  );
}