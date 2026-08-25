import { NavLink } from "react-router-dom";
import {
  FaHome,
  FaUsers,
  FaCamera,
  FaDesktop,
  FaRobot,
} from "react-icons/fa";

import "../styles/sidebar.css";

const links = [
  {
    title: "Dashboard",
    icon: <FaHome />,
    path: "/",
  },
  {
    title: "People",
    icon: <FaUsers />,
    path: "/people",
  },
  {
    title: "Camera",
    icon: <FaCamera />,
    path: "/camera",
  },
  {
    title: "Devices",
    icon: <FaDesktop />,
    path: "/devices",
  },
  {
    title: "AI Assistant",
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