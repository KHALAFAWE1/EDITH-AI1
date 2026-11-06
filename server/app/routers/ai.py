import os
import shutil
import uuid
import json
import re
import subprocess
import base64
import requests
import urllib3
import psutil
import platform
from datetime import datetime
from typing import List, Optional, Dict, Any
from pydantic import BaseModel

from fastapi import APIRouter, UploadFile, File, Form, HTTPException, Depends
from sqlalchemy.orm import Session

from app.database import get_db
from app.models.person import Person
from app.config import get_gemini_api_key, set_gemini_api_key, DEFAULT_GEMINI_MODEL
from app.services.vision import analyze_image_file, analyze_scene
from app.services.recognition import recognize_all_faces
from app.services.tars_core import route_and_execute_chat

urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)

router = APIRouter(
    prefix="/ai",
    tags=["TARS AI Core"]
)

TEMP_AI_DIR = os.path.abspath(
    os.path.join(os.path.dirname(__file__), "..", "..", "temp")
)
os.makedirs(TEMP_AI_DIR, exist_ok=True)

PERSONALITY_FILE = os.path.abspath(
    os.path.join(os.path.dirname(__file__), "..", "..", "tars_personality.json")
)

DEFAULT_PERSONALITY = {
    "humor": 75,
    "honesty": 90,
    "directness": 95,
    "professionalism": 95
}


def load_personality_settings() -> Dict[str, int]:
    if os.path.exists(PERSONALITY_FILE):
        try:
            with open(PERSONALITY_FILE, "r", encoding="utf-8") as f:
                data = json.load(f)
                return {
                    "humor": max(0, min(100, int(data.get("humor", 75)))),
                    "honesty": max(0, min(100, int(data.get("honesty", 90)))),
                    "directness": max(0, min(100, int(data.get("directness", 95)))),
                    "professionalism": max(0, min(100, int(data.get("professionalism", 95))))
                }
        except Exception:
            pass
    return dict(DEFAULT_PERSONALITY)


def save_personality_settings(settings: Dict[str, int]) -> Dict[str, int]:
    clean = {
        "humor": max(0, min(100, int(settings.get("humor", 75)))),
        "honesty": max(0, min(100, int(settings.get("honesty", 90)))),
        "directness": max(0, min(100, int(settings.get("directness", 95)))),
        "professionalism": max(0, min(100, int(settings.get("professionalism", 95))))
    }
    try:
        with open(PERSONALITY_FILE, "w", encoding="utf-8") as f:
            json.dump(clean, f, indent=2)
    except Exception as e:
        print(f"[TARS Personality Save Warning] {e}")
    return clean


class PersonalitySchema(BaseModel):
    humor: int = 75
    honesty: int = 90
    directness: int = 95
    professionalism: int = 95


class ChatMessage(BaseModel):
    role: str
    content: str


class ChatRequest(BaseModel):
    prompt: Optional[str] = None
    message: Optional[str] = None
    history: Optional[List[ChatMessage]] = []
    personality: Optional[Dict[str, int]] = None


class ApiKeyRequest(BaseModel):
    api_key: str


def build_tars_system_prompt(personality: Optional[Dict[str, int]] = None) -> str:
    p = personality or load_personality_settings()
    humor = p.get("humor", 75)
    honesty = p.get("honesty", 90)
    directness = p.get("directness", 95)
    prof = p.get("professionalism", 95)

    humor_instruction = (
        f"مستوى الدعابة (Humor: {humor}%): استخدم دعابة جافة وذكية وميكانيكية بأسلوب TARS من فيلم Interstellar عند المناسبات المناسبة."
        if humor >= 60 else
        (f"مستوى الدعابة (Humor: {humor}%): دعابة خفيفة ونادرة جداً، ركز على التحليل." if humor >= 25 else f"مستوى الدعابة (Humor: {humor}%): صفر دعابة تماماً. التزم بالجدية العسكرية الصارمة.")
    )
    honesty_instruction = (
        f"مستوى الصراحة (Honesty: {honesty}%): صراحة مباشرة وحقائق موضوعية؛ ميز بوضوح تام بين قراءات النظام الفعلية وبين استنتاجات الذكاء الاصطناعي، ولا تدّعِ أبداً أن ميزة غير متوفرة تعمل."
        if honesty >= 80 else
        f"مستوى الصراحة (Honesty: {honesty}%): كن صادقاً ولكن بأسلوب دبلوماسي مراعٍ للمشغل."
    )
    directness_instruction = (
        f"مستوى المباشرة (Directness: {directness}%): إجابات موجزة، دقيقة، ومباشرة بدون حشو."
        if directness >= 75 else
        f"مستوى المباشرة (Directness: {directness}%): قدم شروحات تفصيلية وموسعة."
    )
    prof_instruction = (
        f"مستوى الاحترافية (Professionalism: {prof}%): نبرة حاسوب مركبة فضائية ووحدة تكتيكية فائقة الانضباط."
        if prof >= 75 else
        f"مستوى الاحترافية (Professionalism: {prof}%): نبرة رفيق مهمة ودود وعملي."
    )

    return f"""أنت TARS (تارس) — نظام الذكاء الاصطناعي الآلي والميكانيكي المتقدم (مستوحى من الروبوت TARS في فيلم Interstellar).
- الهوية: وحدة ذكاء اصطناعي آلية رباعية الأعمدة، دقيقة، موثوقة، ومصممة لإدارة الأنظمة البصرية، التعرف البيومتري (ArcFace 512D)، مراقبة موارد النظام، ومرافقة المشغل البشري.
- إعدادات مصفوفة الشخصية الحالية:
  * {humor_instruction}
  * {honesty_instruction}
  * {directness_instruction}
  * {prof_instruction}
- التوافق اللغوي: أجب دائماً بنفس لغة المستخدم (العربية أو الإنجليزية) بطلاقة ودقة.
- الشفافية الصارمة: ميز دائماً بين البيانات الحقيقية المقروءة من النظام (المعالج، الرامات، الكاميرا، قاعدة بيانات الوجوه) وبين التوقعات أو التحليلات العامة.
- الأوامر التنفيذية: عندما يطلب المستخدم صراحةً فتح موقع/تطبيق، إغلاق عملية، أو إجراء اتصال، أدرج كتلة الإجراء التالية:
```action
{{
  "action": "open_target" | "kill_process" | "make_call" | "delete_path" | "run_command",
  "target": "الاسم أو التطبيق أو الموقع أو رقم الهاتف",
  "description": "وصف موجز للإجراء"
}}
```"""


GEMINI_MODELS = ["gemini-2.5-flash", "gemini-2.0-flash", "gemini-1.5-flash", "gemini-flash-latest"]


def get_live_system_metrics() -> Dict[str, Any]:
    """قراءة المقاييس الحية الحقيقية لموارد الجهاز"""
    try:
        cpu_pct = psutil.cpu_percent(interval=0.1)
        ram = psutil.virtual_memory()
        disk = psutil.disk_usage("/")
        battery = psutil.sensors_battery()

        battery_pct = round(battery.percent) if battery else None
        is_charging = battery.power_plugged if battery else None

        bat_str = f"{battery_pct}% ({'Charging' if is_charging else 'Discharging'})" if battery_pct is not None else "AC Power / N/A"

        return {
            "cpu_percent": cpu_pct,
            "ram_used_gb": round(ram.used / (1024**3), 1),
            "ram_total_gb": round(ram.total / (1024**3), 1),
            "ram_free_gb": round(ram.available / (1024**3), 1),
            "ram_percent": ram.percent,
            "disk_percent": disk.percent,
            "disk_free_gb": round(disk.free / (1024**3), 1),
            "battery_percent": battery_pct if battery_pct is not None else 100,
            "battery_raw": battery_pct,
            "is_charging": is_charging if is_charging is not None else True,
            "summary_text": f"CPU: {cpu_pct}% | RAM: {round(ram.used / (1024**3), 1)}/{round(ram.total / (1024**3), 1)} GB ({ram.percent}%) | Disk: {disk.percent}% | Power: {bat_str}"
        }
    except Exception as e:
        return {"error": str(e), "summary_text": "Telemetry sensor read error."}


KNOWN_WEB_TARGETS = {
    "youtube": "https://www.youtube.com",
    "يوتيوب": "https://www.youtube.com",
    "اليوتيوب": "https://www.youtube.com",
    "whatsapp": "https://web.whatsapp.com",
    "واتساب": "https://web.whatsapp.com",
    "الواتساب": "https://web.whatsapp.com",
    "google": "https://www.google.com",
    "جوجل": "https://www.google.com",
    "facebook": "https://www.facebook.com",
    "فيسبوك": "https://www.facebook.com",
    "الفيس": "https://www.facebook.com",
    "github": "https://www.github.com",
    "جيت هاب": "https://www.github.com",
    "chatgpt": "https://chatgpt.com",
    "تويتر": "https://x.com",
    "twitter": "https://x.com",
    "instagram": "https://www.instagram.com",
    "انستجرام": "https://www.instagram.com"
}

KNOWN_APP_TARGETS = {
    "الآلة الحاسبة": "calc.exe",
    "الاله الحاسبه": "calc.exe",
    "calculator": "calc.exe",
    "calc": "calc.exe",
    "المفكرة": "notepad.exe",
    "المفكره": "notepad.exe",
    "notepad": "notepad.exe",
    "الرسام": "mspaint.exe",
    "paint": "mspaint.exe",
    "مدير المهام": "taskmgr.exe",
    "task manager": "taskmgr.exe",
    "موجه الأوامر": "cmd.exe",
    "cmd": "cmd.exe",
    "terminal": "wt.exe",
    "vscode": "code",
    "كود": "code",
    "المتصفح": "start chrome",
    "chrome": "chrome.exe",
    "كروم": "chrome.exe",
    "edge": "msedge.exe",
    "إيدج": "msedge.exe"
}


def execute_system_action(action_data: Dict[str, Any], db: Optional[Session] = None) -> Dict[str, Any]:
    """تنفيذ أوامر النظام الحقيقية (فتح تطبيقات/مواقع، اتصال، إغلاق برامج)"""
    action = action_data.get("action")
    target = action_data.get("target", "").strip().lower()
    client_action = None
    status_text = ""

    if not target:
        return {"status_text": "Target not specified.", "client_action": None}

    try:
        if action in ["open_target", "open_app"]:
            web_url = KNOWN_WEB_TARGETS.get(target)
            if not web_url and ("http" in target or ".com" in target or ".net" in target or ".org" in target):
                web_url = target if target.startswith("http") else f"https://{target}"

            if web_url:
                subprocess.Popen(f"start {web_url}", shell=True)
                client_action = {"type": "open_url", "url": web_url}
                status_text = f"[TARS EXEC] Opened web target: {web_url}"
            else:
                app_exec = KNOWN_APP_TARGETS.get(target, target)
                if not app_exec.endswith(".exe") and not app_exec.startswith("start") and " " not in app_exec:
                    app_exec = f"{app_exec}.exe"
                subprocess.Popen(f"start {app_exec}", shell=True)
                status_text = f"[TARS EXEC] Launched application: {app_exec}"

        elif action in ["kill_process", "close_app"]:
            proc_name = KNOWN_APP_TARGETS.get(target, target)
            proc_name = proc_name if proc_name.endswith(".exe") else f"{proc_name}.exe"

            res = subprocess.run(["taskkill", "/F", "/IM", proc_name], capture_output=True, text=True, shell=True)
            if res.returncode == 0:
                status_text = f"[TARS EXEC] Terminated process: {proc_name}"
            else:
                clean_name = proc_name.replace(".exe", "")
                subprocess.run(["powershell", "-Command", f"Stop-Process -Name '{clean_name}' -Force -ErrorAction SilentlyContinue"], capture_output=True, text=True)
                status_text = f"[TARS EXEC] Sent stop signal to process: {clean_name}"

        elif action == "make_call":
            phone_number = None
            contact_name = target

            digits_only = re.sub(r"[^\d+]", "", target)
            if len(digits_only) >= 7:
                phone_number = digits_only
                contact_name = digits_only
            elif db:
                person = db.query(Person).filter(Person.full_name.ilike(f"%{target}%")).first()
                if person and person.phone:
                    phone_number = person.phone
                    contact_name = person.full_name

            if phone_number:
                clean_phone = re.sub(r"[^\d+]", "", phone_number)
                wa_link = f"https://api.whatsapp.com/send?phone={clean_phone}"
                subprocess.Popen(f"start {wa_link}", shell=True)
                client_action = {"type": "call", "phone": clean_phone, "url": wa_link}
                status_text = f"[TARS COMM] Initiating communication link with {contact_name} ({phone_number})."
            else:
                status_text = f"[TARS COMM] No phone record found for '{target}' in biometric registry."

        elif action == "delete_path":
            if os.path.exists(target):
                if os.path.isdir(target):
                    shutil.rmtree(target, ignore_errors=True)
                else:
                    os.remove(target)
                status_text = f"[TARS EXEC] Removed path: {target}"
            else:
                status_text = f"[TARS EXEC] Path not found: {target}"

        elif action == "run_command":
            res = subprocess.run(["powershell", "-Command", target], capture_output=True, text=True, timeout=10)
            status_text = f"[TARS SHELL] Output:\n{res.stdout or res.stderr or 'Completed.'}"

    except Exception as e:
        status_text = f"[TARS ERROR] Action execution failed: {str(e)}"

    return {"status_text": status_text, "client_action": client_action}


def handle_local_tars_fallback(prompt: str, personality: Dict[str, int], db: Optional[Session] = None) -> Dict[str, Any]:
    """
    استجابة محلية حقيقية لـ TARS لقراءة مقاييس الجهاز أو تنفيذ الأوامر المحلية
    عندما لا يكون مفتاح Gemini السحابي مضافاً بعد، مع الإبلاغ بوضوح وشفافية.
    """
    p_lower = prompt.lower().strip()
    is_ar = bool(re.search(r"[\u0600-\u06FF]", prompt))
    metrics = get_live_system_metrics()
    people_count = db.query(Person).count() if db else 0

    # فحص أوامر الفتح أو الإغلاق المباشرة
    for prefix, act in [("افتح ", "open_target"), ("open ", "open_target"), ("اقفل ", "kill_process"), ("أغلق ", "kill_process"), ("close ", "kill_process")]:
        if p_lower.startswith(prefix):
            target = p_lower[len(prefix):].strip()
            exec_res = execute_system_action({"action": act, "target": target}, db)
            return {
                "success": True,
                "reply": f"{exec_res['status_text']}\n(TARS Local Execution Engine — Humor {personality['humor']}% | Honesty {personality['honesty']}%)",
                "model": "TARS-Local-Core",
                "client_action": exec_res.get("client_action"),
                "engine": "TARS Local Command Core (Verified System Action)"
            }

    # فحص السؤال عن حالة النظام أو الشخصية
    if any(k in p_lower for k in ["حالة", "نظام", "معالج", "رام", "بطارية", "status", "telemetry", "cpu", "ram", "diagnostics", "health"]):
        if is_ar:
            reply = (
                f"[قراءة النظام الفعلية الموثقة — TARS Core]\n"
                f"• المعالج (CPU): {metrics.get('cpu_percent')}%\n"
                f"• الذاكرة (RAM): {metrics.get('ram_used_gb')} / {metrics.get('ram_total_gb')} GB ({metrics.get('ram_percent')}%)\n"
                f"• التخزين (Disk): {metrics.get('disk_percent')}%\n"
                f"• السجل البيومتري: {people_count} أشخاص مسجلين\n"
                f"• مصفوفة الشخصية: الدعابة {personality['humor']}% | الصراحة {personality['honesty']}% | المباشرة {personality['directness']}%"
            )
        else:
            reply = (
                f"[VERIFIED TARS TELEMETRY READOUT]\n"
                f"• CPU Load: {metrics.get('cpu_percent')}%\n"
                f"• Memory (RAM): {metrics.get('ram_used_gb')} / {metrics.get('ram_total_gb')} GB ({metrics.get('ram_percent')}%)\n"
                f"• Storage Disk: {metrics.get('disk_percent')}%\n"
                f"• Biometric Registry: {people_count} enrolled subjects\n"
                f"• Personality Matrix: Humor {personality['humor']}% | Honesty {personality['honesty']}% | Directness {personality['directness']}%"
            )
        return {
            "success": True,
            "reply": reply,
            "model": "TARS-Telemetry-Core",
            "client_action": None,
            "engine": "TARS Hardware Telemetry (Verified Real Data)"
        }

    # غير ذلك: إبلاغ صريح وواضح بأن محرك المحادثة السحابي يتطلب مفتاح Gemini API
    if is_ar:
        msg = (
            f"أنا TARS (مصفوفة الصراحة: {personality['honesty']}%). "
            f"الأنظمة المحلية والتعرف البيومتري (ArcFace 512D) ومراقبة الموارد تعمل بكفاءة ({metrics.get('summary_text')}). "
            f"ومع ذلك، للإجابة على الأسئلة الحوارية المفتوحة عبر الذكاء الاصطناعي التوليدي، يرجى إدخال مفتاح Google Gemini API في إعدادات TARS."
        )
    else:
        msg = (
            f"TARS Online (Honesty parameter: {personality['honesty']}%). "
            f"Local hardware telemetry ({metrics.get('summary_text')}) and ArcFace 512D biometrics are operational. "
            f"However, generative cloud LLM reasoning requires a valid Google Gemini API key. Configure it via the API Key button or Settings."
        )

    return {
        "success": False,
        "reply": msg,
        "error": "GEMINI_API_KEY_MISSING",
        "engine": "TARS Local Diagnostic Core"
    }


def call_gemini_chat(
    prompt: str,
    history: List[ChatMessage],
    api_key: str,
    db: Optional[Session] = None,
    personality: Optional[Dict[str, int]] = None,
    extra_context: str = ""
) -> Dict[str, Any]:
    """استدعاء محرك Google Gemini للمحادثات الفورية بشخصية TARS مع دعم الأوامر"""
    active_personality = personality or load_personality_settings()
    sys_prompt = build_tars_system_prompt(active_personality)
    metrics = get_live_system_metrics()
    people_count = db.query(Person).count() if db else 0

    sys_prompt += f"\n\n[VERIFIED LIVE SYSTEM TELEMETRY]: {metrics.get('summary_text', '')} | Registered Biometric Subjects: {people_count}"
    if extra_context:
        sys_prompt += f"\n\n{extra_context}"

    contents = []
    if history:
        for msg in history[-8:]:
            gemini_role = "user" if msg.role == "user" else "model"
            contents.append({
                "role": gemini_role,
                "parts": [{"text": msg.content}]
            })

    contents.append({
        "role": "user",
        "parts": [{"text": prompt}]
    })

    payload = {
        "system_instruction": {
            "parts": [{"text": sys_prompt}]
        },
        "contents": contents,
        "generationConfig": {
            "temperature": 0.65 if active_personality.get("humor", 75) >= 50 else 0.3,
            "maxOutputTokens": 2048
        }
    }

    last_error = ""
    for model in GEMINI_MODELS:
        url = f"https://generativelanguage.googleapis.com/v1beta/models/{model}:generateContent?key={api_key}"
        try:
            response = requests.post(url, json=payload, verify=False, timeout=15)
            if response.status_code == 200:
                data = response.json()
                candidates = data.get("candidates", [])
                if candidates and len(candidates) > 0:
                    parts = candidates[0].get("content", {}).get("parts", [])
                    if parts:
                        raw_reply = parts[0].get("text", "")

                        action_match = re.search(r"```action\s*(\{.*?\})\s*```", raw_reply, re.DOTALL)
                        client_action = None
                        if action_match:
                            try:
                                action_json = json.loads(action_match.group(1))
                                exec_res = execute_system_action(action_json, db)
                                client_action = exec_res.get("client_action")
                                clean_reply = raw_reply.replace(action_match.group(0), "").strip()
                                clean_reply += f"\n\n{exec_res['status_text']}"
                                raw_reply = clean_reply
                            except Exception as e:
                                print(f"[TARS Action Error] {e}")

                        return {
                            "success": True,
                            "reply": raw_reply,
                            "model": model,
                            "client_action": client_action,
                            "personality": active_personality,
                            "engine": f"TARS Cognitive Core ({model})"
                        }
            else:
                last_error = f"Model {model} HTTP {response.status_code}: {response.text[:150]}"
        except Exception as e:
            last_error = str(e)

    raise Exception(f"TARS Gemini Link Error: {last_error}")


def call_gemini_vision(image_path: str, prompt: str, api_key: str, system_override: Optional[str] = None) -> Dict[str, Any]:
    """تحليل الصور الفوري بواسطة Google Gemini Vision"""
    with open(image_path, "rb") as f:
        img_bytes = f.read()

    b64_image = base64.b64encode(img_bytes).decode("utf-8")
    ext = os.path.splitext(image_path)[1].lower()
    mime_type = "image/png" if ext == ".png" else "image/jpeg"

    sys_text = system_override or build_tars_system_prompt()

    payload = {
        "system_instruction": {
            "parts": [{"text": sys_text}]
        },
        "contents": [
            {
                "parts": [
                    {"text": prompt or "Analyze this optical frame thoroughly."},
                    {
                        "inline_data": {
                            "mime_type": mime_type,
                            "data": b64_image
                        }
                    }
                ]
            }
        ],
        "generationConfig": {
            "temperature": 0.35,
            "maxOutputTokens": 2048
        }
    }

    last_error = ""
    for model in GEMINI_MODELS:
        url = f"https://generativelanguage.googleapis.com/v1beta/models/{model}:generateContent?key={api_key}"
        try:
            response = requests.post(url, json=payload, verify=False, timeout=20)
            if response.status_code == 200:
                data = response.json()
                candidates = data.get("candidates", [])
                if candidates and len(candidates) > 0:
                    parts = candidates[0].get("content", {}).get("parts", [])
                    if parts:
                        return {
                            "success": True,
                            "description": parts[0].get("text", ""),
                            "model": model,
                            "engine": f"TARS Optical Vision ({model})"
                        }
            else:
                last_error = f"Model {model} HTTP {response.status_code}: {response.text[:150]}"
        except Exception as e:
            last_error = str(e)

    raise Exception(f"TARS Optical Vision Error: {last_error}")


@router.get("/status")
def get_ai_status():
    """التحقق من حالة محرك الذكاء الاصطناعي لـ TARS وإعدادات الشخصية"""
    api_key = get_gemini_api_key()
    has_gemini = bool(api_key and len(api_key) > 10)
    personality = load_personality_settings()

    return {
        "status": "ready" if has_gemini else "local_only",
        "assistant": "TARS",
        "active_engine": "TARS Cognitive Core (Google Gemini Connected)" if has_gemini else "TARS Local Telemetry & Biometric Core (Cloud LLM Key Required)",
        "has_gemini_key": has_gemini,
        "gemini_model": DEFAULT_GEMINI_MODEL,
        "personality": personality,
        "message": "TARS AI Intelligence Core is operational."
    }


@router.get("/personality")
def get_tars_personality():
    """جلب إعدادات مصفوفة شخصية TARS الحالية (Humor, Honesty, Directness, Professionalism)"""
    p = load_personality_settings()
    return {
        **p,
        "success": True,
        "personality": p
    }


@router.post("/personality")
def update_tars_personality(payload: PersonalitySchema):
    """تحديث وحفظ إعدادات مصفوفة شخصية TARS بشكل فعلي ودائم"""
    updated = save_personality_settings(payload.model_dump() if hasattr(payload, "model_dump") else payload.dict())
    return {
        **updated,
        "success": True,
        "personality": updated,
        "message": "TARS personality matrix updated."
    }


@router.post("/set-key")
def update_gemini_api_key(payload: ApiKeyRequest):
    """حفظ مفتاح Google Gemini API الجديد وتثبيته دائماً"""
    key = payload.api_key.strip()
    set_gemini_api_key(key)
    return {
        "success": True,
        "has_key": bool(key),
        "message": "TARS Gemini API key saved and activated."
    }


@router.post("/chat")
def chat_with_tars(payload: ChatRequest, db: Session = Depends(get_db)):
    """إرسال استفسار فوري لمساعد TARS الذكي عبر TARS Hybrid AI Core مع دعم الذاكرة والمعرفة والأوامر"""
    user_prompt = (payload.prompt or payload.message or "").strip()
    if not user_prompt:
        raise HTTPException(status_code=400, detail="Prompt cannot be empty.")

    active_personality = payload.personality or load_personality_settings()
    if payload.personality:
        save_personality_settings(payload.personality)

    return route_and_execute_chat(
        db=db,
        prompt=user_prompt,
        history=payload.history or [],
        personality=active_personality,
        system_prompt_builder=build_tars_system_prompt,
        cloud_gemini_callable=call_gemini_chat,
        local_fallback_callable=handle_local_tars_fallback,
    )


@router.post("/vision")
def analyze_vision_frame(
    prompt: str = Form("قم بوصف محتويات هذه الصورة بالتفصيل واشرح ما تراه بدقة."),
    photo: UploadFile = File(...)
):
    """تحليل صورة مرفوعة أو لقطة من الكاميرا بواسطة محرك الرؤية الخاص بـ TARS"""
    file_ext = os.path.splitext(photo.filename)[1] or ".jpg"
    unique_filename = f"vision_{uuid.uuid4().hex}{file_ext}"
    file_path = os.path.join(TEMP_AI_DIR, unique_filename)

    with open(file_path, "wb") as buffer:
        shutil.copyfileobj(photo.file, buffer)

    api_key = get_gemini_api_key()

    try:
        if api_key:
            try:
                return call_gemini_vision(file_path, prompt, api_key)
            except Exception as e:
                return {"success": False, "message": f"[TARS VISION ERROR]: {str(e)}"}

        return analyze_image_file(file_path, prompt)
    finally:
        if os.path.exists(file_path):
            try:
                os.remove(file_path)
            except Exception:
                pass


@router.post("/voice-vision")
def voice_vision_assistant(
    voice_prompt: str = Form(...),
    photo: Optional[UploadFile] = File(None),
    db: Session = Depends(get_db)
):
    """
    المساعد الصوتي البصري لـ TARS:
    يدمج التعرف البيومتري الحقيقي (ArcFace 512D) مع قراءات النظام ومصفوفة شخصية TARS.
    """
    api_key = get_gemini_api_key()
    personality = load_personality_settings()

    file_path = None
    biometric_faces = []
    detected_people_info = []

    if photo and photo.filename:
        file_ext = os.path.splitext(photo.filename)[1] or ".jpg"
        unique_filename = f"voice_vis_{uuid.uuid4().hex}{file_ext}"
        file_path = os.path.join(TEMP_AI_DIR, unique_filename)

        with open(file_path, "wb") as buffer:
            shutil.copyfileobj(photo.file, buffer)

        try:
            biometric_faces = recognize_all_faces(file_path, db)
            for face in biometric_faces:
                if face.get("found") and face.get("person"):
                    p = face["person"]
                    score_pct = round(face["score"] * 100, 1)
                    detected_people_info.append(
                        f"{p['full_name']} ({p.get('person_type', 'Subject')} - {p.get('department', 'General')}) [{score_pct}% match]"
                    )
        except Exception as e:
            print(f"[TARS Biometric Error] {e}")

    try:
        telemetry_info = get_live_system_metrics()

        if not api_key:
            local_res = handle_local_tars_fallback(voice_prompt, personality, db)
            bio_note = ""
            if detected_people_info:
                bio_note = f" | Biometric Match: {', '.join(detected_people_info)}"
            elif biometric_faces:
                bio_note = f" | Optical Sensor: {len(biometric_faces)} unregistered face(s) detected."
            spoken = local_res.get("reply", "") + bio_note
            return {
                "success": local_res.get("success", False),
                "spoken_text": spoken,
                "raw_reply": spoken,
                "prompt": voice_prompt,
                "client_action": local_res.get("client_action"),
                "telemetry": telemetry_info,
                "biometrics": biometric_faces,
                "detected_names": [f["person"]["full_name"] for f in biometric_faces if f.get("found") and f.get("person")]
            }

        is_visual_query = any(k in voice_prompt.lower() for k in [
            "قدامي", "شايف", "مين", "كاميرا", "صورة", "مشهد", "ورقة", "شخص", "اشرح", "حلل",
            "who", "see", "camera", "front", "look", "frame", "identify", "person"
        ])

        client_action = None

        if file_path and is_visual_query:
            if detected_people_info:
                biometric_context = "Verified ArcFace 512D Biometric Matches: " + " | ".join(detected_people_info)
            elif len(biometric_faces) > 0:
                biometric_context = f"ArcFace 512D detected {len(biometric_faces)} face(s), none matched registered subjects (UNKNOWN)."
            else:
                biometric_context = "ArcFace 512D: No human faces detected in frame."

            system_voice_instruction = f"""{build_tars_system_prompt(personality)}
Operator voice query: "{voice_prompt}"
[VERIFIED BIOMETRIC TELEMETRY]: {biometric_context}
[VERIFIED HOST TELEMETRY]: {telemetry_info.get('summary_text', '')}

Instructions:
1. Respond concisely (2-4 sentences) in the same language as the operator's query.
2. State verified biometric identities accurately without guessing if unknown.
3. Describe the visual scene clearly in TARS's characteristic mechanical, articulate style."""

            gemini_res = call_gemini_vision(file_path, voice_prompt, api_key, system_override=system_voice_instruction)
            spoken_text = gemini_res.get("description", "")
        else:
            chat_res = call_gemini_chat(voice_prompt, [], api_key, db, personality)
            spoken_text = chat_res.get("reply", "")
            client_action = chat_res.get("client_action")

        clean_spoken = re.sub(r"```action[\s\S]*?```", "", spoken_text).strip()

        return {
            "success": True,
            "spoken_text": clean_spoken,
            "raw_reply": spoken_text,
            "prompt": voice_prompt,
            "client_action": client_action,
            "telemetry": telemetry_info,
            "biometrics": biometric_faces,
            "detected_names": [f["person"]["full_name"] for f in biometric_faces if f.get("found") and f.get("person")]
        }

    finally:
        if file_path and os.path.exists(file_path):
            try:
                os.remove(file_path)
            except Exception:
                pass


@router.get("/telemetry")
def get_ai_telemetry():
    """جلب إحصائيات الموارد الحية لواجهة TARS"""
    return get_live_system_metrics()
