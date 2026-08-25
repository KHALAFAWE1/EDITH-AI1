import os
from dotenv import load_dotenv

# تحميل ملف .env إن وُجد
ENV_PATH = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "..", ".env"))
load_dotenv(ENV_PATH)

GEMINI_API_KEY = os.getenv("GEMINI_API_KEY", "")
DEFAULT_GEMINI_MODEL = os.getenv("GEMINI_MODEL", "gemini-3.5-flash")


def get_gemini_api_key() -> str:
    global GEMINI_API_KEY
    if not GEMINI_API_KEY:
        load_dotenv(ENV_PATH)
        GEMINI_API_KEY = os.getenv("GEMINI_API_KEY", "")
    return GEMINI_API_KEY


def set_gemini_api_key(new_key: str):
    global GEMINI_API_KEY
    GEMINI_API_KEY = new_key.strip()
    # حفظ المفتاح في ملف .env حتى يبقى محفوظاً دائماً
    try:
        lines = []
        if os.path.exists(ENV_PATH):
            with open(ENV_PATH, "r", encoding="utf-8") as f:
                lines = f.readlines()
        
        updated = False
        new_lines = []
        for line in lines:
            if line.startswith("GEMINI_API_KEY="):
                new_lines.append(f"GEMINI_API_KEY={GEMINI_API_KEY}\n")
                updated = True
            else:
                new_lines.append(line)
        
        if not updated:
            new_lines.append(f"GEMINI_API_KEY={GEMINI_API_KEY}\n")
            
        with open(ENV_PATH, "w", encoding="utf-8") as f:
            f.writelines(new_lines)
    except Exception as e:
        print(f"[EDITH Config Error] Failed to write to .env: {e}")
