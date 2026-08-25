import os
import cv2
import base64
import requests
import urllib3
from typing import Dict, Any, Optional

from app.config import get_gemini_api_key

urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)

OUTPUT_FOLDER = os.path.abspath(
    os.path.join(os.path.dirname(__file__), "..", "..", "captures")
)
os.makedirs(OUTPUT_FOLDER, exist_ok=True)

GEMINI_MODELS = ["gemini-3.5-flash", "gemini-flash-latest", "gemini-3.7-flash"]


def analyze_image_file(image_path: str, prompt: str = "قم بوصف محتويات هذه الصورة بالتفصيل واشرح ما تراه باللغة العربية.") -> Dict[str, Any]:
    """تحليل صورة موجودة باستخدام محرك Google Gemini Vision الفائق"""
    if not os.path.exists(image_path):
        return {
            "success": False,
            "message": "الصورة غير موجودة في المسار المحدد."
        }

    api_key = get_gemini_api_key()
    if not api_key:
        return {
            "success": False,
            "message": "مفتاح Google Gemini API غير متوفر. يرجى إدخال المفتاح في الداشبورد."
        }

    with open(image_path, "rb") as f:
        img_bytes = f.read()

    b64_image = base64.b64encode(img_bytes).decode("utf-8")
    ext = os.path.splitext(image_path)[1].lower()
    mime_type = "image/png" if ext == ".png" else "image/jpeg"

    payload = {
        "contents": [
            {
                "parts": [
                    {"text": prompt},
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
            res = requests.post(url, json=payload, verify=False, timeout=20)
            if res.status_code == 200:
                data = res.json()
                candidates = data.get("candidates", [])
                if candidates and len(candidates) > 0:
                    parts = candidates[0].get("content", {}).get("parts", [])
                    if parts:
                        return {
                            "success": True,
                            "image": image_path,
                            "prompt": prompt,
                            "description": parts[0].get("text", ""),
                            "engine": "Google Gemini Vision 👁️⚡"
                        }
            else:
                last_error = f"Model {model} returned {res.status_code}"
        except Exception as e:
            last_error = str(e)

    return {
        "success": False,
        "message": f"حدث خطأ أثناء معالجة الرؤية: {last_error}"
    }


def analyze_scene(prompt: str = "قم بوصف محتويات هذه الصورة بالتفصيل واشرح ما تراه باللغة العربية.") -> Dict[str, Any]:
    """التقاط لقطة مباشرة من الكاميرا الموصلة بالجهاز وتحليلها بواسطة Gemini"""
    camera = cv2.VideoCapture(0)

    if not camera.isOpened():
        return {
            "success": False,
            "message": "لم يتم العثور على الكاميرا المحلية."
        }

    success, frame = camera.read()
    camera.release()

    if not success:
        return {
            "success": False,
            "message": "تعذر التقاط صورة من الكاميرا."
        }

    image_path = os.path.join(OUTPUT_FOLDER, "capture.jpg")
    cv2.imwrite(image_path, frame)

    return analyze_image_file(image_path, prompt)