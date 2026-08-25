import { useEffect, useRef, useState, useCallback } from "react";
import { api } from "../services/api";

export default function CameraView({ onRecognized, scanIntervalMs = 2500 }) {
  const videoRef = useRef(null);
  const canvasCapture = useRef(document.createElement("canvas"));
  const overlayRef = useRef(null);

  const [result, setResult] = useState(null);
  const [cameraActive, setCameraActive] = useState(false);
  const [cameraError, setCameraError] = useState(null);
  const [isScanning, setIsScanning] = useState(true);

  // تشغيل الكاميرا
  useEffect(() => {
    let stream = null;

    async function startCamera() {
      try {
        setCameraError(null);
        stream = await navigator.mediaDevices.getUserMedia({
          video: {
            width: { ideal: 1280 },
            height: { ideal: 720 },
            facingMode: "user"
          },
          audio: false
        });

        if (videoRef.current) {
          videoRef.current.srcObject = stream;
          setCameraActive(true);
        }
      } catch (err) {
        console.error("Camera access error:", err);
        setCameraError("تعذر الوصول إلى الكاميرا. يرجى التأكد من منح الإذن للمتصفح.");
      }
    }

    startCamera();

    return () => {
      if (stream) {
        stream.getTracks().forEach((track) => track.stop());
      }
    };
  }, []);

  const isProcessingRef = useRef(false);

  // التقاط لقطة وإرسالها للباك إند
  const captureAndSend = useCallback(async () => {
    if (!videoRef.current || !cameraActive || !isScanning) return;
    if (isProcessingRef.current) return; // منع تراكم الطلبات أثناء المعالجة

    const video = videoRef.current;
    if (video.videoWidth === 0 || video.videoHeight === 0) return;

    const canvas = canvasCapture.current;
    canvas.width = Math.min(640, video.videoWidth);
    canvas.height = Math.min(480, video.videoHeight);

    const ctx = canvas.getContext("2d");
    ctx.drawImage(video, 0, 0, canvas.width, canvas.height);

    isProcessingRef.current = true;

    canvas.toBlob(
      async (blob) => {
        if (!blob) {
          isProcessingRef.current = false;
          return;
        }

        const formData = new FormData();
        formData.append("photo", blob, "camera_frame.jpg");

        try {
          const res = await api.post("/recognition/identify", formData);
          setResult(res.data);
          if (onRecognized) {
            onRecognized(res.data);
          }
        } catch (err) {
          console.warn("Recognition ping:", err.message);
        } finally {
          isProcessingRef.current = false;
        }
      },
      "image/jpeg",
      0.8
    );
  }, [cameraActive, isScanning, onRecognized]);

  // تكرار الفحص بفاصل زمني محدد
  useEffect(() => {
    if (!cameraActive || !isScanning) return;
    const interval = setInterval(captureAndSend, scanIntervalMs);
    return () => clearInterval(interval);
  }, [cameraActive, isScanning, scanIntervalMs, captureAndSend]);

  // رسم إطارات الـ HUD والمربعات السيبرانية حول كل وجه
  const drawOverlay = useCallback(() => {
    const canvas = overlayRef.current;
    const video = videoRef.current;
    if (!canvas || !video) return;

    canvas.width = video.clientWidth;
    canvas.height = video.clientHeight;

    const ctx = canvas.getContext("2d");
    ctx.clearRect(0, 0, canvas.width, canvas.height);

    if (!result) return;

    // استخراج قائمة الوجوه
    const facesToDraw = result.faces && result.faces.length > 0
      ? result.faces
      : result.bbox ? [{
          found: result.found,
          score: result.score,
          bbox: result.bbox,
          person: result.person,
          gender: result.gender,
          age: result.age
        }] : [];

    const scaleX = canvas.width / (video.videoWidth || 1);
    const scaleY = canvas.height / (video.videoHeight || 1);

    facesToDraw.forEach((face) => {
      if (!face.bbox) return;

      const x = face.bbox.x * scaleX;
      const y = face.bbox.y * scaleY;
      const w = face.bbox.width * scaleX;
      const h = face.bbox.height * scaleY;

      const isKnown = face.found && face.person;
      const strokeColor = isKnown ? "#00ff99" : "#ff3b5c";
      const bgColor = isKnown ? "rgba(0, 255, 153, 0.15)" : "rgba(255, 59, 92, 0.15)";
      const label = isKnown ? face.person.full_name : "UNKNOWN TARGET";
      const percent = isKnown ? `${(face.score * 100).toFixed(1)}%` : "NO MATCH";

      // خلفية شبه شفافة للمربع
      ctx.fillStyle = bgColor;
      ctx.fillRect(x, y, w, h);

      // رسم زوايا الـ Cyber Box
      const cornerLength = Math.min(24, w / 4, h / 4);
      ctx.lineWidth = 3;
      ctx.strokeStyle = strokeColor;

      // Top-Left
      ctx.beginPath();
      ctx.moveTo(x, y + cornerLength);
      ctx.lineTo(x, y);
      ctx.lineTo(x + cornerLength, y);
      ctx.stroke();

      // Top-Right
      ctx.beginPath();
      ctx.moveTo(x + w - cornerLength, y);
      ctx.lineTo(x + w, y);
      ctx.lineTo(x + w, y + cornerLength);
      ctx.stroke();

      // Bottom-Left
      ctx.beginPath();
      ctx.moveTo(x, y + h - cornerLength);
      ctx.lineTo(x, y + h);
      ctx.lineTo(x + cornerLength, y + h);
      ctx.stroke();

      // Bottom-Right
      ctx.beginPath();
      ctx.moveTo(x + w - cornerLength, y + h);
      ctx.lineTo(x + w, y + h);
      ctx.lineTo(x + w, y + h - cornerLength);
      ctx.stroke();

      // إطار خفيف متصل
      ctx.strokeStyle = isKnown ? "rgba(0, 255, 153, 0.3)" : "rgba(255, 59, 92, 0.3)";
      ctx.lineWidth = 1;
      ctx.strokeRect(x, y, w, h);

      // رسم شريط معلومات علوي (Tag)
      const tagText = `${label} [${percent}]`;
      ctx.font = "bold 13px 'Segoe UI', Consolas, monospace";
      const textMetrics = ctx.measureText(tagText);
      const tagWidth = textMetrics.width + 16;
      const tagHeight = 24;

      ctx.fillStyle = strokeColor;
      ctx.fillRect(x, Math.max(0, y - tagHeight), tagWidth, tagHeight);

      ctx.fillStyle = "#050816";
      ctx.fillText(tagText, x + 8, Math.max(16, y - 7));
    });
  }, [result]);

  useEffect(() => {
    drawOverlay();
  }, [result, drawOverlay]);

  return (
    <div
      style={{
        position: "relative",
        width: "100%",
        height: "100%",
        minHeight: "350px",
        background: "#000000",
        borderRadius: "14px",
        overflow: "hidden",
        display: "flex",
        alignItems: "center",
        justifyContent: "center"
      }}
    >
      {cameraError && (
        <div
          style={{
            position: "absolute",
            zIndex: 10,
            padding: "20px",
            background: "rgba(255, 59, 92, 0.9)",
            color: "#fff",
            borderRadius: "10px",
            textAlign: "center",
            maxWidth: "80%"
          }}
        >
          {cameraError}
        </div>
      )}

      <video
        ref={videoRef}
        autoPlay
        muted
        playsInline
        style={{
          width: "100%",
          height: "100%",
          objectFit: "cover",
          transform: "scaleX(-1)" // مرآة لراحة المستخدم
        }}
      />

      <canvas
        ref={overlayRef}
        style={{
          position: "absolute",
          top: 0,
          left: 0,
          width: "100%",
          height: "100%",
          pointerEvents: "none",
          transform: "scaleX(-1)" // مطابقة المرآة مع الفيديو
        }}
      />

      {/* Cyber HUD Overlay Info */}
      <div
        style={{
          position: "absolute",
          bottom: "12px",
          left: "15px",
          display: "flex",
          gap: "10px",
          alignItems: "center",
          background: "rgba(5, 8, 22, 0.75)",
          backdropFilter: "blur(6px)",
          padding: "6px 14px",
          borderRadius: "8px",
          border: "1px solid rgba(0, 212, 255, 0.3)",
          fontSize: "12px",
          color: "#00d4ff",
          fontFamily: "monospace",
          zIndex: 5
        }}
      >
        <span
          style={{
            display: "inline-block",
            width: "8px",
            height: "8px",
            borderRadius: "50%",
            backgroundColor: isScanning ? "#00ff99" : "#8b9bb4",
            boxShadow: isScanning ? "0 0 8px #00ff99" : "none"
          }}
        />
        <span>EDITH OPTICAL ENGINE {isScanning ? "ACTIVE" : "PAUSED"}</span>
      </div>
    </div>
  );
}