import { useEffect, useState } from "react";
import { motion } from "framer-motion";
import { Link } from "react-router-dom";
import MainLayout from "../layouts/MainLayout";
import CameraView from "../components/CameraView";
import StatusCard from "../components/StatusCard";
import { api } from "../services/api";
import { FaUsers, FaCamera, FaMicrochip, FaShieldAlt, FaIdCard, FaBuilding, FaBriefcase, FaEnvelope, FaPhone } from "react-icons/fa";

export default function Home() {
  const [person, setPerson] = useState(null);
  const [peopleCount, setPeopleCount] = useState(0);

  useEffect(() => {
    api.get("/people")
      .then((res) => {
        if (Array.isArray(res.data)) {
          setPeopleCount(res.data.length);
        }
      })
      .catch((err) => console.log("Failed to get people count", err));
  }, []);

  const isFound = person?.found && person?.person;
  const pData = person?.person;

  return (
    <MainLayout>
      <motion.div initial={{ opacity: 0 }} animate={{ opacity: 1 }}>
        {/* Header */}
        <div style={{ marginBottom: "25px" }}>
          <h1 className="title">EDITH AI Command Center</h1>
          <p className="subtitle">Real-time Biometric Surveillance, Face Recognition & System Telemetry</p>
        </div>

        {/* Status Metrics Bar */}
        <div
          style={{
            display: "grid",
            gridTemplateColumns: "repeat(auto-fit, minmax(220px, 1fr))",
            gap: "18px",
            marginBottom: "25px"
          }}
        >
          <StatusCard
            icon={<FaUsers />}
            title="Biometric Registry"
            value={peopleCount}
            subtitle={`${peopleCount} Verified Subjects`}
            accentColor="#00d4ff"
          />
          <StatusCard
            icon={<FaCamera />}
            title="Optical Sensor"
            value="ACTIVE"
            subtitle="Webcam 640x640 DET"
            accentColor="#00ff99"
          />
          <StatusCard
            icon={<FaMicrochip />}
            title="AI Vision Engine"
            value="BUFFALO_L"
            subtitle="InsightFace ArcFace 512D"
            accentColor="#aa3bff"
          />
          <StatusCard
            icon={<FaShieldAlt />}
            title="Security Status"
            value="SECURE"
            subtitle="Threshold: 70% Match"
            accentColor="#00ff99"
          />
        </div>

        {/* Live Feed and Recognition Panel */}
        <div className="hero">
          {/* Live Camera Feed */}
          <div className="camera-box">
            <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center", marginBottom: "15px" }}>
              <h2>📷 Live Optical Stream</h2>
              <Link to="/camera" style={{ color: "#00d4ff", fontSize: "13px", textDecoration: "none", fontWeight: 600 }}>
                Full Screen View &rarr;
              </Link>
            </div>

            <div className="camera-preview">
              <CameraView onRecognized={setPerson} scanIntervalMs={2500} />
            </div>
          </div>

          {/* Biometric Verification Card */}
          <div className="status-box">
            <h2>👤 Target Identity</h2>

            {isFound ? (
              <div style={{ display: "flex", flexDirection: "column", gap: "14px" }}>
                <div style={{ display: "flex", gap: "14px", alignItems: "center" }}>
                  <div
                    style={{
                      width: "60px",
                      height: "60px",
                      borderRadius: "12px",
                      background: "#192033",
                      border: "2px solid #00ff99",
                      display: "flex",
                      alignItems: "center",
                      justifyContent: "center",
                      overflow: "hidden"
                    }}
                  >
                    {pData.photo_path ? (
                      <img
                        src={
                          pData.photo_path.startsWith("http")
                            ? pData.photo_path
                            : `${import.meta.env.VITE_API_URL || ""}/${pData.photo_path.replace(/^\/+/, "")}`
                        }
                        alt={pData.full_name}
                        style={{ width: "100%", height: "100%", objectFit: "cover" }}
                        onError={(e) => {
                          if (!e.target.src.includes("127.0.0.1:8000")) {
                            e.target.src = `http://127.0.0.1:8000/${pData.photo_path.replace(/^\/+/, "")}`;
                          } else {
                            e.target.style.display = "none";
                          }
                        }}
                      />
                    ) : (
                      <FaIdCard size={24} color="#00ff99" />
                    )}

                  </div>
                  <div>
                    <h3 style={{ color: "#fff", fontSize: "18px", marginBottom: "2px" }}>{pData.full_name}</h3>
                    <span className="badge badge-green">{(person.score * 100).toFixed(1)}% Match</span>
                  </div>
                </div>

                <div style={{ display: "flex", flexDirection: "column", gap: "8px", fontSize: "13px", color: "#8b9bb4", marginTop: "6px" }}>
                  {pData.department && (
                    <div style={{ display: "flex", alignItems: "center", gap: "8px" }}>
                      <FaBuilding color="#00d4ff" />
                      <span style={{ color: "#fff" }}>{pData.department}</span>
                    </div>
                  )}
                  {pData.position && (
                    <div style={{ display: "flex", alignItems: "center", gap: "8px" }}>
                      <FaBriefcase color="#00d4ff" />
                      <span>{pData.position}</span>
                    </div>
                  )}
                  {pData.email && (
                    <div style={{ display: "flex", alignItems: "center", gap: "8px" }}>
                      <FaEnvelope color="#00d4ff" />
                      <span>{pData.email}</span>
                    </div>
                  )}
                  {pData.phone && (
                    <div style={{ display: "flex", alignItems: "center", gap: "8px" }}>
                      <FaPhone color="#00d4ff" />
                      <span>{pData.phone}</span>
                    </div>
                  )}
                </div>
              </div>
            ) : person?.faces_count > 0 || person?.bbox ? (
              <div style={{ textAlign: "center", padding: "30px 0" }}>
                <span className="badge badge-red" style={{ marginBottom: "10px" }}>UNKNOWN TARGET</span>
                <p style={{ color: "#8b9bb4", fontSize: "13px" }}>Face detected in frame but not registered in database.</p>
              </div>
            ) : (
              <div style={{ textAlign: "center", padding: "40px 0", color: "#606f8b" }}>
                <p>Waiting for subjects in camera view...</p>
              </div>
            )}
          </div>
        </div>
      </motion.div>
    </MainLayout>
  );
}