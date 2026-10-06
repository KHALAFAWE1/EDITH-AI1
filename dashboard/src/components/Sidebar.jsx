import { NavLink } from "react-router-dom";
import { useLanguage } from "../context/LanguageContext";
import {
  FaHome,
  FaUsers,
  FaCamera,
  FaSlidersH,
  FaRobot,
  FaGlasses,
  FaHistory,
  FaNetworkWired,
  FaDesktop,
  FaShieldAlt
} from "react-icons/fa";

import "../styles/sidebar.css";

export default function Sidebar() {
  const { t } = useLanguage();

  const links = [
    {
      title: t("nav.command_hub"),
      icon: <FaHome />,
      path: "/",
    },
    {
      title: t("nav.biometrics"),
      icon: <FaUsers />,
      path: "/people",
    },
    {
      title: t("nav.optical_stream"),
      icon: <FaCamera />,
      path: "/camera",
    },
    {
      title: t("nav.camera_manager"),
      icon: <FaSlidersH />,
      path: "/cameras",
    },
    {
      title: t("nav.ai_assistant"),
      icon: <FaRobot />,
      path: "/ai",
    },
    {
      title: t("nav.smart_glasses"),
      icon: <FaGlasses />,
      path: "/glasses-hud",
    },
    {
      title: t("nav.timeline"),
      icon: <FaHistory />,
      path: "/timeline",
    },
    {
      title: t("nav.cyber_defense"),
      icon: <FaNetworkWired />,
      path: "/cyber",
    },
    {
      title: t("nav.host_health"),
      icon: <FaDesktop />,
      path: "/devices",
    },
    {
      title: t("nav.soc_security"),
      icon: <FaShieldAlt />,
      path: "/security",
    },
  ];

  return (
    <div className="sidebar">
      <div className="logo">
        <h2>EDITH AI</h2>
        <span>{t("app.subtitle")}</span>
      </div>

      <div className="menu">
        {links.map((item) => (
          <NavLink
            key={item.path}
            to={item.path}
            className={({ isActive }) =>
              isActive ? "menu-item active" : "menu-item"
            }
          >
            {item.icon}
            <span>{item.title}</span>
          </NavLink>
        ))}
      </div>
    </div>
  );
}
