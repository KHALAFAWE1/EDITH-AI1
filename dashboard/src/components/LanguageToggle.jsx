import React from "react";
import { useLanguage } from "../context/LanguageContext";
import { FaGlobe } from "react-icons/fa";

export default function LanguageToggle() {
  const { language, setLanguage } = useLanguage();

  return (
    <div
      style={{
        display: "inline-flex",
        alignItems: "center",
        background: "#192033",
        border: "1px solid rgba(0, 212, 255, 0.3)",
        borderRadius: "20px",
        padding: "3px 4px",
        gap: "4px"
      }}
    >
      <button
        onClick={() => setLanguage("ar")}
        style={{
          background: language === "ar" ? "linear-gradient(135deg, #00d4ff, #0077ff)" : "transparent",
          color: language === "ar" ? "#050816" : "#8b9bb4",
          border: "none",
          borderRadius: "16px",
          padding: "4px 10px",
          fontSize: "12px",
          fontWeight: 700,
          cursor: "pointer",
          transition: "all 0.2s ease"
        }}
      >
        العربية
      </button>

      <button
        onClick={() => setLanguage("en")}
        style={{
          background: language === "en" ? "linear-gradient(135deg, #00d4ff, #0077ff)" : "transparent",
          color: language === "en" ? "#050816" : "#8b9bb4",
          border: "none",
          borderRadius: "16px",
          padding: "4px 10px",
          fontSize: "12px",
          fontWeight: 700,
          cursor: "pointer",
          transition: "all 0.2s ease"
        }}
      >
        English
      </button>
    </div>
  );
}
