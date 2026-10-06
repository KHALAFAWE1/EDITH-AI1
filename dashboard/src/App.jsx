import { BrowserRouter, Routes, Route } from "react-router-dom";

import Home from "./pages/Home";
import People from "./pages/People";
import Camera from "./pages/Camera";
import GlassesHUD from "./pages/GlassesHUD";
import Timeline from "./pages/Timeline";
import CyberVision from "./pages/CyberVision";
import Devices from "./pages/Devices";
import Security from "./pages/Security";
import AI from "./pages/AI";

function App() {
  return (
    <BrowserRouter>
      <Routes>
        <Route path="/" element={<Home />} />
        <Route path="/people" element={<People />} />
        <Route path="/camera" element={<Camera />} />
        <Route path="/glasses-hud" element={<GlassesHUD />} />
        <Route path="/timeline" element={<Timeline />} />
        <Route path="/cyber" element={<CyberVision />} />
        <Route path="/devices" element={<Devices />} />
        <Route path="/security" element={<Security />} />
        <Route path="/ai" element={<AI />} />
      </Routes>
    </BrowserRouter>
  );
}

export default App;