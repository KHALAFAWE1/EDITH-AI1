import { useEffect, useState, useRef } from "react";
import MainLayout from "../layouts/MainLayout";
import { api } from "../services/api";
import { useLanguage } from "../context/LanguageContext";
import {
  FaCamera,
  FaVideo,
  FaPlus,
  FaSync,
  FaCheckCircle,
  FaTimesCircle,
  FaTrash,
  FaBroadcastTower,
  FaWifi,
  FaSpinner
} from "react-icons/fa";

export default function Cameras() {
  const { t } = useLanguage();
  const [cameras, setCameras] = useState([]);
  const [loading, setLoading] = useState(true);
  const [selectedCam, setSelectedCam] = useState(null);
  const [browserDevices, setBrowserDevices] = useState([]);

  // Form state for adding network camera
  const [showAddModal, setShowAddModal] = useState(false);
  const [camForm, setCamForm] = useState({ name: "", camera_type: "RTSP_STREAM", source_url: "" });
  const [testingConnection, setTestingConnection] = useState(false);
  const [testResult, setTestResult] = useState(null);

  const videoRef = useRef(null);
  const activeStreamRef = useRef(null);

  const fetchCameras = async () => {
    try {
      setLoading(true);
      const res = await api.get("/cameras");
      if (res.data && res.data.cameras) {
        setCameras(res.data.cameras);
        if (!selectedCam && res.data.cameras.length > 0) {
          setSelectedCam(res.data.cameras[0]);
        }
      }

      // Probing browser navigator media devices
      if (navigator.mediaDevices && navigator.mediaDevices.enumerateDevices) {
        const devs = await navigator.mediaDevices.enumerateDevices();
        const videoDevs = devs.filter((d) => d.kind === "videoinput");
        setBrowserDevices(videoDevs);
      }
    } catch (err) {
      console.warn("Failed to fetch cameras:", err);
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    fetchCameras();
  }, []);

  // Live video preview handler
  useEffect(() => {
    async function startSelectedCamera() {
      if (activeStreamRef.current) {
        activeStreamRef.current.getTracks().forEach((track) => track.stop());
      }

      if (selectedCam?.is_local || (!selectedCam?.source?.startsWith("rtsp") && !selectedCam?.source?.startsWith("http"))) {
        try {
          const stream = await navigator.mediaDevices.getUserMedia({
            video: { width: { ideal: 1280 }, height: { ideal: 720 } },
            audio: false
          });
          activeStreamRef.current = stream;
          if (videoRef.current) {
            videoRef.current.srcObject = stream;
          }
        } catch (e) {
          console.warn("Camera preview stream error:", e);
        }
      }
    }

    startSelectedCamera();

    return () => {
      if (activeStreamRef.current) {
        activeStreamRef.current.getTracks().forEach((track) => track.stop());
      }
    };
  }, [selectedCam]);

  const handleTestConnection = async () => {
    if (!camForm.source_url.trim()) return;
    try {
      setTestingConnection(true);
      setTestResult(null);
      const res = await api.post("/cameras/test-connection", { source_url: camForm.source_url });
      setTestResult(res.data);
    } catch (err) {
      setTestResult({ success: false, message: "Connection test failed: server timed out." });
    } finally {
      setTestingConnection(false);
    }
  };

  const handleAddCamera = async (e) => {
    e.preventDefault();
    if (!camForm.name.trim() || !camForm.source_url.trim()) return;

    try {
      await api.post("/cameras/add", camForm);
      setShowAddModal(false);
      setCamForm({ name: "", camera_type: "RTSP_STREAM", source_url: "" });
      setTestResult(null);
      fetchCameras();
    } catch (err) {
      alert("Failed to add camera: " + (err.response?.data?.detail || err.message));
    }
  };

  const handleDeleteCamera = async (dbId) => {
    if (!window.confirm("Are you sure you want to remove this network camera?")) return;
    try {
      await api.delete(`/cameras/${dbId}`);
      fetchCameras();
    } catch (e) {
      console.warn("Delete camera failed:", e);
    }
  };

  return (
    <MainLayout>
      {/* Header */}
      <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center", marginBottom: "22px", flexWrap: "wrap", gap: "10px" }}>
        <div>
          <h1 className="title" style={{ display: "flex", alignItems: "center", gap: "10px" }}>
            <FaCamera style={{ color: "#00d4ff" }} /> {t("cameras.title")}
          </h1>
          <p className="subtitle">{t("cameras.subtitle")}</p>
        </div>

        <div style={{ display: "flex", gap: "10px" }}>
          <button
            onClick={fetchCameras}
            style={{
              background: "#192033",
              color: "#00d4ff",
              border: "1px solid rgba(0, 212, 255, 0.3)",
              borderRadius: "10px",
              padding: "10px 16px",
              fontWeight: 700,
              fontSize: "13px",
              cursor: "pointer",
              display: "flex",
              alignItems: "center",
              gap: "6px"
            }}
          >
            <FaSync className={loading ? "spin" : ""} /> {t("timeline.refresh")}
          </button>

          <button
            onClick={() => setShowAddModal(true)}
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
              gap: "6px",
              cursor: "pointer"
            }}
          >
            <FaPlus /> {t("cameras.add_camera")}
          </button>
        </div>
      </div>

      {/* Main Viewport & List Grid */}
      <div style={{ display: "grid", gridTemplateColumns: "repeat(auto-fit, minmax(320px, 1fr))", gap: "20px" }}>
        {/* Live Active Stream Box */}
        <div style={{ background: "#111827", borderRadius: "16px", border: "1px solid rgba(0, 212, 255, 0.2)", padding: "20px", display: "flex", flexDirection: "column", gap: "14px" }}>
          <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center" }}>
            <h3 style={{ color: "#fff", margin: 0, fontSize: "16px", display: "flex", alignItems: "center", gap: "8px" }}>
              <FaVideo color="#00ff99" /> {selectedCam?.name || "Active Optical Stream"}
            </h3>
            <span className="badge badge-green">{selectedCam?.status || "Online"}</span>
          </div>

          <div style={{ position: "relative", width: "100%", height: "360px", background: "#050816", borderRadius: "12px", overflow: "hidden", border: "1px solid rgba(255,255,255,0.08)" }}>
            <video ref={videoRef} autoPlay playsInline muted style={{ width: "100%", height: "100%", objectFit: "cover" }} />
            <div style={{ position: "absolute", bottom: "12px", left: "12px", background: "rgba(5, 8, 22, 0.8)", padding: "4px 10px", borderRadius: "6px", fontSize: "11px", color: "#00d4ff", fontFamily: "monospace" }}>
              {selectedCam?.resolution || "1280x720"} @ {selectedCam?.fps || 30} FPS
            </div>
          </div>
        </div>

        {/* Camera Devices List */}
        <div style={{ background: "#111827", borderRadius: "16px", border: "1px solid rgba(255,255,255,0.08)", padding: "20px", display: "flex", flexDirection: "column", gap: "12px" }}>
          <h3 style={{ color: "#fff", margin: 0, fontSize: "16px" }}>
            {t("cameras.detected_cameras")} ({cameras.length})
          </h3>

          {cameras.length === 0 ? (
            <div style={{ textAlign: "center", padding: "40px 20px", color: "#8b9bb4" }}>
              <FaCamera size={36} color="#00d4ff" style={{ marginBottom: "10px" }} />
              <p>{t("cameras.no_cameras")}</p>
            </div>
          ) : (
            cameras.map((cam) => (
              <div
                key={cam.id}
                onClick={() => setSelectedCam(cam)}
                style={{
                  background: selectedCam?.id === cam.id ? "rgba(0, 212, 255, 0.15)" : "#192033",
                  border: selectedCam?.id === cam.id ? "1px solid #00d4ff" : "1px solid rgba(255,255,255,0.06)",
                  borderRadius: "12px",
                  padding: "14px 16px",
                  cursor: "pointer",
                  display: "flex",
                  justifyContent: "space-between",
                  alignItems: "center"
                }}
              >
                <div>
                  <h4 style={{ color: "#fff", margin: "0 0 4px 0", fontSize: "14px" }}>{cam.name}</h4>
                  <div style={{ fontSize: "12px", color: "#8b9bb4" }}>
                    Type: <strong style={{ color: "#00d4ff" }}>{cam.type}</strong> | {cam.resolution}
                  </div>
                </div>

                <div style={{ display: "flex", alignItems: "center", gap: "10px" }}>
                  <span className="badge badge-green">{cam.status}</span>
                  {!cam.is_local && cam.db_id && (
                    <button
                      onClick={(e) => {
                        e.stopPropagation();
                        handleDeleteCamera(cam.db_id);
                      }}
                      style={{ background: "none", border: "none", color: "#ff3b5c", cursor: "pointer" }}
                    >
                      <FaTrash size={12} />
                    </button>
                  )}
                </div>
              </div>
            ))
          )}
        </div>
      </div>

      {/* Add Network Camera Modal */}
      {showAddModal && (
        <div style={{ position: "fixed", top: 0, left: 0, width: "100vw", height: "100vh", background: "rgba(0,0,0,0.8)", backdropFilter: "blur(6px)", display: "flex", alignItems: "center", justifyContent: "center", zIndex: 1000, padding: "20px" }}>
          <div style={{ background: "#111827", border: "1px solid rgba(0,212,255,0.3)", borderRadius: "16px", padding: "24px", maxWidth: "500px", width: "100%" }}>
            <h3 style={{ color: "#fff", marginTop: 0, marginBottom: "16px" }}>{t("cameras.add_camera")}</h3>
            
            <form onSubmit={handleAddCamera} style={{ display: "flex", flexDirection: "column", gap: "14px" }}>
              <div>
                <label style={{ fontSize: "12px", color: "#8b9bb4", display: "block", marginBottom: "4px" }}>Camera Label Name</label>
                <input
                  type="text"
                  required
                  placeholder="e.g. Sector B Hallway Camera"
                  value={camForm.name}
                  onChange={(e) => setCamForm({ ...camForm, name: e.target.value })}
                  style={{ width: "100%", padding: "10px", background: "#192033", border: "1px solid rgba(255,255,255,0.1)", borderRadius: "8px", color: "#fff", outline: "none" }}
                />
              </div>

              <div>
                <label style={{ fontSize: "12px", color: "#8b9bb4", display: "block", marginBottom: "4px" }}>Stream Type</label>
                <select
                  value={camForm.camera_type}
                  onChange={(e) => setCamForm({ ...camForm, camera_type: e.target.value })}
                  style={{ width: "100%", padding: "10px", background: "#192033", border: "1px solid rgba(255,255,255,0.1)", borderRadius: "8px", color: "#fff", outline: "none" }}
                >
                  <option value="RTSP_STREAM">RTSP Video Stream (e.g. rtsp://192.168.1.50:554/live)</option>
                  <option value="HTTP_MJPEG">HTTP / MJPEG Video Endpoint</option>
                  <option value="WI_FI_CAM">Wi-Fi IP Camera</option>
                </select>
              </div>

              <div>
                <label style={{ fontSize: "12px", color: "#8b9bb4", display: "block", marginBottom: "4px" }}>Stream URL</label>
                <input
                  type="text"
                  required
                  placeholder="rtsp://admin:password@192.168.1.100:554/stream1"
                  value={camForm.source_url}
                  onChange={(e) => setCamForm({ ...camForm, source_url: e.target.value })}
                  style={{ width: "100%", padding: "10px", background: "#192033", border: "1px solid rgba(255,255,255,0.1)", borderRadius: "8px", color: "#fff", outline: "none" }}
                />
              </div>

              <div style={{ display: "flex", gap: "10px" }}>
                <button
                  type="button"
                  onClick={handleTestConnection}
                  disabled={testingConnection}
                  style={{ background: "#192033", color: "#00d4ff", border: "1px solid #00d4ff", padding: "8px 14px", borderRadius: "8px", cursor: "pointer", fontSize: "12px", fontWeight: 700 }}
                >
                  {testingConnection ? "Verifying Stream..." : t("cameras.test_connection")}
                </button>
              </div>

              {testResult && (
                <div style={{ background: testResult.success ? "rgba(0, 255, 153, 0.15)" : "rgba(255, 59, 92, 0.15)", color: testResult.success ? "#00ff99" : "#ff3b5c", padding: "10px", borderRadius: "8px", fontSize: "12px" }}>
                  {testResult.message}
                </div>
              )}

              <div style={{ display: "flex", justifyContent: "flex-end", gap: "10px", marginTop: "10px" }}>
                <button type="button" onClick={() => setShowAddModal(false)} style={{ background: "#192033", color: "#8b9bb4", border: "none", padding: "10px 16px", borderRadius: "8px", cursor: "pointer" }}>
                  Cancel
                </button>
                <button type="submit" style={{ background: "linear-gradient(135deg, #00d4ff, #0077ff)", color: "#050816", border: "none", padding: "10px 20px", borderRadius: "8px", fontWeight: 700, cursor: "pointer" }}>
                  Save Camera
                </button>
              </div>
            </form>
          </div>
        </div>
      )}
    </MainLayout>
  );
}
