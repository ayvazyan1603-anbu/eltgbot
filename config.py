import json
import os
import sys
from dotenv import load_dotenv

# Настройка кодировки для Windows консоли
if sys.platform == "win32":
    try:
        sys.stdout.reconfigure(encoding="utf-8")
        sys.stderr.reconfigure(encoding="utf-8")
    except Exception:
        pass

load_dotenv()

BOT_TOKEN = os.getenv("BOT_TOKEN", "").strip()
ADMIN_IDS_RAW = os.getenv("ADMIN_IDS", "").strip()

ADMIN_IDS: set[int] = set()
if ADMIN_IDS_RAW:
    for aid in ADMIN_IDS_RAW.split(","):
        aid = aid.strip()
        if aid.isdigit():
            ADMIN_IDS.add(int(aid))

# Настройки FreeKassa
FK_MERCHANT_ID = os.getenv("FK_MERCHANT_ID", "").strip()
FK_SECRET_1 = os.getenv("FK_SECRET_1", "").strip()
FK_SECRET_2 = os.getenv("FK_SECRET_2", "").strip()
FK_API_KEY = os.getenv("FK_API_KEY", "").strip()
# Railway автоматически передает порт в переменную PORT
WEBHOOK_PORT = int(os.getenv("PORT") or os.getenv("WEBHOOK_PORT") or 8080)
WEBHOOK_HOST = os.getenv("WEBHOOK_HOST", "0.0.0.0").strip()

def is_admin(user_id: int) -> bool:
    return user_id in ADMIN_IDS

# Загрузка текстов из texts.json
TEXTS_FILE = os.path.join(os.path.dirname(__file__), "texts.json")

def load_texts() -> dict:
    if os.path.exists(TEXTS_FILE):
        with open(TEXTS_FILE, "r", encoding="utf-8") as f:
            return json.load(f)
    return {}

TEXTS = load_texts()

def get_text(path: str, default: str = "", **kwargs) -> str:
    """
    Получение текста по ключу (например 'welcome_text' или 'order.step_name')
    с автоматической подстановкой аргументов формата.
    """
    keys = path.split(".")
    val = TEXTS
    for k in keys:
        if isinstance(val, dict) and k in val:
            val = val[k]
        else:
            return default
    if isinstance(val, str):
        try:
            return val.format(**kwargs)
        except Exception:
            return val
    return str(val)

def get_button(btn_key: str, default: str = "") -> str:
    return TEXTS.get("buttons", {}).get(btn_key, default or btn_key)
