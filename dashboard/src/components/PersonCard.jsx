import { FaUserGraduate, FaChalkboardTeacher, FaUserTie, FaUserShield, FaTrash, FaBuilding, FaBriefcase, FaEnvelope, FaPhone, FaFingerprint } from "react-icons/fa";

export default function PersonCard({ person, onDelete }) {
  const getRoleIcon = (type) => {
    switch ((type || "").toLowerCase()) {
      case "teacher":
      case "professor":
        return <FaChalkboardTeacher style={{ color: "#f59e0b" }} />;
      case "security":
      case "admin":
        return <FaUserShield style={{ color: "#ff3b5c" }} />;
      case "employee":
      case "staff":
        return <FaUserTie style={{ color: "#aa3bff" }} />;
      default:
        return <FaUserGraduate style={{ color: "#00ff99" }} />;
    }
  };

  const getRoleBadgeClass = (type) => {
    switch ((type || "").toLowerCase()) {
      case "teacher":
      case "professor":
        return "badge-cyan";
      case "security":
      case "admin":
        return "badge-red";
      default:
        return "badge-green";
    }
  };

  return (
    <div
      style={{
        background: "#12151e",
        borderRadius: "16px",
        border: "1px solid rgba(245, 158, 11, 0.18)",
        padding: "20px",
        display: "flex",
        flexDirection: "column",
        justifyContent: "space-between",
        boxShadow: "0 10px 25px rgba(0, 0, 0, 0.3)",
        position: "relative",
        transition: "all 0.3s ease"
      }}
    >
      {/* Top Section */}
      <div>
        <div style={{ display: "flex", justifyContent: "space-between", alignItems: "flex-start", marginBottom: "16px" }}>
          <div style={{ display: "flex", gap: "14px", alignItems: "center" }}>
            <div
              style={{
                width: "56px",
                height: "56px",
                borderRadius: "12px",
                background: "#1a1e29",
                border: "2px solid rgba(245, 158, 11, 0.35)",
                display: "flex",
                alignItems: "center",
                justifyContent: "center",
                overflow: "hidden",
                flexShrink: 0
              }}
            >
              {person.photo_path ? (
                <img
                  src={
                    person.photo_path.startsWith("http")
                      ? person.photo_path
                      : `${import.meta.env.VITE_API_URL || ""}/${person.photo_path.replace(/^\/+/, "")}`
                  }
                  alt={person.full_name}
                  style={{ width: "100%", height: "100%", objectFit: "cover" }}
                  onError={(e) => {
                    // Fallback to direct localhost if relative fails in dev mode
                    if (!e.target.src.includes("127.0.0.1:8000")) {
                      e.target.src = `http://127.0.0.1:8000/${person.photo_path.replace(/^\/+/, "")}`;
                    } else {
                      e.target.style.display = "none";
                    }
                  }}
                />
              ) : (
                getRoleIcon(person.person_type)
              )}
            </div>

            <div>
              <h3 style={{ color: "#ffffff", fontSize: "16px", fontWeight: 600, marginBottom: "4px" }}>
                {person.full_name}
              </h3>
              <span className={`badge ${getRoleBadgeClass(person.person_type)}`}>
                {person.person_type || "Registered"}
              </span>
            </div>
          </div>

          <button
            onClick={() => onDelete(person.id, person.full_name)}
            title="Delete Subject"
            style={{
              background: "rgba(255, 59, 92, 0.1)",
              border: "1px solid rgba(255, 59, 92, 0.3)",
              color: "#ff3b5c",
              borderRadius: "8px",
              padding: "7px 10px",
              cursor: "pointer",
              display: "flex",
              alignItems: "center",
              justifyContent: "center",
              transition: "all 0.2s"
            }}
            onMouseOver={(e) => (e.currentTarget.style.background = "rgba(255, 59, 92, 0.25)")}
            onMouseOut={(e) => (e.currentTarget.style.background = "rgba(255, 59, 92, 0.1)")}
          >
            <FaTrash size={12} />
          </button>
        </div>

        {/* Info Grid */}
        <div style={{ display: "flex", flexDirection: "column", gap: "8px", fontSize: "13px", color: "#9ca3af", marginTop: "12px" }}>
          {person.department && (
            <div style={{ display: "flex", alignItems: "center", gap: "8px" }}>
              <FaBuilding color="#f59e0b" size={13} />
              <span style={{ color: "#fff" }}>{person.department}</span>
            </div>
          )}
          {person.position && (
            <div style={{ display: "flex", alignItems: "center", gap: "8px" }}>
              <FaBriefcase color="#f59e0b" size={13} />
              <span>{person.position}</span>
            </div>
          )}
          {person.email && (
            <div style={{ display: "flex", alignItems: "center", gap: "8px" }}>
              <FaEnvelope color="#f59e0b" size={13} />
              <span>{person.email}</span>
            </div>
          )}
          {person.phone && (
            <div style={{ display: "flex", alignItems: "center", gap: "8px" }}>
              <FaPhone color="#f59e0b" size={13} />
              <span>{person.phone}</span>
            </div>
          )}
        </div>
      </div>

      {/* Footer Biometrics Info */}
      <div
        style={{
          marginTop: "16px",
          paddingTop: "12px",
          borderTop: "1px solid rgba(255, 255, 255, 0.06)",
          display: "flex",
          justifyContent: "space-between",
          alignItems: "center",
          fontSize: "12px",
          color: "#9ca3af"
        }}
      >
        <span style={{ display: "flex", alignItems: "center", gap: "5px", color: "#f59e0b", fontFamily: "monospace" }}>
          <FaFingerprint size={14} /> {person.embeddings_count || 1} Embedded Ref(s)
        </span>
        <span>ID #{person.id}</span>
      </div>
    </div>
  );
}
