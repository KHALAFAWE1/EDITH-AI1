export default function StatusCard({ icon, title, value, subtitle, accentColor = "#f59e0b" }) {
  return (
    <div
      style={{
        background: "#12151e",
        borderRadius: "16px",
        padding: "20px",
        border: `1px solid rgba(${accentColor === "#00ff99" ? "0, 255, 153" : "245, 158, 11"}, 0.2)`,
        boxShadow: "0 10px 25px rgba(0, 0, 0, 0.35)",
        display: "flex",
        alignItems: "center",
        gap: "16px"
      }}
    >
      <div
        style={{
          width: "50px",
          height: "50px",
          borderRadius: "12px",
          background: "rgba(26, 30, 41, 0.8)",
          border: `1px solid ${accentColor}`,
          display: "flex",
          alignItems: "center",
          justifyContent: "center",
          color: accentColor,
          fontSize: "22px",
          flexShrink: 0
        }}
      >
        {icon}
      </div>

      <div>
        <p style={{ color: "#9ca3af", fontSize: "13px", marginBottom: "2px", textTransform: "uppercase", letterSpacing: "0.5px" }}>
          {title}
        </p>
        <h3 style={{ color: "#ffffff", fontSize: "24px", fontWeight: 700, margin: 0, fontFamily: "monospace" }}>
          {value}
        </h3>
        {subtitle && (
          <span style={{ color: accentColor, fontSize: "11px", fontWeight: 600 }}>
            {subtitle}
          </span>
        )}
      </div>
    </div>
  );
}
