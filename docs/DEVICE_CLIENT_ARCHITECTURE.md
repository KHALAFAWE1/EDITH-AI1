# EDITH-AI — Universal Device Client Layer Architecture

## 1. Architectural Philosophy

The **Universal EDITH Device Client Layer** is engineered as a device-agnostic, thin perception and telemetry edge client. Heavy intelligence, face recognition, multi-modal vision synthesis, risk correlation, and cyber defense grids reside centrally on the EDITH-AI server core.

```
                         +-----------------------------------+
                         |         EDITH-AI Backend          |
                         |   FastAPI Core & Defense Grid     |
                         +-----------------------------------+
                                          |
                        Universal Device WebSocket & REST API
                                          |
       +-----------------+----------------+-----------------+-----------------+
       |                 |                |                 |                 |
+--------------+  +--------------+  +-------------+  +--------------+  +--------------+
| iOS / iPhone |  | Android      |  | Desktop/Web |  | PWA Mobile   |  | Smart        |
| Safari / App |  | Chrome / App |  | Windows/Mac |  | Offline/Sync |  | Glasses HUD  |
+--------------+  +--------------+  +-------------+  +--------------+  +--------------+
```

---

## 2. Core Tenets

### 2.1 Device Agnostic Client Design
* EDITH-AI is **not** an iPhone-specific or Android-specific system.
* Any compliant user-agent supporting standard Web APIs (`MediaDevices`, `WebSocket`, `WebRTC`, `Navigator`) can enroll as an authenticated client node.
* Legacy devices (e.g., iPhone 6 on iOS 12 Safari) and modern high-end devices operate seamlessly through feature detection and graceful degradation.

### 2.2 Edge Perception vs. Server Intelligence
* **Client Role**:
  * Capture optical sensor stream (`getUserMedia` video frames).
  * Collect real-time telemetry (Battery status, Orientation, Device type, Screen dimensions).
  * Render tactical HUD AR reticle and situational overlay.
  * Receive and execute allowlisted server commands (`PING`, `CAPTURE_FRAME`, `HUD_ALERT`, `VIBRATE`, `RECONNECT`).
* **Server Role**:
  * ArcFace 512D Biometric feature extraction and recognition.
  * Gemini Vision multi-modal cognitive reasoning.
  * Real-time network correlation and risk scoring (0-100).
  * Ephemeral QR pairing token issuance, validation, and session authorization.
  * WebSocket broadcast and bi-directional command dispatching.

---

## 3. Communication Protocols

### 3.1 Ephemeral QR Pairing Flow (REST)
1. **Host Request**: Dashboard requests a new pairing session via `POST /api/v1/devices/pairing/generate`.
2. **Token Minting**: Server generates a 5-minute TTL cryptographic token (`pair_...`) and QR code data payload.
3. **Client Scan**: Companion device scans the QR code or opens `http://<server-ip>:8000/client?pair_token=pair_...`.
4. **Claim Exchange**: Client issues `POST /api/v1/devices/pairing/claim` with hardware capability flags.
5. **Credential Storage**: Server returns permanent `device_id` and secret `auth_token`. Client caches these securely in `localStorage`.

### 3.2 Real-Time WebSocket Channel (`/api/v1/devices/{device_id}/ws`)
* **Handshake**: Client connects to `ws://<host>:8000/api/v1/devices/{device_id}/ws?token={auth_token}`.
* **Authentication**: Server verifies that `auth_token` matches the enrolled device identity.
* **Telemetry Streaming**: Client pushes periodic JSON heartbeats containing battery %, charging state, optical stream state.
* **Command Dispatch**: Server dispatches low-latency tactical commands (`PING`, `HUD_ALERT`, `VIBRATE`, etc.).
* **Connection Lifecycle**: `DeviceConnectionManager` tracks active sockets, auto-updates DB connection status (`ONLINE` / `OFFLINE`), and broadcasts disconnection alerts.

---

## 4. Security & Zero-Trust Policies

1. **Ephemeral Tokens**: Pairing tokens expire in 300 seconds and are strictly single-use (`CLAIMED` status cannot be reused).
2. **Command Allowlisting**: Remote command dispatch is constrained to safe operations (`PING`, `CAPTURE_FRAME`, `TORCH_ON`, `TORCH_OFF`, `HUD_ALERT`, `VIBRATE`, `RECONNECT`). Arbitrary remote shell execution is strictly blocked.
3. **Hardware Capability Integrity**: Capabilities are probed dynamically via standard browser APIs; simulated or fake capabilities are never reported.
4. **Revocation**: Dashboard operators can revoke any enrolled device via `DELETE /api/v1/devices/{device_id}`, which immediately severs active WebSockets and invalidates authentication tokens.
