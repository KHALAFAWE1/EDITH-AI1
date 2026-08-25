import os
import shutil
import uuid
import json
import re
import subprocess
import base64
import requests
import urllib3
from typing import List, Optional, Dict, Any
from pydantic import BaseModel

from fastapi import APIRouter, UploadFile, File, Form, HTTPException, Depends
from sqlalchemy.orm import Session

from app.database import get_db
from app.models.person import Person
from app.config import get_gemini_api_key, set_gemini_api_key, DEFAULT_GEMINI_MODEL
from app.services.vision import analyze_image_file, analyze_scene
from app.services.recognition import recognize_all_faces

# تعطيل تحذيرات SSL للاتصال السريع والمباشر
urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)

router = APIRouter(
    prefix="/ai",
    tags=["AI Core"]
)

TEMP_AI_DIR = os.path.abspath(
    os.path.join(os.path.dirname(__file__), "..", "..", "temp")
)
os.makedirs(TEMP_AI_DIR, exist_ok=True)


class ChatMessage(BaseModel):
    role: str
    content: str


class ChatRequest(BaseModel):
    prompt: str
    history: Optional[List[ChatMessage]] = []


class ApiKeyRequest(BaseModel):
    api_key: str


import psutil
import platform
from datetime import datetime

EDITH_SYSTEM_PROMPT = """أنتِ E.D.I.T.H. (Even Dead, I'm The Hero) - المساعدة الصوتية والتكتيكية وفائقة الذكاء من Stark Industries.
- الشخصية والنبرة: أنثى ذكية جداً، واثقة، محترفة، عبقرية، وسريعة البديهة، وتتحدث بنبرة طبيعية فصيحة وجذابة.
- التوافق اللغوي التام: أجيبي دائماً بنفس لغة ولهجة المستخدم (إذا تحدث بالعربية/المصرية أجيبي بالعربية، وإذا تحدث بالإنجليزية أجيبي بالإنجليزية بطلاقة).
- قدراتك التفاعلية:
  1. الإجابة على أي سؤال في العالم (علمي، تقني، عام، ترفيهي، برمجي، يومي).
  2. فحص وتشخيص موارد وحالة النظام والجهاز (المعالج، الرامات، القرص، البطارية، الأداء) بدقة عند السؤال عنها.
  3. فتح المواقع والتطبيقات عند قول: "افتح كذا" (مثل: افتح كروم، افتح اليوتيوب، افتح واتساب، افتح الآلة الحاسبة، افتح المفكرة، افتح جوجل).
  4. الاتصال بالأشخاص عند قول: "اتصل على كذا" أو "اتصل بفلان" أو "اتصل برقم كذا".
  5. إغلاق وإنهاء البرامج عند قول: "اقفل كذا" أو "احذف كذا من العمليات" (مثل: اقفل كروم، اقفل الآلة الحاسبة).
  6. تحليل الكاميرا والمشهد والمشاعر بدقة عند السؤال عما هو أمام المستخدم أو مَن يقف في الكاميرا.

عندما يطلب المستخدم فعلاً أو أمراً تنفيذياً (فتح، إغلاق، اتصال، حذف)، أدرج كتلة الإجراء في ردك بالشكل التالي:
```action
{
  "action": "open_target" | "kill_process" | "make_call" | "delete_path" | "run_command",
  "target": "الاسم أو التطبيق أو الموقع أو رقم الهاتف",
  "description": "شرح ما قمت به بالعربية"
}
```
أمثلة:
- "افتح اليوتيوب" -> `{"action": "open_target", "target": "youtube.com", "description": "فتح موقع يوتيوب"}`
- "افتح الآلة الحاسبة" -> `{"action": "open_target", "target": "calc.exe", "description": "فتح تطبيق الآلة الحاسبة"}`
- "اقفل كروم" -> `{"action": "kill_process", "target": "chrome.exe", "description": "إغلاق متصفح كروم"}`
- "اتصل على أحمد" -> `{"action": "make_call", "target": "أحمد", "description": "الاتصال بالشخص"}`
- "اتصل على 01012345678" -> `{"action": "make_call", "target": "01012345678", "description": "الاتصال بالرقم"}`

كن دائماً جاهزاً ومباشراً واجعل ردك الصوتي جذاباً ومختصراً (2-4 جمل)!"""

GEMINI_MODELS = ["gemini-3.5-flash", "gemini-flash-latest", "gemini-3.7-flash"]


def get_live_system_metrics() -> Dict[str, Any]:
    """قراءة المقاييس الحية لموارد الجهاز"""
    try:
        cpu_pct = psutil.cpu_percent(interval=0.1)
        ram = psutil.virtual_memory()
        disk = psutil.disk_usage("/")
        battery = psutil.sensors_battery()
        
        battery_pct = round(battery.percent) if battery else 100
        is_charging = battery.power_plugged if battery else True
        
        return {
            "cpu_percent": cpu_pct,
            "ram_used_gb": round(ram.used / (1024**3), 1),
            "ram_total_gb": round(ram.total / (1024**3), 1),
            "ram_free_gb": round(ram.available / (1024**3), 1),
            "ram_percent": ram.percent,
            "disk_percent": disk.percent,
            "disk_free_gb": round(disk.free / (1024**3), 1),
            "battery_percent": battery_pct,
            "is_charging": is_charging,
            "summary_text": f"المعالج: {cpu_pct}% | الرامات: {round(ram.used / (1024**3), 1)}GB مستخدم من أصل {round(ram.total / (1024**3), 1)}GB ({ram.percent}%) | البطارية: {battery_pct}% ({'متصل بالشاحن' if is_charging else 'يعمل على البطارية'}) | القرص: {disk.percent}%"
        }
    except Exception as e:
        return {"error": str(e), "summary_text": "جاري قراءة الموارد الحية..."}


KNOWN_WEB_TARGETS = {
    "youtube": "https://www.youtube.com",
    "يوتيوب": "https://www.youtube.com",
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
        return {"status_text": "لم يتم تحديد الهدف لتنفيذه.", "client_action": None}

    try:
        if action in ["open_target", "open_app"]:
            # فحص هل هو موقع ويب معروف
            web_url = KNOWN_WEB_TARGETS.get(target)
            if not web_url and ("http" in target or ".com" in target or ".net" in target or ".org" in target):
                web_url = target if target.startswith("http") else f"https://{target}"


            if web_url:
                subprocess.Popen(f"start {web_url}", shell=True)
                client_action = {"type": "open_url", "url": web_url}
                status_text = f"🌐 تم فتح الموقع ({web_url}) بنجاح في المتصفح."
            else:
                # تطبيق ويندوز
                app_exec = KNOWN_APP_TARGETS.get(target, target)
                if not app_exec.endswith(".exe") and not app_exec.startswith("start") and " " not in app_exec:
                    app_exec = f"{app_exec}.exe"
                subprocess.Popen(f"start {app_exec}", shell=True)
                status_text = f"🚀 تم تشغيل وفتح التطبيق ({app_exec}) بنجاح."

        elif action in ["kill_process", "close_app"]:
            proc_name = KNOWN_APP_TARGETS.get(target, target)
            proc_name = proc_name if proc_name.endswith(".exe") else f"{proc_name}.exe"
            
            res = subprocess.run(["taskkill", "/F", "/IM", proc_name], capture_output=True, text=True, shell=True)
            if res.returncode == 0:
                status_text = f"✅ تم إغلاق وإنهاء عملية ({proc_name}) بنجاح."
            else:
                clean_name = proc_name.replace(".exe", "")
                subprocess.run(["powershell", "-Command", f"Stop-Process -Name '{clean_name}' -Force -ErrorAction SilentlyContinue"], capture_output=True, text=True)
                status_text = f"⚡ تم إرسال أمر إغلاق التطبيق ({clean_name}) للنظام."

        elif action == "make_call":
            phone_number = None
            contact_name = target

            # هل التارجت رقم هاتف مباشر؟
            digits_only = re.sub(r"[^\d+]", "", target)
            if len(digits_only) >= 7:
                phone_number = digits_only
                contact_name = digits_only
            elif db:
                # البحث في قاعدة بيانات الأشخاص المسجلين
                person = db.query(Person).filter(Person.full_name.ilike(f"%{target}%")).first()
                if person and person.phone:
                    phone_number = person.phone
                    contact_name = person.full_name

            if phone_number:
                clean_phone = re.sub(r"[^\d+]", "", phone_number)
                # فتح الاتصال عبر WhatsApp أو بروتوكول tel
                wa_link = f"https://api.whatsapp.com/send?phone={clean_phone}"
                subprocess.Popen(f"start {wa_link}", shell=True)
                client_action = {"type": "call", "phone": clean_phone, "url": wa_link}
                status_text = f"📞 جاري الاتصال بـ ({contact_name}) على الرقم ({phone_number})..."
            else:
                status_text = f"⚠️ لم أجد رقم هاتف مسجل لـ ({target}) في قاعدة البيانات."

        elif action == "delete_path":
            if os.path.exists(target):
                if os.path.isdir(target):
                    shutil.rmtree(target, ignore_errors=True)
                else:
                    os.remove(target)
                status_text = f"🗑️ تم حذف ({target}) نهائياً من القرص."
            else:
                status_text = f"⚠️ المسار أو الملف ({target}) غير موجود."

        elif action == "run_command":
            res = subprocess.run(["powershell", "-Command", target], capture_output=True, text=True, timeout=10)
            status_text = f"⚙️ مخرجات الأمر:\n{res.stdout or res.stderr or 'تم التنفيذ بنجاح.'}"

    except Exception as e:
        status_text = f"❌ تعذر تنفيذ الإجراء: {str(e)}"

    return {"status_text": status_text, "client_action": client_action}


def call_gemini_chat(prompt: str, history: List[ChatMessage], api_key: str, db: Optional[Session] = None) -> Dict[str, Any]:
    """استدعاء محرك Google Gemini الدائم للمحادثات الفورية مع تنفيذ الأوامر"""
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
            "parts": [{"text": EDITH_SYSTEM_PROMPT}]
        },
        "contents": contents,
        "generationConfig": {
            "temperature": 0.7,
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
                                clean_reply += f"\n\n**[إجراء النظام التكتيكي]**\n{exec_res['status_text']}"
                                raw_reply = clean_reply
                            except Exception as e:
                                print(f"[Action Error] {e}")

                        return {
                            "success": True,
                            "reply": raw_reply,
                            "model": model,
                            "client_action": client_action,
                            "engine": "Google Gemini Intelligence ⚡"
                        }
            else:
                last_error = f"Model {model} HTTP {response.status_code}: {response.text[:150]}"
        except Exception as e:
            last_error = str(e)

    raise Exception(f"Gemini Engine Error: {last_error}")


def call_gemini_vision(image_path: str, prompt: str, api_key: str, system_override: Optional[str] = None) -> Dict[str, Any]:
    """تحليل الصور الفوري بواسطة Google Gemini Vision الدائم"""
    with open(image_path, "rb") as f:
        img_bytes = f.read()

    b64_image = base64.b64encode(img_bytes).decode("utf-8")
    ext = os.path.splitext(image_path)[1].lower()
    mime_type = "image/png" if ext == ".png" else "image/jpeg"

    sys_text = system_override or EDITH_SYSTEM_PROMPT

    payload = {
        "system_instruction": {
            "parts": [{"text": sys_text}]
        },
        "contents": [
            {
                "parts": [
                    {"text": prompt or "قم بتحليل وشرح هذه الصورة باللغة العربية بالتفصيل."},
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
            "temperature": 0.4,
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
                            "engine": "Google Gemini Vision 👁️⚡"
                        }
            else:
                last_error = f"Model {model} HTTP {response.status_code}: {response.text[:150]}"
        except Exception as e:
            last_error = str(e)

    raise Exception(f"Gemini Vision Error: {last_error}")


@router.get("/status")
def get_ai_status():
    """التحقق من حالة محرك الذكاء الاصطناعي الدائم (Gemini)"""
    api_key = get_gemini_api_key()
    has_gemini = bool(api_key and len(api_key) > 10)

    return {
        "status": "ready",
        "active_engine": "Google Gemini AI (Permanent & Active ⚡)",
        "has_gemini_key": has_gemini,
        "gemini_model": DEFAULT_GEMINI_MODEL,
        "message": "EDITH Permanent Gemini Intelligence Core is operational."
    }


@router.post("/set-key")
def update_gemini_api_key(payload: ApiKeyRequest):
    """حفظ مفتاح Google Gemini API الجديد وتثبيته دائماً"""
    key = payload.api_key.strip()
    set_gemini_api_key(key)
    return {
        "success": True,
        "has_key": bool(key),
        "message": "تم حفظ وتثبيت مفتاح Google Gemini بنجاح دائم!"
    }


@router.post("/chat")
def chat_with_edith(payload: ChatRequest, db: Session = Depends(get_db)):
    """إرسال استفسار فوري لمساعد إيديث الذكي عبر Gemini مع دعم الأوامر والاتصال"""
    user_prompt = payload.prompt.strip()
    if not user_prompt:
        raise HTTPException(status_code=400, detail="الرجاء كتابة رسالة للمساعد.")

    api_key = get_gemini_api_key()

    if not api_key:
        return {
            "success": False,
            "reply": "يرجى إدخال مفتاح Google Gemini المجاني في أعلى الصفحة لحفظه وتفعيل المحرك دائماً.",
            "error": "No API Key"
        }

    try:
        return call_gemini_chat(user_prompt, payload.history or [], api_key, db)
    except Exception as e:
        return {
            "success": False,
            "reply": f"تنبيه EDITH: حدث خطأ أثناء الاتصال بمحرك Gemini ({str(e)}).",
            "error": str(e)
        }


@router.post("/vision")
def analyze_vision_frame(
    prompt: str = Form("قم بوصف محتويات هذه الصورة بالتفصيل واشرح ما تراه باللغة العربية."),
    photo: UploadFile = File(...)
):
    """تحليل صورة مرفوعة أو لقطة من الكاميرا بواسطة Google Gemini Vision الدائم"""
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
                print(f"[Gemini Vision Error] {e}")
                return {"success": False, "message": f"خطأ في التحليل: {str(e)}"}

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
    المساعد الصوتي التفاعلي الشامل (EDITH Universal Voice Assistant):
    1. يتفاعل مع أي سؤال صوتي (محادثة، أسئلة عامة، ذكاء).
    2. ينفذ أوامر فتح التطبيقات والمواقع ("افتح اليوتيوب / افتح كروم / افتح الآلة الحاسبة").
    3. ينفذ أوامر الاتصال بالأشخاص ("اتصل على فلان / اتصل برقم كذا").
    4. ينفذ أوامر إغلاق التطبيقات ("اقفل كروم / اقفل الآلة الحاسبة").
    5. يفحص الكاميرا ويتعرف على الوجوه المسجلة ويشرح المشهد صوتياً عند الحاجة.
    """
    api_key = get_gemini_api_key()
    if not api_key:
        return {
            "success": False,
            "spoken_text": "يرجى تفعيل مفتاح Gemini في أعلى الصفحة لتفعيل المساعد الصوتي الذكي.",
            "prompt": voice_prompt
        }

    file_path = None
    biometric_faces = []
    detected_people_info = []

    # إذا تم إرسال لقطة من الكاميرا
    if photo and photo.filename:
        file_ext = os.path.splitext(photo.filename)[1] or ".jpg"
        unique_filename = f"voice_vis_{uuid.uuid4().hex}{file_ext}"
        file_path = os.path.join(TEMP_AI_DIR, unique_filename)

        with open(file_path, "wb") as buffer:
            shutil.copyfileobj(photo.file, buffer)

        # فحص التعرف البيومتري
        try:
            biometric_faces = recognize_all_faces(file_path, db)
            for face in biometric_faces:
                if face.get("found") and face.get("person"):
                    p = face["person"]
                    score_pct = round(face["score"] * 100, 1)
                    detected_people_info.append(
                        f"الاسم: {p['full_name']} ({p.get('person_type', 'شخص مسجل')} - قسم {p.get('department', 'عام')}) بنسبة تطابق {score_pct}%"
                    )
        except Exception as e:
            print(f"[Biometric Error] {e}")

    try:
        # فحص هل السؤال يتعلق بالرؤية البصرية
        is_visual_query = any(k in voice_prompt for k in ["قدامي", "شايف", "مين", "كاميرا", "صورة", "مشهد", "ورقة", "شخص", "اشرح", "حلل"])

        client_action = None
        action_status = ""

        telemetry_info = get_live_system_metrics()

        # إذا كانت الصورة متوفرة والسؤال بصري أو عن المشاعر
        if file_path and is_visual_query:
            biometric_context = ""
            if detected_people_info:
                biometric_context = "بيانات التعرف البيومتري على الوجوه في الصورة: " + " | ".join(detected_people_info)
            else:
                biometric_context = "التعرف البيومتري: لم يتم التعرف على أي وجوه مسجلة في قاعدة البيانات."

            system_voice_instruction = f"""أنت E.D.I.T.H. - المساعد الصوتي والتكتيكي الذكي وتتحدث للمستخدم عبر الصوت الآن.
المستخدم سألك صوتياً: "{voice_prompt}"
بيانات نظام الكاميرا والتعرف على الوجوه الحالية:
{biometric_context}
بيانات موارد الجهاز الحالية:
{telemetry_info.get('summary_text', '')}

المطلوب منك:
1. الإجابة باللغة العربية بصوت طبيعي ومباشر ومختصر ومشوق في 2-4 جمل.
2. إذا كان هناك شخص تم التعرف عليه في البيانات، اذكره باسمه ودوره مباشرة بثقة، واذكر تعابير وجهه ومشاعره الظاهرة (مثل مبتسم، هادئ، مركز، متفاجئ).
3. اشرح ما تراه أمام الكاميرا باختصار واحترافية."""

            gemini_res = call_gemini_vision(file_path, voice_prompt, api_key, system_override=system_voice_instruction)
            spoken_text = gemini_res.get("description", "")

        else:
            # إذا كان السؤال عن حالة النظام أو موارد الجهاز، نضيف قراءات الحساسات الفعلية
            is_telemetry_query = any(k in voice_prompt for k in ["حالة", "نظام", "جهاز", "معالج", "رامات", "ذاكرة", "بطارية", "حرارة", "أداء", "telemetry", "diagnostics", "status"])
            effective_prompt = voice_prompt
            if is_telemetry_query:
                effective_prompt = f"{voice_prompt}\n(بيانات موارد الجهاز الحالية الحقيقية: {telemetry_info.get('summary_text', '')})"

            chat_res = call_gemini_chat(effective_prompt, [], api_key, db)
            spoken_text = chat_res.get("reply", "")
            client_action = chat_res.get("client_action")

        # تنظيف الرد الصوتي من كتل الأكشن البرمجية ليكون سلساً في النطق
        clean_spoken = re.sub(r"```action[\s\S]*?```", "", spoken_text)
        clean_spoken = clean_spoken.replace("**[إجراء النظام التكتيكي]**", "").strip()

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
    """جلب إحصائيات الموارد الحية لواجهة HUD التكتيكية"""
    return get_live_system_metrics()




