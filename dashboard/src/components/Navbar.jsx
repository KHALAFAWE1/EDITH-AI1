import { FaShieldAlt } from "react-icons/fa";

export default function Navbar() {
  return (
    <div
      style={{
        height: "70px",
        display: "flex",
        justifyContent: "space-between",
        alignItems: "center",
        padding: "0 25px",
        background: "#0d1222",
        borderBottom: "1px solid rgba(255,255,255,.08)",
      }}
    >
      <div style={{ display: "flex", alignItems: "center", gap: "15px" }}>
        <h2 style={{ color: "#fff", margin: 0, fontSize: "18px" }}>
          Welcome to EDITH AI
        </h2>
        <span
          style={{
            fontSize: "11px",
            color: "#00ff99",
            background: "rgba(0, 255, 153, 0.1)",
            border: "1px solid rgba(0, 255, 153, 0.3)",
            padding: "4px 8px",
            borderRadius: "6px",
            display: "flex",
            alignItems: "center",
            gap: "5px"
          }}
        >
          <FaShieldAlt /> Grid Secured
        </span>
      </div>

      <div style={{ display: "flex", alignItems: "center", gap: "14px" }}>
        <div
          style={{
            color: "#00ff99",
            fontWeight: "bold",
            fontSize: "13px",
            display: "flex",
            alignItems: "center",
            gap: "6px"
          }}
        >
          <span style={{ width: "8px", height: "8px", borderRadius: "50%", background: "#00ff99", display: "inline-block", boxShadow: "0 0 8px #00ff99" }}></span>
          <span>Online & Encrypted</span>
        </div>
      </div>
    </div>
  );
}
