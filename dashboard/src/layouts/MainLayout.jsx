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
      }}
    >
      <Sidebar />

      <div
        style={{
          flex: 1,
          display: "flex",
          flexDirection: "column",
          overflow: "hidden",
        }}
      >
        <Navbar />

        <motion.div
          initial={{ opacity: 0, y: 25 }}
          animate={{ opacity: 1, y: 0 }}
          transition={{ duration: 0.5 }}
          style={{
            flex: 1,
            padding: "25px",
            overflowY: "auto",
          }}
        >
          {children}
        </motion.div>
      </div>
    </div>
  );
}

export default MainLayout;