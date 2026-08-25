import { useState, useEffect, useRef, useCallback } from "react";
import MainLayout from "../layouts/MainLayout";
import { api } from "../services/api";
import { 
  FaRobot, FaEye, FaPaperPlane, FaCamera, FaSpinner, FaMicrochip, 
  FaUser, FaInfoCircle, FaLightbulb, FaKey, FaTimes, FaBolt, 
  FaMicrophone, FaMicrophoneSlash, FaVolumeUp, FaVolumeMute, FaRedo, FaVideo,
  FaBatteryFull, FaHdd, FaMemory, FaSmile, FaVolumeOff, FaBroadcastTower
} from "react-icons/fa";

// محرك المؤثرات الصوتية المستقبلية التكتيكية (Web Audio Synthesizer)
const playCyberSFX = (type = "wake") => {
  try {
    const AudioContext = window.AudioContext || window.webkitAudioContext;
    if (!AudioContext) return;
    const ctx = new AudioContext();
    const osc = ctx.createOscillator();
    const gain = ctx.createGain();
    osc.connect(gain);
    gain.connect(ctx.destination);

    const now = ctx.currentTime;
    if (type === "wake") {
      // نغمة التنبيه والاستجابة عند قول "يا إيديث" (750Hz -> 1450Hz)
      osc.type = "sine";
      osc.frequency.setValueAtTime(750, now);
      osc.frequency.exponentialRampToValueAtTime(1450, now + 0.16);
      gain.gain.setValueAtTime(0.3, now);
      gain.gain.exponentialRampToValueAtTime(0.01, now + 0.2);
      osc.start(now);
      osc.stop(now + 0.2);
    } else if (type === "scan") {
      // مسح راداري بصري
      osc.type = "sawtooth";
      osc.frequency.setValueAtTime(400, now);
      osc.frequency.linearRampToValueAtTime(850, now + 0.22);
      gain.gain.setValueAtTime(0.15, now);
      gain.gain.exponentialRampToValueAtTime(0.01, now + 0.26);
      osc.start(now);
      osc.stop(now + 0.26);
    } else if (type === "confirm") {
      // نغمة تأكيد تنفيذ أوامر Stark Industries
      osc.type = "triangle";
      osc.frequency.setValueAtTime(880, now);
      osc.frequency.setValueAtTime(1320, now + 0.08);
      gain.gain.setValueAtTime(0.25, now);
      gain.gain.exponentialRampToValueAtTime(0.01, now + 0.28);
      osc.start(now);
      osc.stop(now + 0.28);
    } else if (type === "alert") {
      // نغمة تحذير أمني
      osc.type = "square";
      osc.frequency.setValueAtTime(950, now);
      osc.frequency.setValueAtTime(650, now + 0.14);
      gain.gain.setValueAtTime(0.2, now);
      gain.gain.exponentialRampToValueAtTime(0.01, now + 0.26);
      osc.start(now);
      osc.stop(now + 0.26);
    }
  } catch (err) {
    console.log("SFX error:", err);
  }
};

export default function AI() {
  const [activeTab, setActiveTab] = useState("voice_vision"); // "voice_vision" | "chat" | "vision"
  const [aiStatus, setAiStatus] = useState(null);

  // Gemini API Key Modal
  const [isKeyModalOpen, setIsKeyModalOpen] = useState(false);
  const [apiKeyInput, setApiKeyInput] = useState("");
  const [savingKey, setSavingKey] = useState(false);
  const [keyFeedback, setKeyFeedback] = useState("");

  // Chat State
  const [messages, setMessages] = useState([
    {
      role: "assistant",
      content: "مرحباً بك يا فندم! أنا E.D.I.T.H. - المساعد التكتيكي الذكي. تم تزويدي بقدرات التحليل البيومتري، والتعرف على الوجوه، والرؤية الحاسوبية، ومراقبة موارد النظام، والذكاء الاصطناعي الفائق. كيف يمكنني خدمتك اليوم؟"
    }
  ]);
  const [inputPrompt, setInputPrompt] = useState("");
  const [chatLoading, setChatLoading] = useState(false);
  const chatEndRef = useRef(null);

  // Vision State (Upload)
  const [visionPrompt, setVisionPrompt] = useState("قم بوصف محتويات هذه الصورة بالتفصيل واشرح ما تراه باللغة العربية.");
  const [selectedVisionImage, setSelectedVisionImage] = useState(null);
  const [visionPreview, setVisionPreview] = useState(null);
  const [visionResult, setVisionResult] = useState(null);
  const [visionLoading, setVisionLoading] = useState(false);

  // Voice Vision HUD State
  const [videoDevices, setVideoDevices] = useState([]);
  const [selectedDeviceId, setSelectedDeviceId] = useState("");
  const [isListening, setIsListening] = useState(false);
  const [isWakeWordActive, setIsWakeWordActive] = useState(true); // الاستماع المستمر لكلمة "يا إيديث"
  const [wakeWordPulsing, setWakeWordPulsing] = useState(false);
  const [speechTranscript, setSpeechTranscript] = useState("");
  const [voiceProcessing, setVoiceProcessing] = useState(false);
  const [voiceResult, setVoiceResult] = useState(null);
  const [isSpeaking, setIsSpeaking] = useState(false);
  const [autoSpeak, setAutoSpeak] = useState(true);
  const [soundEffectsEnabled, setSoundEffectsEnabled] = useState(true);

  // Live System Telemetry
  const [telemetry, setTelemetry] = useState({
    cpu_percent: 0,
    ram_used_gb: 0,
    ram_total_gb: 8,
    ram_percent: 0,
    disk_percent: 0,
    battery_percent: 100,
    is_charging: true
  });

  const voiceVideoRef = useRef(null);
  const voiceCanvasRef = useRef(document.createElement("canvas"));
  const recognitionRef = useRef(null);
  const wakeWordRecognitionRef = useRef(null);

  // Fetch AI Status & System Telemetry
  const fetchStatus = () => {
    api.get("/ai/status")
      .then((res) => setAiStatus(res.data))
      .catch((err) => console.log("AI status check error:", err));
  };

  const fetchTelemetry = () => {
    api.get("/ai/telemetry")
      .then((res) => {
        if (res.data && !res.data.error) {
          setTelemetry(res.data);
        }
      })
      .catch((err) => console.log("Telemetry check error:", err));
  };

  useEffect(() => {
    fetchStatus();
    fetchTelemetry();
    const interval = setInterval(fetchTelemetry, 4000);
    return () => clearInterval(interval);
  }, []);

  // Enumerate Connected Cameras (Laptop, Bluetooth, USB)
  useEffect(() => {
    async function getDevices() {
      try {
        const devices = await navigator.mediaDevices.enumerateDevices();
        const videoInputs = devices.filter((d) => d.kind === "videoinput");
        setVideoDevices(videoInputs);
        if (videoInputs.length > 0 && !selectedDeviceId) {
          setSelectedDeviceId(videoInputs[0].deviceId);
        }
      } catch (err) {
        console.warn("Could not enumerate video devices:", err);
      }
    }
    getDevices();
  }, [selectedDeviceId]);

  // Start Camera Stream for Voice Vision
  useEffect(() => {
    if (activeTab !== "voice_vision") return;

    let stream = null;
    async function startStream() {
      try {
        const constraints = {
          video: selectedDeviceId ? { deviceId: { exact: selectedDeviceId } } : { facingMode: "user" },
          audio: false
        };
        stream = await navigator.mediaDevices.getUserMedia(constraints);
        if (voiceVideoRef.current) {
          voiceVideoRef.current.srcObject = stream;
        }
      } catch (err) {
        console.error("Voice Camera Stream Error:", err);
      }
    }

    startStream();

    return () => {
      if (stream) {
        stream.getTracks().forEach((track) => track.stop());
      }
    };
  }, [activeTab, selectedDeviceId]);

  // Speech Synthesis Helper
  const speakArabic = useCallback((text) => {
    if (!("speechSynthesis" in window) || !text) return;
    window.speechSynthesis.cancel();

    const utterance = new SpeechSynthesisUtterance(text);
    utterance.lang = "ar-SA";
    utterance.rate = 1.05;
    utterance.pitch = 1.0;

    const voices = window.speechSynthesis.getVoices();
    const arabicVoice = voices.find((v) => v.lang.startsWith("ar"));
    if (arabicVoice) {
      utterance.voice = arabicVoice;
    }

    utterance.onstart = () => setIsSpeaking(true);
    utterance.onend = () => setIsSpeaking(false);
    utterance.onerror = () => setIsSpeaking(false);

    window.speechSynthesis.speak(utterance);
  }, []);

  // Capture Frame and Send to Voice-Vision Assistant
  const triggerVoiceVisionCapture = useCallback(async (promptText) => {
    if (soundEffectsEnabled) playCyberSFX("scan");

    let blobToSend = null;
    if (voiceVideoRef.current && voiceVideoRef.current.videoWidth > 0) {
      const video = voiceVideoRef.current;
      const canvas = voiceCanvasRef.current;
      canvas.width = Math.min(800, video.videoWidth);
      canvas.height = Math.min(600, video.videoHeight);
      const ctx = canvas.getContext("2d");
      ctx.drawImage(video, 0, 0, canvas.width, canvas.height);
      blobToSend = await new Promise((resolve) => canvas.toBlob(resolve, "image/jpeg", 0.85));
    }

    setVoiceProcessing(true);
    setVoiceResult(null);

    const formData = new FormData();
    formData.append("voice_prompt", promptText || "إيه اللي قدامي ده ومين موجود في الكاميرا؟");
    if (blobToSend) {
      formData.append("photo", blobToSend, "voice_frame.jpg");
    }

    try {
      const res = await api.post("/ai/voice-vision", formData);
      setVoiceResult(res.data);
      if (res.data.telemetry) setTelemetry(res.data.telemetry);

      if (soundEffectsEnabled) {
        if (res.data.detected_names && res.data.detected_names.length > 0) {
          playCyberSFX("confirm");
        } else if (res.data.client_action) {
          playCyberSFX("confirm");
        }
      }

      if (autoSpeak && res.data.spoken_text) {
        speakArabic(res.data.spoken_text);
      }
    } catch (err) {
      console.error(err);
      const errorMsg = "حدث خطأ أثناء فحص المشهد.";
      setVoiceResult({ success: false, spoken_text: errorMsg });
      if (soundEffectsEnabled) playCyberSFX("alert");
      if (autoSpeak) speakArabic(errorMsg);
    } finally {
      setVoiceProcessing(false);
    }
  }, [autoSpeak, speakArabic, soundEffectsEnabled]);

  // Continuous Wake Word Listener ("يا إيديث" / "Hey EDITH")
  useEffect(() => {
    const SpeechRecognition = window.SpeechRecognition || window.webkitSpeechRecognition;
    if (!SpeechRecognition || !isWakeWordActive || activeTab !== "voice_vision") return;

    let wakeRecognition = null;
    let isStopped = false;

    try {
      wakeRecognition = new SpeechRecognition();
      wakeRecognition.lang = "ar-EG";
      wakeRecognition.continuous = true;
      wakeRecognition.interimResults = true;

      wakeRecognition.onresult = (event) => {
        const lastResult = event.results[event.results.length - 1];
        const transcript = lastResult[0].transcript.trim().toLowerCase();

        // فحص هل نطق المستخدم كلمة التنبيه (يا إيديث / إيديث / Hey EDITH)
        const wakeWordMatches = ["يا إيديث", "إيديث", "يا ايديث", "ايديث", "hey edith", "edith"];
        const matched = wakeWordMatches.some((w) => transcript.includes(w));

        if (matched) {
          // تشغيل صوت التنبيه المستقبلي فوراً
          if (soundEffectsEnabled) playCyberSFX("wake");
          setWakeWordPulsing(true);
          setTimeout(() => setWakeWordPulsing(false), 2000);

          // تنظيف كلمة التنبيه واستخراج الأمر
          let command = transcript;
          wakeWordMatches.forEach((w) => {
            command = command.replace(w, "").trim();
          });

          if (!command) {
            command = "ما هي حالة النظام والوضع الحالي؟";
          }

          setSpeechTranscript(`🎙️ أمر صوتي: "${command}"`);
          triggerVoiceVisionCapture(command);
        }
      };

      wakeRecognition.onerror = (e) => {
        if (!isStopped && isWakeWordActive) {
          try { wakeRecognition.start(); } catch (_) {}
        }
      };

      wakeRecognition.onend = () => {
        if (!isStopped && isWakeWordActive) {
          try { wakeRecognition.start(); } catch (_) {}
        }
      };

      wakeRecognition.start();
      wakeWordRecognitionRef.current = wakeRecognition;
    } catch (err) {
      console.log("Wake word listener init error:", err);
    }

    return () => {
      isStopped = true;
      try {
        wakeRecognition?.stop();
      } catch (_) {}
    };
  }, [isWakeWordActive, activeTab, soundEffectsEnabled, triggerVoiceVisionCapture]);

  // Speech Recognition (Microphone Listener)
  const toggleVoiceListening = () => {
    const SpeechRecognition = window.SpeechRecognition || window.webkitSpeechRecognition;

    if (!SpeechRecognition) {
      alert("متصفحك لا يدعم التعرف الصوتي المباشر. يمكنك كتابة السؤال أو استخدام متصفح Google Chrome / Microsoft Edge.");
      return;
    }

    if (isListening) {
      recognitionRef.current?.stop();
      setIsListening(false);
      return;
    }

    window.speechSynthesis.cancel();
    setIsSpeaking(false);

    const recognition = new SpeechRecognition();

    recognition.lang = "ar-EG";
    recognition.interimResults = true;
    recognition.continuous = false;

    recognition.onstart = () => {
      setIsListening(true);
      setSpeechTranscript("جاري الاستماع لصوتك الآن...");
    };

    recognition.onresult = (event) => {
      const currentTranscript = Array.from(event.results)
        .map((r) => r[0].transcript)
        .join("");
      setSpeechTranscript(currentTranscript);
    };

    recognition.onerror = (err) => {
      console.warn("Speech Recognition Error:", err);
      setIsListening(false);
    };

    recognition.onend = () => {
      setIsListening(false);
      setSpeechTranscript((finalTranscript) => {
        if (finalTranscript && finalTranscript !== "جاري الاستماع لصوتك الآن..." && finalTranscript.trim().length > 1) {
          triggerVoiceVisionCapture(finalTranscript);
        }
        return finalTranscript;
      });
    };

    recognitionRef.current = recognition;
    recognition.start();
  };

  // Auto-scroll chat
  useEffect(() => {
    chatEndRef.current?.scrollIntoView({ behavior: "smooth" });
  }, [messages]);

  // Handle Save Gemini API Key
  const handleSaveKey = async (e) => {
    e.preventDefault();
    if (!apiKeyInput.trim()) return;

    try {
      setSavingKey(true);
      setKeyFeedback("");
      const res = await api.post("/ai/set-key", { api_key: apiKeyInput });
      if (res.data.success) {
        setKeyFeedback("تم حفظ وتفعيل محرك Google Gemini بنجاح دائم!");
        fetchStatus();
        setTimeout(() => {
          setIsKeyModalOpen(false);
          setKeyFeedback("");
          setApiKeyInput("");
        }, 1200);
      }
    } catch (err) {
      setKeyFeedback("فشل حفظ المفتاح: " + (err.response?.data?.detail || err.message));
    } finally {
      setSavingKey(false);
    }
  };

  // Handle Send Chat
  const handleSendMessage = async (customText = null) => {
    const textToSend = customText || inputPrompt;
    if (!textToSend.trim() || chatLoading) return;

    const userMessage = { role: "user", content: textToSend };
    setMessages((prev) => [...prev, userMessage]);
    if (!customText) setInputPrompt("");
    setChatLoading(true);

    try {
      const res = await api.post("/ai/chat", {
        prompt: textToSend,
        history: messages
      });

      setMessages((prev) => [
        ...prev,
        {
          role: "assistant",
          content: res.data.reply || "EDITH Core generated no response.",
          engine: res.data.engine
        }
      ]);
    } catch (err) {
      console.error(err);
      setMessages((prev) => [
        ...prev,
        {
          role: "assistant",
          content: "Tactical Link Error: تعذر الاتصال بمحرك الذكاء الاصطناعي. تأكد من إدخال مفتاح Gemini."
        }
      ]);
    } finally {
      setChatLoading(false);
    }
  };

  // Handle Vision File Selection
  const handleVisionFile = (e) => {
    const file = e.target.files[0];
    if (file) {
      setSelectedVisionImage(file);
      const reader = new FileReader();
      reader.onloadend = () => setVisionPreview(reader.result);
      reader.readAsDataURL(file);
    }
  };

  // Handle Vision Upload Analysis
  const handleAnalyzeVision = async () => {
    if (!selectedVisionImage) {
      alert("يرجى اختيار صورة للتحليل");
      return;
    }

    setVisionLoading(true);
    setVisionResult(null);

    const formData = new FormData();
    formData.append("prompt", visionPrompt);
    formData.append("photo", selectedVisionImage);

    try {
      const res = await api.post("/ai/vision", formData);
      setVisionResult(res.data);
    } catch (err) {
      console.error(err);
      setVisionResult({
        success: false,
        message: "Failed to analyze image with vision engine. Check your API key or network connection."
      });
    } finally {
      setVisionLoading(false);
    }
  };

  const isGeminiActive = aiStatus?.has_gemini_key;

  return (
    <MainLayout>
      {/* Header with Mode Switcher & API Key Config */}
      <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center", marginBottom: "20px" }}>
        <div>
          <h1 className="title" style={{ display: "flex", alignItems: "center", gap: "10px" }}>
            <FaRobot style={{ color: "#00d4ff" }} /> EDITH Tactical Intelligence Hub
          </h1>
          <p className="subtitle">
            Voice-Activated Multi-Modal Assistant & Biometric Optical AI Engine
          </p>
        </div>

        <div style={{ display: "flex", gap: "12px", alignItems: "center" }}>
          {/* Configure Key Button */}
          <button
            onClick={() => setIsKeyModalOpen(true)}
            style={{
              background: isGeminiActive ? "rgba(0, 255, 153, 0.15)" : "linear-gradient(135deg, #00d4ff 0%, #0077ff 100%)",
              color: isGeminiActive ? "#00ff99" : "#050816",
              border: isGeminiActive ? "1px solid rgba(0, 255, 153, 0.4)" : "none",
              borderRadius: "10px",
              padding: "10px 16px",
              fontWeight: 700,
              fontSize: "13px",
              display: "flex",
              alignItems: "center",
              gap: "8px",
              cursor: "pointer",
              boxShadow: isGeminiActive ? "none" : "0 4px 15px rgba(0, 212, 255, 0.3)"
            }}
          >
            <FaKey size={13} /> {isGeminiActive ? "Gemini 3.5 Active ⚡" : "Set Gemini API Key 🔑"}
          </button>

          {/* Mode Switcher (3 Tabs) */}
          <div style={{ display: "flex", gap: "6px", background: "#111827", padding: "4px", borderRadius: "12px", border: "1px solid rgba(0, 212, 255, 0.2)" }}>
            <button
              onClick={() => setActiveTab("voice_vision")}
              style={{
                background: activeTab === "voice_vision" ? "linear-gradient(135deg, #00d4ff 0%, #0077ff 100%)" : "transparent",
                color: activeTab === "voice_vision" ? "#050816" : "#8b9bb4",
                border: "none",
                borderRadius: "8px",
                padding: "8px 14px",
                fontWeight: 700,
                fontSize: "13px",
                display: "flex",
                alignItems: "center",
                gap: "6px",
                cursor: "pointer"
              }}
            >
              <FaMicrophone size={13} /> Voice Vision Assistant
            </button>
            <button
              onClick={() => setActiveTab("chat")}
              style={{
                background: activeTab === "chat" ? "#00d4ff" : "transparent",
                color: activeTab === "chat" ? "#050816" : "#8b9bb4",
                border: "none",
                borderRadius: "8px",
                padding: "8px 14px",
                fontWeight: 700,
                fontSize: "13px",
                display: "flex",
                alignItems: "center",
                gap: "6px",
                cursor: "pointer"
              }}
            >
              <FaRobot size={13} /> Tactical Chat
            </button>
            <button
              onClick={() => setActiveTab("vision")}
              style={{
                background: activeTab === "vision" ? "#00d4ff" : "transparent",
                color: activeTab === "vision" ? "#050816" : "#8b9bb4",
                border: "none",
                borderRadius: "8px",
                padding: "8px 14px",
                fontWeight: 700,
                fontSize: "13px",
                display: "flex",
                alignItems: "center",
                gap: "6px",
                cursor: "pointer"
              }}
            >
              <FaEye size={13} /> Vision Lab
            </button>
          </div>
        </div>
      </div>

      {/* MODE 1: Voice Vision Assistant (Requested Feature!) */}
      {activeTab === "voice_vision" && (
        <div style={{ display: "grid", gridTemplateColumns: "1.2fr 1fr", gap: "25px", height: "calc(100vh - 190px)" }}>
          {/* Live Camera + Voice Trigger HUD */}
          <div
            style={{
              background: "#111827",
              borderRadius: "16px",
              border: "1px solid rgba(0, 212, 255, 0.2)",
              padding: "20px",
              display: "flex",
              flexDirection: "column",
              gap: "16px",
              position: "relative"
            }}
          >
            {/* Top Bar: Camera Selector, Telemetry Quick Status & SFX Toggle */}
            <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center", flexWrap: "wrap", gap: "10px" }}>
              <div style={{ display: "flex", alignItems: "center", gap: "8px" }}>
                <FaVideo color="#00d4ff" />
                <select
                  value={selectedDeviceId}
                  onChange={(e) => setSelectedDeviceId(e.target.value)}
                  style={{
                    background: "#192033",
                    color: "#fff",
                    border: "1px solid rgba(0, 212, 255, 0.3)",
                    borderRadius: "8px",
                    padding: "6px 10px",
                    fontSize: "12px",
                    outline: "none",
                    cursor: "pointer"
                  }}
                >
                  {videoDevices.map((dev, idx) => (
                    <option key={dev.deviceId || idx} value={dev.deviceId}>
                      {dev.label || `Optical Sensor #${idx + 1}`}
                    </option>
                  ))}
                </select>
              </div>

              {/* Toggles: Wake Word & Cyber SFX */}
              <div style={{ display: "flex", alignItems: "center", gap: "10px" }}>
                <button
                  onClick={() => setIsWakeWordActive(!isWakeWordActive)}
                  style={{
                    background: isWakeWordActive ? "rgba(0, 212, 255, 0.15)" : "#192033",
                    border: isWakeWordActive ? "1px solid #00d4ff" : "1px solid rgba(255, 255, 255, 0.1)",
                    color: isWakeWordActive ? "#00d4ff" : "#8b9bb4",
                    borderRadius: "8px",
                    padding: "5px 10px",
                    fontSize: "11px",
                    fontWeight: 700,
                    cursor: "pointer",
                    display: "flex",
                    alignItems: "center",
                    gap: "6px"
                  }}
                  title="الاستماع التلقائي في الخلفية لكلمة «يا إيديث»"
                >
                  <FaBroadcastTower /> {isWakeWordActive ? "Wake Word: «يا إيديث» مفعّل 🎙️" : "Wake Word: معطل"}
                </button>

                <button
                  onClick={() => setSoundEffectsEnabled(!soundEffectsEnabled)}
                  style={{
                    background: soundEffectsEnabled ? "rgba(0, 255, 153, 0.15)" : "#192033",
                    border: soundEffectsEnabled ? "1px solid #00ff99" : "1px solid rgba(255, 255, 255, 0.1)",
                    color: soundEffectsEnabled ? "#00ff99" : "#8b9bb4",
                    borderRadius: "8px",
                    padding: "5px 10px",
                    fontSize: "11px",
                    fontWeight: 700,
                    cursor: "pointer",
                    display: "flex",
                    alignItems: "center",
                    gap: "5px"
                  }}
                >
                  {soundEffectsEnabled ? <FaVolumeUp /> : <FaVolumeOff />}
                  {soundEffectsEnabled ? "SFX أصوات تكتيكية" : "كتم المؤثرات"}
                </button>
              </div>
            </div>

            {/* Live System Telemetry HUD Mini-Bar */}
            <div style={{ display: "grid", gridTemplateColumns: "repeat(4, 1fr)", gap: "8px", background: "#0d1222", padding: "10px 14px", borderRadius: "10px", border: "1px solid rgba(0, 212, 255, 0.15)" }}>
              <div style={{ display: "flex", alignItems: "center", gap: "8px" }}>
                <FaBolt color="#00d4ff" size={13} />
                <div>
                  <div style={{ fontSize: "10px", color: "#8b9bb4", textTransform: "uppercase" }}>CPU Load</div>
                  <div style={{ fontSize: "12px", color: telemetry.cpu_percent > 70 ? "#ff3b5c" : "#00d4ff", fontWeight: 700 }}>
                    {telemetry.cpu_percent}%
                  </div>
                </div>
              </div>

              <div style={{ display: "flex", alignItems: "center", gap: "8px" }}>
                <FaMemory color="#00ff99" size={13} />
                <div>
                  <div style={{ fontSize: "10px", color: "#8b9bb4", textTransform: "uppercase" }}>RAM Usage</div>
                  <div style={{ fontSize: "12px", color: "#00ff99", fontWeight: 700 }}>
                    {telemetry.ram_used_gb} / {telemetry.ram_total_gb} GB
                  </div>
                </div>
              </div>

              <div style={{ display: "flex", alignItems: "center", gap: "8px" }}>
                <FaBatteryFull color="#ffd700" size={13} />
                <div>
                  <div style={{ fontSize: "10px", color: "#8b9bb4", textTransform: "uppercase" }}>Power & Battery</div>
                  <div style={{ fontSize: "12px", color: "#ffd700", fontWeight: 700 }}>
                    {telemetry.battery_percent}% {telemetry.is_charging ? "⚡" : ""}
                  </div>
                </div>
              </div>

              <div style={{ display: "flex", alignItems: "center", gap: "8px" }}>
                <FaHdd color="#b388ff" size={13} />
                <div>
                  <div style={{ fontSize: "10px", color: "#8b9bb4", textTransform: "uppercase" }}>Storage Disk</div>
                  <div style={{ fontSize: "12px", color: "#b388ff", fontWeight: 700 }}>
                    {telemetry.disk_percent}%
                  </div>
                </div>
              </div>
            </div>

            {/* Live Camera View Box */}
            <div
              style={{
                flex: 1,
                minHeight: "240px",
                background: "#000",
                borderRadius: "14px",
                overflow: "hidden",
                position: "relative",
                display: "flex",
                alignItems: "center",
                justifyContent: "center",
                border: wakeWordPulsing ? "2px solid #ffd700" : "1px solid rgba(0, 212, 255, 0.2)",
                boxShadow: wakeWordPulsing ? "0 0 30px rgba(255, 215, 0, 0.6)" : "none",
                transition: "all 0.3s"
              }}
            >
              <video
                ref={voiceVideoRef}
                autoPlay
                muted
                playsInline
                style={{ width: "100%", height: "100%", objectFit: "cover", transform: "scaleX(-1)" }}
              />

              {/* Futuristic Cyber Overlay Grid */}
              <div
                style={{
                  position: "absolute",
                  inset: 0,
                  pointerEvents: "none",
                  border: "2px solid rgba(0, 212, 255, 0.15)",
                  background: "radial-gradient(circle, transparent 60%, rgba(0, 212, 255, 0.05) 100%)"
                }}
              />

              {/* Wake Word Visual Trigger Pulse Banner */}
              {wakeWordPulsing && (
                <div
                  style={{
                    position: "absolute",
                    top: "15px",
                    background: "rgba(255, 215, 0, 0.9)",
                    color: "#050816",
                    padding: "8px 18px",
                    borderRadius: "20px",
                    fontWeight: 900,
                    fontSize: "13px",
                    display: "flex",
                    alignItems: "center",
                    gap: "8px",
                    boxShadow: "0 0 20px #ffd700"
                  }}
                >
                  <FaBolt /> E.D.I.T.H. WAKE TRIGGER ACTIVATED!
                </div>
              )}

              {/* Status Badge Over Video */}
              {voiceProcessing && (
                <div
                  style={{
                    position: "absolute",
                    background: "rgba(5, 8, 22, 0.85)",
                    backdropFilter: "blur(6px)",
                    padding: "12px 24px",
                    borderRadius: "12px",
                    border: "1px solid #00d4ff",
                    color: "#00d4ff",
                    display: "flex",
                    alignItems: "center",
                    gap: "10px",
                    fontSize: "14px",
                    fontWeight: 700
                  }}
                >
                  <FaSpinner className="spin" /> E.D.I.T.H. Analyzing Scene, Telemetry & Biometrics...
                </div>
              )}
            </div>

            {/* Voice Command Orb & Quick Trigger Bar */}
            <div style={{ background: "#192033", borderRadius: "14px", padding: "16px", display: "flex", flexDirection: "column", gap: "12px" }}>
              <div style={{ display: "flex", alignItems: "center", gap: "16px" }}>
                {/* Voice Orb Button */}
                <button
                  onClick={toggleVoiceListening}
                  disabled={voiceProcessing}
                  style={{
                    width: "60px",
                    height: "60px",
                    borderRadius: "50%",
                    background: isListening ? "radial-gradient(circle, #ff3b5c 0%, #aa0022 100%)" : "radial-gradient(circle, #00d4ff 0%, #0055ff 100%)",
                    border: isListening ? "3px solid #ff3b5c" : "3px solid #00d4ff",
                    boxShadow: isListening ? "0 0 25px #ff3b5c" : "0 0 20px rgba(0, 212, 255, 0.5)",
                    color: "#fff",
                    display: "flex",
                    alignItems: "center",
                    justifyContent: "center",
                    cursor: "pointer",
                    fontSize: "22px",
                    transition: "all 0.2s",
                    flexShrink: 0
                  }}
                  title={isListening ? "انقر للإيقاف والإرسال" : "انقر وتحدث بالصوت"}
                >
                  {isListening ? <FaMicrophoneSlash /> : <FaMicrophone />}
                </button>

                <div style={{ flex: 1 }}>
                  <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center" }}>
                    <span style={{ fontSize: "12px", color: isListening ? "#ff3b5c" : "#00d4ff", fontWeight: 700 }}>
                      {isListening ? "🔴 جاري الاستماع لصوتك الآن (تحدث)..." : (isWakeWordActive ? "🎙️ قل «يا إيديث» في أي وقت أو اضغط على المايك" : "المساعد الصوتي البصري جاهز")}
                    </span>
                    <button
                      onClick={() => setAutoSpeak(!autoSpeak)}
                      style={{
                        background: "none",
                        border: "none",
                        color: autoSpeak ? "#00ff99" : "#8b9bb4",
                        cursor: "pointer",
                        fontSize: "12px",
                        display: "flex",
                        alignItems: "center",
                        gap: "4px"
                      }}
                    >
                      {autoSpeak ? <FaVolumeUp /> : <FaVolumeMute />}
                      {autoSpeak ? "النطق الصوتي مفعّل" : "صامت"}
                    </button>
                  </div>
                  <p style={{ color: "#fff", fontSize: "13px", margin: "4px 0 0 0", minHeight: "18px" }}>
                    {speechTranscript || "قل «يا إيديث ما هي حالة النظام؟» أو «يا إيديث إيه اللي قدامي؟»"}
                  </p>
                </div>
              </div>

              {/* Quick Voice Shortcut Buttons */}
              <div style={{ display: "flex", gap: "8px", overflowX: "auto", paddingBottom: "4px", scrollbarWidth: "thin" }}>
                {[
                  "يا إيديث، ما هي حالة موارد الجهاز والنظام؟",
                  "إيه اللي قدامي ده وما هي المشاعر الظاهرة؟",
                  "افتح اليوتيوب",
                  "افتح الآلة الحاسبة",
                  "اقفل الآلة الحاسبة",
                  "اتصل على 01099887766",
                  "احكي لي معلومة ذكية عن الكون"
                ].map((txt, idx) => (
                  <button
                    key={idx}
                    onClick={() => {
                      setSpeechTranscript(txt);
                      triggerVoiceVisionCapture(txt);
                    }}
                    disabled={voiceProcessing}
                    style={{
                      background: "rgba(255, 255, 255, 0.05)",
                      border: "1px solid rgba(0, 212, 255, 0.25)",
                      borderRadius: "8px",
                      color: "#00d4ff",
                      padding: "7px 12px",
                      fontSize: "12px",
                      fontWeight: 600,
                      cursor: "pointer",
                      whiteSpace: "nowrap",
                      transition: "all 0.2s"
                    }}
                    onMouseOver={(e) => {
                      e.currentTarget.style.borderColor = "#00ff99";
                      e.currentTarget.style.color = "#00ff99";
                    }}
                    onMouseOut={(e) => {
                      e.currentTarget.style.borderColor = "rgba(0, 212, 255, 0.25)";
                      e.currentTarget.style.color = "#00d4ff";
                    }}
                  >
                    ⚡ {txt}
                  </button>
                ))}
              </div>
            </div>
          </div>


          {/* Voice Response & Biometric Profile Output */}
          <div
            style={{
              background: "#111827",
              borderRadius: "16px",
              border: "1px solid rgba(0, 255, 153, 0.25)",
              padding: "24px",
              display: "flex",
              flexDirection: "column",
              gap: "18px",
              boxShadow: "0 10px 30px rgba(0,0,0,0.4)",
              overflowY: "auto"
            }}
          >
            <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center" }}>
              <h2 style={{ fontSize: "17px", color: "#fff", margin: 0, display: "flex", alignItems: "center", gap: "8px" }}>
                <FaVolumeUp color="#00ff99" /> رد إيديث الصوتي التفاعلي
              </h2>
              {voiceResult?.spoken_text && (
                <button
                  onClick={() => speakArabic(voiceResult.spoken_text)}
                  style={{
                    background: "rgba(0, 255, 153, 0.15)",
                    color: "#00ff99",
                    border: "1px solid rgba(0, 255, 153, 0.3)",
                    borderRadius: "8px",
                    padding: "6px 12px",
                    fontSize: "12px",
                    display: "flex",
                    alignItems: "center",
                    gap: "6px",
                    cursor: "pointer"
                  }}
                >
                  <FaRedo size={10} /> إعادة النطق
                </button>
              )}
            </div>

            {/* Client Action Alert Banner */}
            {voiceResult?.client_action && (
              <div
                style={{
                  background: "rgba(0, 212, 255, 0.15)",
                  border: "1px solid #00d4ff",
                  borderRadius: "10px",
                  padding: "12px 16px",
                  display: "flex",
                  justifyContent: "space-between",
                  alignItems: "center"
                }}
              >
                <div style={{ color: "#00d4ff", fontSize: "13px", fontWeight: 700 }}>
                  🚀 تم تنفيذ الإجراء التفاعلي: {voiceResult.client_action.type === "call" ? "إجراء اتصال" : "فتح الرابط"}
                </div>
                {voiceResult.client_action.url && (
                  <a
                    href={voiceResult.client_action.url}
                    target="_blank"
                    rel="noreferrer"
                    style={{
                      background: "#00d4ff",
                      color: "#050816",
                      padding: "6px 12px",
                      borderRadius: "6px",
                      fontSize: "12px",
                      fontWeight: 700,
                      textDecoration: "none"
                    }}
                  >
                    الانتقال فوراً ↗
                  </a>
                )}
              </div>
            )}

            {/* Identified Persons Badges */}
            {voiceResult?.detected_names && voiceResult.detected_names.length > 0 && (
              <div style={{ background: "rgba(0, 255, 153, 0.1)", border: "1px solid #00ff99", borderRadius: "10px", padding: "12px" }}>
                <div style={{ fontSize: "12px", color: "#00ff99", fontWeight: 700, marginBottom: "6px" }}>
                  👤 تم التعرف على الهوية البيومترية:
                </div>
                <div style={{ display: "flex", gap: "6px", flexWrap: "wrap" }}>
                  {voiceResult.detected_names.map((name, i) => (
                    <span key={i} className="badge badge-green" style={{ fontSize: "12px", padding: "4px 10px" }}>
                      ✓ {name}
                    </span>
                  ))}
                </div>
              </div>
            )}

            {/* Audio Waveform / Talking Indicator */}
            {isSpeaking && (
              <div style={{ display: "flex", alignItems: "center", gap: "10px", color: "#00d4ff", fontSize: "13px", padding: "10px", background: "rgba(0, 212, 255, 0.08)", borderRadius: "8px" }}>
                <FaVolumeUp className="pulse" />
                <span>إيديث تتحدث الآن في مكبرات الصوت...</span>
              </div>
            )}

            {/* Main Spoken Narrative Box */}
            <div
              style={{
                flex: 1,
                background: "#192033",
                borderRadius: "14px",
                border: "1px solid rgba(255, 255, 255, 0.08)",
                padding: "20px",
                display: "flex",
                flexDirection: "column",
                gap: "12px",
                minHeight: "180px"
              }}
            >
              <div style={{ fontSize: "12px", color: "#8b9bb4", textTransform: "uppercase", letterSpacing: "0.5px" }}>
                التحليل الصوتي التكتيكي
              </div>

              {!voiceResult && !voiceProcessing && (
                <div style={{ textAlign: "center", padding: "40px 0", color: "#8b9bb4" }}>
                  <FaMicrophone size={38} color="#00d4ff" style={{ marginBottom: "12px" }} />
                  <p style={{ margin: 0, fontSize: "13px" }}>
                    تحدث بصوتك واسأل عن أي شيء، أو اطلب: «افتح اليوتيوب»، «افتح الآلة الحاسبة»، «اتصل على فلان»، «اقفل كذا»!
                  </p>
                </div>
              )}

              {voiceProcessing && (
                <div style={{ textAlign: "center", padding: "40px 0", color: "#00d4ff" }}>
                  <FaSpinner className="spin" size={36} style={{ marginBottom: "12px" }} />
                  <p style={{ margin: 0, fontSize: "13px" }}>جاري معالجة الأمر الصوتي وتنفيذ الإجراء...</p>
                </div>
              )}

              {voiceResult && (
                <p style={{ color: "#f3f4f6", fontSize: "15px", lineHeight: "1.7", margin: 0, whiteSpace: "pre-wrap" }}>
                  {voiceResult.spoken_text}
                </p>
              )}
            </div>

            {/* Prompt Recall */}
            {voiceResult?.prompt && (
              <div style={{ fontSize: "12px", color: "#8b9bb4", background: "rgba(0,0,0,0.2)", padding: "8px 12px", borderRadius: "6px" }}>
                <strong>أمرك الصوتي:</strong> "{voiceResult.prompt}"
              </div>
            )}
          </div>
        </div>
      )}

      {/* MODE 2: Tactical AI Chat */}
      {activeTab === "chat" && (
        <div style={{ display: "grid", gridTemplateColumns: "1fr 320px", gap: "20px", height: "calc(100vh - 190px)" }}>
          {/* Main Chat Stream */}
          <div
            style={{
              background: "#111827",
              borderRadius: "16px",
              border: "1px solid rgba(0, 212, 255, 0.15)",
              display: "flex",
              flexDirection: "column",
              overflow: "hidden",
              boxShadow: "0 10px 30px rgba(0,0,0,0.4)"
            }}
          >
            {/* Messages Container */}
            <div style={{ flex: 1, padding: "20px", overflowY: "auto", display: "flex", flexDirection: "column", gap: "16px" }}>
              {messages.map((msg, idx) => (
                <div
                  key={idx}
                  style={{
                    display: "flex",
                    gap: "12px",
                    alignSelf: msg.role === "user" ? "flex-end" : "flex-start",
                    maxWidth: "85%"
                  }}
                >
                  {msg.role === "assistant" && (
                    <div
                      style={{
                        width: "38px",
                        height: "38px",
                        borderRadius: "10px",
                        background: "rgba(0, 212, 255, 0.15)",
                        border: "1px solid #00d4ff",
                        display: "flex",
                        alignItems: "center",
                        justifyContent: "center",
                        color: "#00d4ff",
                        flexShrink: 0
                      }}
                    >
                      <FaRobot size={18} />
                    </div>
                  )}

                  <div
                    style={{
                      background: msg.role === "user" ? "linear-gradient(135deg, #0077ff 0%, #00d4ff 100%)" : "#192033",
                      color: msg.role === "user" ? "#ffffff" : "#f3f4f6",
                      padding: "14px 18px",
                      borderRadius: msg.role === "user" ? "14px 14px 2px 14px" : "14px 14px 14px 2px",
                      border: msg.role === "assistant" ? "1px solid rgba(255, 255, 255, 0.08)" : "none",
                      fontSize: "14px",
                      lineHeight: "1.6",
                      whiteSpace: "pre-wrap"
                    }}
                  >
                    {msg.content}
                    {msg.engine && (
                      <div style={{ marginTop: "8px", fontSize: "11px", color: "#00d4ff", fontFamily: "monospace" }}>
                        ⚡ {msg.engine}
                      </div>
                    )}
                  </div>

                  {msg.role === "user" && (
                    <div
                      style={{
                        width: "38px",
                        height: "38px",
                        borderRadius: "10px",
                        background: "#0077ff",
                        display: "flex",
                        alignItems: "center",
                        justifyContent: "center",
                        color: "#fff",
                        flexShrink: 0
                      }}
                    >
                      <FaUser size={16} />
                    </div>
                  )}
                </div>
              ))}

              {chatLoading && (
                <div style={{ display: "flex", gap: "12px", alignItems: "center", color: "#00d4ff", fontSize: "13px" }}>
                  <FaSpinner className="spin" /> E.D.I.T.H. is computing tactical response...
                </div>
              )}
              <div ref={chatEndRef} />
            </div>

            {/* Input Bar */}
            <div style={{ padding: "16px", background: "#0d1222", borderTop: "1px solid rgba(255, 255, 255, 0.06)", display: "flex", gap: "12px" }}>
              <input
                type="text"
                placeholder="تحدث مع إيديث (اطلب تنفيذ أوامر: افتح برنامج، احذف ملف، اسأل عن أي شيء)..."
                value={inputPrompt}
                onChange={(e) => setInputPrompt(e.target.value)}
                onKeyDown={(e) => e.key === "Enter" && handleSendMessage()}
                style={{
                  flex: 1,
                  background: "#192033",
                  border: "1px solid rgba(0, 212, 255, 0.2)",
                  borderRadius: "10px",
                  padding: "12px 16px",
                  color: "#fff",
                  outline: "none",
                  fontSize: "14px"
                }}
              />
              <button
                onClick={() => handleSendMessage()}
                disabled={chatLoading || !inputPrompt.trim()}
                style={{
                  background: "linear-gradient(135deg, #00d4ff 0%, #0077ff 100%)",
                  color: "#050816",
                  border: "none",
                  borderRadius: "10px",
                  padding: "0 22px",
                  cursor: chatLoading || !inputPrompt.trim() ? "not-allowed" : "pointer",
                  display: "flex",
                  alignItems: "center",
                  justifyContent: "center",
                  opacity: chatLoading || !inputPrompt.trim() ? 0.6 : 1
                }}
              >
                <FaPaperPlane size={16} />
              </button>
            </div>
          </div>

          {/* Quick Prompts & AI Telemetry Sidebar */}
          <div style={{ display: "flex", flexDirection: "column", gap: "18px" }}>
            <div style={{ background: "#111827", borderRadius: "16px", border: "1px solid rgba(0, 212, 255, 0.15)", padding: "18px" }}>
              <h3 style={{ fontSize: "14px", color: "#fff", marginBottom: "12px", display: "flex", alignItems: "center", gap: "8px" }}>
                <FaBolt color="#00d4ff" /> Active Intelligence Engine
              </h3>
              <div style={{ fontSize: "13px", color: "#8b9bb4", display: "flex", flexDirection: "column", gap: "8px" }}>
                <div style={{ display: "flex", justifyContent: "space-between" }}>
                  <span>Engine:</span>
                  <strong style={{ color: "#00ff99" }}>Google Gemini 3.5 Flash</strong>
                </div>
                <div style={{ display: "flex", justifyContent: "space-between" }}>
                  <span>System Control:</span>
                  <strong style={{ color: "#00d4ff" }}>Enabled (Live OS Execution)</strong>
                </div>
                <div style={{ display: "flex", justifyContent: "space-between" }}>
                  <span>Status:</span>
                  <span className="badge badge-green">PERMANENT ⚡</span>
                </div>
              </div>
            </div>

            <div style={{ background: "#111827", borderRadius: "16px", border: "1px solid rgba(255, 255, 255, 0.08)", padding: "18px", flex: 1 }}>
              <h3 style={{ fontSize: "14px", color: "#8b9bb4", marginBottom: "12px", textTransform: "uppercase", letterSpacing: "0.5px" }}>
                Tactical Shortcuts
              </h3>
              <div style={{ display: "flex", flexDirection: "column", gap: "8px" }}>
                {[
                  "افتحي لي الآلة الحاسبة يا إيديث",
                  "أغلقي برنامج الآلة الحاسبة",
                  "ما هي وظائف نظام EDITH-AI بالكامل؟",
                  "كيف نقوم بحماية قواعد بيانات بصمات الوجوه من الاختراق؟"
                ].map((promptText, idx) => (
                  <button
                    key={idx}
                    onClick={() => handleSendMessage(promptText)}
                    style={{
                      background: "#192033",
                      border: "1px solid rgba(255,255,255,0.06)",
                      color: "#f3f4f6",
                      padding: "10px 12px",
                      borderRadius: "8px",
                      fontSize: "12px",
                      textAlign: "left",
                      cursor: "pointer",
                      transition: "all 0.2s"
                    }}
                    onMouseOver={(e) => (e.currentTarget.style.borderColor = "#00d4ff")}
                    onMouseOut={(e) => (e.currentTarget.style.borderColor = "rgba(255,255,255,0.06)")}
                  >
                    <FaLightbulb color="#00d4ff" style={{ marginRight: "6px" }} />
                    {promptText}
                  </button>
                ))}
              </div>
            </div>
          </div>
        </div>
      )}

      {/* MODE 3: Vision Laboratory (Upload & Custom Questions) */}
      {activeTab === "vision" && (
        <div style={{ display: "grid", gridTemplateColumns: "1.2fr 1fr", gap: "25px", height: "calc(100vh - 190px)" }}>
          {/* Visual Input Panel */}
          <div
            style={{
              background: "#111827",
              borderRadius: "16px",
              border: "1px solid rgba(0, 212, 255, 0.15)",
              padding: "24px",
              display: "flex",
              flexDirection: "column",
              gap: "18px"
            }}
          >
            <h2 style={{ fontSize: "18px", color: "#fff", margin: 0, display: "flex", alignItems: "center", gap: "8px" }}>
              <FaEye color="#00d4ff" /> Visual Scene Input
            </h2>

            {/* Upload Area */}
            <div
              style={{
                flex: 1,
                minHeight: "260px",
                background: "#192033",
                borderRadius: "12px",
                border: "2px dashed rgba(0, 212, 255, 0.3)",
                display: "flex",
                flexDirection: "column",
                alignItems: "center",
                justifyContent: "center",
                position: "relative",
                overflow: "hidden"
              }}
            >
              {visionPreview ? (
                <img
                  src={visionPreview}
                  alt="Target Scene"
                  style={{ width: "100%", height: "100%", objectFit: "contain", maxHeight: "320px" }}
                />
              ) : (
                <label htmlFor="vision-file-input" style={{ cursor: "pointer", textAlign: "center", padding: "20px" }}>
                  <FaCamera size={44} color="#00d4ff" style={{ marginBottom: "12px" }} />
                  <h4 style={{ color: "#fff", marginBottom: "4px" }}>Click to Select Scene Image</h4>
                  <p style={{ color: "#8b9bb4", fontSize: "12px" }}>Upload any photo or diagram for instant Gemini Vision analysis</p>
                </label>
              )}
              <input
                id="vision-file-input"
                type="file"
                accept="image/*"
                onChange={handleVisionFile}
                style={{ display: "none" }}
              />
            </div>

            {/* Prompt input */}
            <div>
              <label style={{ display: "block", color: "#8b9bb4", fontSize: "12px", marginBottom: "6px" }}>
                Analysis Instruction / Prompt
              </label>
              <div style={{ display: "flex", gap: "10px" }}>
                <input
                  type="text"
                  value={visionPrompt}
                  onChange={(e) => setVisionPrompt(e.target.value)}
                  placeholder="e.g. Describe everything in detail, solve this math problem, transcribe text..."
                  style={{
                    flex: 1,
                    background: "#192033",
                    border: "1px solid rgba(255,255,255,0.1)",
                    borderRadius: "8px",
                    padding: "10px 14px",
                    color: "#fff",
                    outline: "none",
                    fontSize: "13px"
                  }}
                />
                <button
                  onClick={handleAnalyzeVision}
                  disabled={visionLoading || !selectedVisionImage}
                  style={{
                    background: "linear-gradient(135deg, #00d4ff 0%, #0077ff 100%)",
                    color: "#050816",
                    fontWeight: 700,
                    border: "none",
                    borderRadius: "8px",
                    padding: "0 20px",
                    cursor: visionLoading || !selectedVisionImage ? "not-allowed" : "pointer",
                    display: "flex",
                    alignItems: "center",
                    gap: "8px",
                    opacity: visionLoading || !selectedVisionImage ? 0.6 : 1
                  }}
                >
                  {visionLoading ? <FaSpinner className="spin" /> : <FaEye />}
                  {visionLoading ? "Analyzing..." : "Analyze Scene"}
                </button>
              </div>
            </div>
          </div>

          {/* Analysis Report Output */}
          <div
            style={{
              background: "#111827",
              borderRadius: "16px",
              border: "1px solid rgba(0, 255, 153, 0.2)",
              padding: "24px",
              display: "flex",
              flexDirection: "column",
              overflowY: "auto",
              boxShadow: "0 10px 30px rgba(0,0,0,0.4)"
            }}
          >
            <h2 style={{ fontSize: "18px", color: "#fff", marginBottom: "16px", display: "flex", alignItems: "center", gap: "8px" }}>
              <FaMicrochip color="#00ff99" /> Gemini Vision Report ⚡
            </h2>

            {!visionResult && !visionLoading && (
              <div style={{ textAlign: "center", padding: "60px 0", color: "#8b9bb4" }}>
                <FaInfoCircle size={36} color="#00d4ff" style={{ marginBottom: "12px" }} />
                <p>Select a scene image and click "Analyze Scene" to generate neural descriptions.</p>
              </div>
            )}

            {visionLoading && (
              <div style={{ textAlign: "center", padding: "60px 0", color: "#00d4ff" }}>
                <FaSpinner className="spin" size={36} style={{ marginBottom: "14px" }} />
                <h4>Analyzing Image with Google Gemini 3.5 Flash...</h4>
                <p style={{ fontSize: "12px", color: "#8b9bb4", marginTop: "6px" }}>Performing deep multi-modal scene understanding</p>
              </div>
            )}

            {visionResult && (
              <div style={{ display: "flex", flexDirection: "column", gap: "16px" }}>
                <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center" }}>
                  <span className={`badge ${visionResult.success ? "badge-green" : "badge-red"}`}>
                    {visionResult.success ? "ANALYSIS COMPLETE" : "PROCESS FAILED"}
                  </span>
                  <span style={{ color: "#8b9bb4", fontSize: "12px", fontFamily: "monospace" }}>
                    Engine: {visionResult.engine || "Gemini 3.5"}
                  </span>
                </div>

                <div
                  style={{
                    background: "#192033",
                    padding: "16px",
                    borderRadius: "12px",
                    border: "1px solid rgba(255, 255, 255, 0.08)",
                    fontSize: "14px",
                    lineHeight: "1.7",
                    color: "#f3f4f6",
                    whiteSpace: "pre-wrap"
                  }}
                >
                  {visionResult.description || visionResult.message}
                </div>

                <div style={{ background: "rgba(0, 212, 255, 0.05)", padding: "12px", borderRadius: "8px", borderLeft: "3px solid #00d4ff", fontSize: "12px", color: "#8b9bb4" }}>
                  <strong>Prompt Used:</strong> "{visionPrompt}"
                </div>
              </div>
            )}
          </div>
        </div>
      )}

      {/* Gemini API Key Configuration Modal */}
      {isKeyModalOpen && (
        <div
          style={{
            position: "fixed",
            top: 0,
            left: 0,
            width: "100vw",
            height: "100vh",
            background: "rgba(0, 0, 0, 0.8)",
            backdropFilter: "blur(8px)",
            display: "flex",
            justifyContent: "center",
            alignItems: "center",
            zIndex: 1000,
            padding: "20px"
          }}
        >
          <div
            style={{
              background: "#111827",
              borderRadius: "20px",
              border: "1px solid rgba(0, 212, 255, 0.3)",
              width: "100%",
              maxWidth: "520px",
              padding: "28px",
              boxShadow: "0 20px 50px rgba(0, 0, 0, 0.7)",
              position: "relative"
            }}
          >
            <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center", marginBottom: "18px" }}>
              <h2 style={{ color: "#fff", fontSize: "18px", display: "flex", alignItems: "center", gap: "8px" }}>
                <FaBolt color="#00ff99" /> Activate Google Gemini AI
              </h2>
              <button
                onClick={() => setIsKeyModalOpen(false)}
                style={{ background: "none", border: "none", color: "#8b9bb4", fontSize: "18px", cursor: "pointer" }}
              >
                <FaTimes />
              </button>
            </div>

            <p style={{ color: "#8b9bb4", fontSize: "13px", lineHeight: "1.6", marginBottom: "16px" }}>
              احصل على مفتاح مجاني 100% من موقع{" "}
              <a href="https://aistudio.google.com/" target="_blank" rel="noreferrer" style={{ color: "#00d4ff", textDecoration: "underline" }}>
                Google AI Studio
              </a>{" "}
              والصقه هنا لتفعيل أذكى محرك ذكاء اصطناعي فائق السرعة وبدون أي استهلاك لمعالج أو رامات جهازك!
            </p>

            {keyFeedback && (
              <div
                style={{
                  background: keyFeedback.includes("بنجاح") ? "rgba(0, 255, 153, 0.15)" : "rgba(255, 59, 92, 0.15)",
                  border: `1px solid ${keyFeedback.includes("بنجاح") ? "#00ff99" : "#ff3b5c"}`,
                  color: keyFeedback.includes("بنجاح") ? "#00ff99" : "#ff3b5c",
                  padding: "10px 14px",
                  borderRadius: "8px",
                  fontSize: "13px",
                  marginBottom: "14px"
                }}
              >
                {keyFeedback}
              </div>
            )}

            <form onSubmit={handleSaveKey} style={{ display: "flex", flexDirection: "column", gap: "14px" }}>
              <div>
                <label style={{ display: "block", color: "#8b9bb4", fontSize: "12px", marginBottom: "6px" }}>
                  Gemini API Key (AIzaSy...)
                </label>
                <input
                  type="password"
                  required
                  placeholder="AIzaSy..."
                  value={apiKeyInput}
                  onChange={(e) => setApiKeyInput(e.target.value)}
                  style={{
                    width: "100%",
                    padding: "12px",
                    background: "#192033",
                    border: "1px solid rgba(0, 212, 255, 0.3)",
                    borderRadius: "8px",
                    color: "#fff",
                    outline: "none",
                    fontFamily: "monospace"
                  }}
                />
              </div>

              <div style={{ display: "flex", justifyContent: "flex-end", gap: "10px", marginTop: "8px" }}>
                <button
                  type="button"
                  onClick={() => setIsKeyModalOpen(false)}
                  style={{ background: "#192033", color: "#8b9bb4", border: "none", padding: "10px 18px", borderRadius: "8px", cursor: "pointer" }}
                >
                  Cancel
                </button>
                <button
                  type="submit"
                  disabled={savingKey || !apiKeyInput.trim()}
                  style={{
                    background: "linear-gradient(135deg, #00ff99 0%, #00aa66 100%)",
                    color: "#050816",
                    fontWeight: 700,
                    border: "none",
                    padding: "10px 22px",
                    borderRadius: "8px",
                    cursor: savingKey || !apiKeyInput.trim() ? "not-allowed" : "pointer",
                    display: "flex",
                    alignItems: "center",
                    gap: "6px"
                  }}
                >
                  {savingKey ? <FaSpinner className="spin" /> : <FaBolt />}
                  {savingKey ? "Activating..." : "Save & Activate"}
                </button>
              </div>
            </form>
          </div>
        </div>
      )}
    </MainLayout>
  );
}

