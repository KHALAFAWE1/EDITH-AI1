import { motion } from "framer-motion";
import Sidebar from "../components/Sidebar";
import Navbar from "../components/Navbar";

function MainLayout({ children }) {
  return (
    <div
      style={{
        display: "flex",
        width: "100vw",
        height: "100vh",
        background: "#050816",
        overflow: "hidden",
        position: "relative"
      }}
    >
      <Sidebar />

      <div
        style={{
          flex: 1,
          display: "flex",
          flexDirection: "column",
          overflow: "hidden",
          width: "100%"
        }}
      >
        <Navbar />

        <motion.div
          initial={{ opacity: 0, y: 15 }}
          animate={{ opacity: 1, y: 0 }}
          transition={{ duration: 0.3 }}
          className="main-content-scroll"
          style={{
            flex: 1,
            padding: "clamp(12px, 2.5vw, 25px)",
            paddingBottom: "80px", // مسافة أمان لشريط الموبايل السفلي
            overflowY: "auto",
            overflowX: "hidden",
            WebkitOverflowScrolling: "touch"
          }}
        >
          {children}
        </motion.div>
      </div>
    </div>
  );
}

export default MainLayout;