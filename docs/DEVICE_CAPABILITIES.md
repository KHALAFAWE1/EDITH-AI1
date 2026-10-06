# EDITH-AI — Real Device Capabilities & Hardware Detection Matrix

## 1. Zero Fake Data Policy

In strict accordance with the **EDITH-AI Real Data Only** mandate:
* All device capabilities reported to the backend reflect verified, probed hardware APIs on the client browser/device.
* If a hardware feature or API is not supported (e.g. Battery Status API on iOS Safari, Torch API on desktop webcams), the client reports `false` / `null`.
* The dashboard and client interfaces cleanly display `Unavailable` or `N/A`. No synthetic values, simulated battery percentages, or fake IP addresses are generated.

---

## 2. Hardware Capability Matrix

| Hardware Feature | Detection Mechanism | iOS Safari (e.g. iPhone 6) | Android Chrome | Desktop (Chrome / Edge / Firefox) | Smart Glasses HUD |
| :--- | :--- | :--- | :--- | :--- | :--- |
| **Camera (Optical Sensor)** | `navigator.mediaDevices.getUserMedia({video: true})` | ✅ Supported (Front/Rear) | ✅ Supported (Front/Rear) | ✅ Supported (Webcam) | ✅ Supported (Point-of-View) |
| **Microphone (Acoustic Sensor)** | `navigator.mediaDevices.getUserMedia({audio: true})` | ✅ Supported | ✅ Supported | ✅ Supported | ✅ Supported |
| **Battery Level & Charging** | `navigator.getBattery()` | ❌ Not Supported (`Unavailable`) | ✅ Supported | ✅ Supported (Chromium Laptops) | ⚠️ Custom Bridge / SDK |
| **Motion & Gyroscope** | `window.DeviceOrientationEvent` | ✅ Supported (Permission on iOS 13+) | ✅ Supported | ❌ Not Supported (`N/A`) | ✅ Supported (IMU tracking) |
| **Haptic Vibration** | `navigator.vibrate` | ❌ Not Supported (`N/A`) | ✅ Supported | ❌ Not Supported (`N/A`) | ⚠️ Haptic Frame |
| **Flashlight / Torch** | `track.applyConstraints({advanced: [{torch: true}]})` | ⚠️ Limited in Web Safari | ✅ Supported (Rear Cam) | ❌ Not Supported (`N/A`) | ⚠️ High-Intensity LED |
| **Touch Interaction** | `'ontouchstart' in window` | ✅ Supported | ✅ Supported | ⚠️ Touchscreen Only | ❌ Touch Bar / Gesture |
| **Real-time WebSocket** | `window.WebSocket` | ✅ Supported | ✅ Supported | ✅ Supported | ✅ Supported |
| **WebRTC P2P Video** | `window.RTCPeerConnection` | ✅ Supported | ✅ Supported | ✅ Supported | ✅ Supported |

---

## 3. Graceful Feature Degradation

```
                       [Device Initialization]
                                  |
               +------------------+------------------+
               |                                     |
    [Supported Capability]               [Unsupported Capability]
               |                                     |
   Enable Hardware Control               Graceful Degradation:
   (e.g., Active Camera Lens,             Display 'Unavailable' / 'N/A'
    Battery Live Gauge, Haptic)           Disable Control Switch Cleanly
```

1. **Battery Level Handling**:
   * If `navigator.getBattery` is available, client listens to `levelchange` and `chargingchange` events, reporting real 0-100% values.
   * If `navigator.getBattery` is undefined (such as on iOS WebKit), `battery_level` is transmitted as `null`, and UI displays `Battery: Unavailable`.
2. **Camera Constraints**:
   * Client inspects `mediaDevices.enumerateDevices()` to dynamically discover all front (`user`) and rear (`environment`) video inputs.
   * Seamless toggle button is only rendered if multiple video devices exist.
3. **Tactical Vibration**:
   * Vibrate commands received over WebSocket are executed only if `navigator.vibrate` is defined, preventing unhandled exceptions on unsupported devices.
