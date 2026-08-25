import { BrowserRouter, Routes, Route } from "react-router-dom";

import Home from "./pages/Home";
import People from "./pages/People";
import Camera from "./pages/Camera";
import Devices from "./pages/Devices";
import AI from "./pages/AI";

function App() {
  return (
    <BrowserRouter>
      <Routes>
        <Route path="/" element={<Home />} />
        <Route path="/people" element={<People />} />
        <Route path="/camera" element={<Camera />} />
        <Route path="/devices" element={<Devices />} />
        <Route path="/ai" element={<AI />} />
      </Routes>
    </BrowserRouter>
  );
}

export default App;