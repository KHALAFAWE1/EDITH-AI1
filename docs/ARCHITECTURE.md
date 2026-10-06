# EDITH-AI — SYSTEM ARCHITECTURE & DESIGN

## 1. System Vision: AI Situational Awareness Platform

EDITH-AI is engineered as an enterprise-grade **Tactical AI Defense & Situational Awareness Platform**. Rather than a basic conversational agent, EDITH continuously observes its operational environment, maintains episodic memory, detects anomalies against baseline norms, correlates physical optical triggers with network cyber-telemetry, assesses risk (0–100), and provides explainable intelligence across a SOC Dashboard and simulated Smart Glasses HUD.

```text
                                  ┌───────────────────────────────┐
                                  │           EDITH-AI            │
                                  │ Situational Awareness Platform│
                                  └───────────────┬───────────────┘
                                                  │
                 ┌────────────────────────────────┼────────────────────────────────┐
                 │                                │                                │
           PERCEPTION LAYER                  MEMORY LAYER                     AUDIO LAYER
                 │                                │                                │
      ┌──────────┼──────────┐                     │                         ┌──────┴──────┐
      │          │          │                     │                         │             │
  ArcFace      Vision      OCR             Episodic Events                 STT           TTS
 Biometrics   Objects   Documents           & Baselining               (Wake Word)   (Synthesizer)
      │          │          │                     │                         │             │
      └──────────┴──────────┴──────────────┬──────┴─────────────────────────┴─────────────┘
                                           │
                                  ┌────────▼────────┐
                                  │ REASONING LAYER │
                                  │   AI + Rules    │
                                  └────────┬────────┘
                                           │
                 ┌─────────────────────────┼─────────────────────────┐
                 │                         │                         │
            RISK ENGINE             ANOMALY ENGINE             ACTION ENGINE
          (0–100 Scoring)         (Baseline Deviation)       (OS/Network Tasks)
                 │                         │                         │
                 └─────────────────────────┼─────────────────────────┘
                                           │
                                ┌──────────▼──────────┐
                                │   INTERFACE LAYER   │
                                ├─────────────────────┤
                                │ 🖥️ SOC Dashboard    │
                                │ 🕶️ Smart Glasses HUD│
                                │ 🎙️ Voice Feedback   │
                                │ ⚠️ Real-time Alerts │
                                └─────────────────────┘
```

---

## 2. Layered Architecture

### 2.1 Backend Layer (`server/app/`)
* **API Routers (`server/app/routers/`)**:
  * `auth.py`: User registration, JWT login, RBAC (`Admin`, `Analyst`, `Operator`).
  * `security.py`: Audit trails, real-time security events, access logs.
  * `people.py`: Biometric registry CRUD, ArcFace embeddings, consent records.
  * `recognition.py`: Multi-face identification, bounding boxes, confidence scoring.
  * `vision.py` / `objects.py`: Object detection, scene classification, OCR.
  * `device.py` / `cyber.py`: Infrastructure node monitoring, ARP/IP network discovery.
  * `events.py` / `timeline.py`: Episodic memory and event timeline.
  * `risk.py`: Centralized risk scoring and anomaly correlation engine.
  * `ai.py`: Multi-modal tactical assistant, OS command execution, wake-word backend.

### 2.2 Core & Provider Abstraction (`server/app/core/`)
* **`AIProvider`**: Base interface with implementations for `GeminiProvider`, `OllamaProvider`, and `LocalProvider`.
* **`VisionProvider`**: Interface for Object Detection, Scene Parsing, and OCR.
* **`RiskEngine`**: Multi-factor scoring combining Biometrics + Spatial Context + Network state + Time anomalies.
* **`CorrelationEngine`**: Temporal and spatial cross-referencing of physical camera detections with network device appearances.

### 2.3 Frontend Layer (`dashboard/src/`)
* **`pages/Home.jsx`**: Live Optical Feed + Target Identity Card + Metric Gauges.
* **`pages/People.jsx`**: Biometric Subject Registry + Photo Upload with ArcFace 512D embeddings.
* **`pages/Devices.jsx`**: Telemetry and Host Health Monitor.
* **`pages/AI.jsx`**: Voice Vision Assistant, Continuous Wake Word, Web Audio Cyber SFX, Tactical Chat.
* **`pages/Security.jsx`**: SOC Security Center, Audit Logs, Risk Breakdown.
* **`pages/Camera.jsx`**: Fullscreen Optical HUD with bounding box overlays.
* **`pages/GlassesHUD.jsx`**: Simulated Smart Glasses Tactical Overlay.

---

## 3. Data Flow & Security Model
1. **Camera Frame Acquisition**: WebRTC stream captures frame at configurable interval (e.g. 2000ms).
2. **Biometric & Object Processing**: ArcFace extracts 512-dim embedding; Vision detector classifies visible entities.
3. **Episodic Memory Logging**: Event stored in database with timestamp, location, entity type, and confidence.
4. **Baseline & Anomaly Assessment**: System queries current environmental state vs historical baseline.
5. **Cyber Correlation**: Network discovery cross-references active MAC/IPs with visual detections.
6. **Explainable AI Formulation**: System outputs structured decision with `WHAT`, `WHY`, `EVIDENCE`, `CONFIDENCE`, and `RECOMMENDED_ACTION`.
7. **Multi-Channel Dispatch**: HUD render + Voice feedback + SOC Dashboard alert.
