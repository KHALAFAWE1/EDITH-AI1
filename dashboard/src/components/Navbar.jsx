import { FaShieldAlt } from "react-icons/fa";
import { useLanguage } from "../context/LanguageContext";
import LanguageToggle from "./LanguageToggle";

export default function Navbar() {
  const { t } = useLanguage();

  return (
    <div
      style={{
        height: "70px",
        display: "flex",
        justifyContent: "space-between",
        alignItems: "center",
        padding: "0 clamp(14px, 3vw, 25px)",
        background: "#0d1222",
        borderBottom: "1px solid rgba(255,255,255,.08)",
        flexWrap: "wrap",
        gap: "10px"
      }}
    >
      <div style={{ display: "flex", alignItems: "center", gap: "12px", flexWrap: "wrap" }}>
        <h2 style={{ color: "#fff", margin: 0, fontSize: "clamp(15px, 2vw, 18px)" }}>
          {t("app.title")}
        </h2>
        <span
          style={{
            fontSize: "11px",
            color: "#00ff99",
            background: "rgba(0, 255, 153, 0.1)",
            border: "1px solid rgba(0, 255, 153, 0.3)",
            padding: "3px 8px",
            borderRadius: "6px",
            display: "flex",
            alignItems: "center",
            gap: "5px"
          }}
        >
          <FaShieldAlt /> {t("app.status_secure")}
        </span>
      </div>

      <div style={{ display: "flex", alignItems: "center", gap: "14px" }}>
        <LanguageToggle />

        <div
          style={{
            color: "#00ff99",
            fontWeight: "bold",
            fontSize: "12px",
            display: "flex",
            alignItems: "center",
            gap: "6px"
          }}
        >
          <span style={{ width: "8px", height: "8px", borderRadius: "50%", background: "#00ff99", display: "inline-block", boxShadow: "0 0 8px #00ff99" }}></span>
          <span className="hide-on-mobile">{t("app.online")}</span>
        </div>
      </div>
    </div>
  );
}