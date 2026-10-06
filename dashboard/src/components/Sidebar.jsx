import { NavLink } from "react-router-dom";
import {
  FaHome,

  FaUsers,
  FaCamera,
  FaDesktop,
  FaRobot,
  FaHistory,
  FaShieldAlt,
  FaNetworkWired,
  FaGlasses
} from "react-icons/fa";

import "../styles/sidebar.css";

const links = [
  {
    title: "Command Hub",
    icon: <FaHome />,
    path: "/",
  },
  {
    title: "Biometrics",
    icon: <FaUsers />,
    path: "/people",
  },
  {
    title: "Optical Stream",
    icon: <FaCamera />,
    path: "/camera",
  },
  {
    title: "Smart Glasses HUD",
    icon: <FaGlasses />,
    path: "/glasses-hud",
  },
  {
    title: "Event Timeline",
    icon: <FaHistory />,
    path: "/timeline",
  },
  {
    title: "CyberVision Defense",
    icon: <FaNetworkWired />,
    path: "/cyber",
  },
  {
    title: "Host Health",
    icon: <FaDesktop />,
    path: "/devices",
  },
  {
    title: "SOC Security Center",
    icon: <FaShieldAlt />,
    path: "/security",
  },
  {
    title: "Voice AI Tactical",
    icon: <FaRobot />,
    path: "/ai",
  },
];


export default function Sidebar() {
  return (
    <div className="sidebar">
      <div className="logo">
        <h2>EDITH AI</h2>
        <span>Cyber Vision</span>
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