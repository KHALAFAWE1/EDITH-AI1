import React, { createContext, useContext, useState, useEffect } from "react";
import arDict from "../i18n/ar.json";
import enDict from "../i18n/en.json";

const LanguageContext = createContext();

const dictionaries = {
  ar: arDict,
  en: enDict
};

export function LanguageProvider({ children }) {
  const [language, setLanguageState] = useState(() => {
    return localStorage.getItem("edith_language") || "ar";
  });

  const setLanguage = (lang) => {
    const validLang = lang === "en" ? "en" : "ar";
    setLanguageState(validLang);
    localStorage.setItem("edith_language", validLang);
  };

  useEffect(() => {
    const isRtl = language === "ar";
    document.documentElement.dir = isRtl ? "rtl" : "ltr";
    document.documentElement.lang = language;
  }, [language]);

  // Nested key resolver helper (e.g. t("nav.command_hub"))
  const t = (path, fallback = "") => {
    const currentDict = dictionaries[language] || dictionaries.ar;
    const keys = path.split(".");
    let current = currentDict;

    for (const key of keys) {
      if (current && typeof current === "object" && key in current) {
        current = current[key];
      } else {
        return fallback || path;
      }
    }
    return typeof current === "string" ? current : fallback || path;
  };

  return (
    <LanguageContext.Provider value={{ language, setLanguage, t, isRtl: language === "ar" }}>
      {children}
    </LanguageContext.Provider>
  );
}

export function useLanguage() {
  const context = useContext(LanguageContext);
  if (!context) {
    throw new Error("useLanguage must be used within a LanguageProvider");
  }
  return context;
}
