export default function StatusCard({ icon, title, value, subtitle, accentColor = "#00d4ff" }) {
  return (
    <div
      style={{
        background: "#111827",
        borderRadius: "16px",
        padding: "20px",
        border: `1px solid rgba(${accentColor === "#00ff99" ? "0, 255, 153" : "0, 212, 255"}, 0.2)`,
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
          background: "rgba(25, 32, 51, 0.8)",
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
        <p style={{ color: "#8b9bb4", fontSize: "13px", marginBottom: "2px", textTransform: "uppercase", letterSpacing: "0.5px" }}>
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
