# EDITH-AI — MASTER DEVELOPMENT ROADMAP

## Phased Progression from Baseline to Full Situational Awareness

---

### 🟢 PHASE 1 — SYSTEM STABILIZATION & CORE SECURITY (IN PROGRESS)
- [x] Unify FastAPI + React SPA into single distributable binary bundle
- [x] Auto-fallback SQLAlchemy engine (Postgres -> SQLite)
- [x] Continuous Wake-Word ("يا إيديث" / "Hey EDITH") with Web Audio Synthesizer
- [x] Fix photo path resolution & defensive array guarding in People/Devices pages
- [ ] Implement `User` model, password hashing (bcrypt), and JWT Authentication in `server/app/routers/auth.py`
- [ ] Implement Security Audit Logging in `server/app/routers/security.py`
- [ ] Fix photo paths in `Home.jsx` to use dynamic API base URL

---

### 🔵 PHASE 2 — MODULAR VISION ENGINE & OBJECT DETECTION
- [ ] Build `VisionProvider` abstraction interface (`GeminiVisionProvider`, `LocalVisionProvider`)
- [ ] Implement Local Object Detection (Laptop, Phone, Backpack, Chair, Desk, Monitor, Person, Door)
- [ ] Implement Structured Scene Understanding (`scene`, `people_count`, `objects`, `anomalies`, `risk_level`)
- [ ] Build OCR Document Intelligence Service (`/api/vision/ocr`) for signs, screens, text, and serial numbers

---

### 🟣 PHASE 3 — ADVANCED PERSON RECOGNITION & PRIVACY CONTROLS
- [ ] Add explicit consent flag & retention policy to `Person` model
- [ ] Add configurable recognition confidence thresholds (Default: 70%, Strict: 85%)
- [ ] Unknown subject tracking with temporary tracking IDs (e.g. `Subject-Unknown-042`)
- [ ] Audit log for all biometric lookup queries and profile views

---

### 🟡 PHASE 4 & 5 — EPISODIC MEMORY & SPATIAL CONTEXT
- [ ] Create `Event` entity (timestamp, location, type, source, confidence, metadata, severity)
- [ ] Create `Location` zone management (e.g., "Server Room 1", "Lab 4", "Main Gate")
- [ ] Spatial Context Service mapping: `Person -> Location`, `Object -> Location`, `Device -> Location`

---

### 🟠 PHASE 6 & 7 — BASELINE ANOMALY DETECTION & CENTRALIZED RISK ENGINE
- [ ] Implement `BaselineEngine` calculating typical people count, device counts, and operating hours per zone
- [ ] Implement `AnomalyEngine` detecting deviations (unexpected presence, new device, missing equipment)
- [ ] Implement Centralized `RiskEngine` computing dynamic 0–100 score with severity categories (`LOW`, `MEDIUM`, `HIGH`, `CRITICAL`)
- [ ] Rule-based and AI-assisted factor weighting

---

### 🔴 PHASE 8 & 9 — CYBERVISION & PHYSICAL-CYBER CORRELATION
- [ ] Defensive local network scanner (Authorized IP/MAC/Hostname/Status monitoring via `psutil`/ARP)
- [ ] Physical-Cyber Correlation Engine: Links physical camera entries with new network device arrivals
- [ ] Causation safeguard: Clearly declares correlations without automated false accusations

---

### ⚪ PHASE 10 & 11 — EXPLAINABLE AI & AGENT PLANNING MODE
- [ ] Structured Explainable AI decision output (`WHAT`, `WHY`, `EVIDENCE`, `CONFIDENCE`, `RECOMMENDED_ACTION`)
- [ ] Tactical Agent Planner (`Goal -> Plan -> Execute -> Verify -> Report`)

---

### 🛡️ PHASE 12–17 — SOC COMMAND DASHBOARD & SMART GLASSES HUD
- [ ] Upgrade React Dashboard into a futuristic SOC Command Center
- [ ] Interactive Real-Time Event Timeline component (`/timeline`)
- [ ] CyberVision Network Defense panel (`/cyber`)
- [ ] Smart Glasses Tactical HUD Simulator (`/glasses-hud`)
- [ ] Cybersecurity Education Mode with Interactive Quizzes & Scenario Labs (`/education`)

---

### 🧪 PHASE 18–22 — TEST SUITE & HARDENING
- [ ] Pytest unit and integration test suite (`tests/test_auth.py`, `tests/test_vision.py`, `tests/test_risk.py`, `tests/test_recognition.py`)
- [ ] Production documentation & deployment guidelines
