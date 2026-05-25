import os
import warnings
from dotenv import load_dotenv

load_dotenv()

TELEGRAM_BOT_TOKEN = os.getenv("TELEGRAM_BOT_TOKEN", "")
TELEGRAM_CHAT_ID = os.getenv("TELEGRAM_CHAT_ID", "")

if not TELEGRAM_BOT_TOKEN:
    raise ValueError("請在 .env 檔案設定 TELEGRAM_BOT_TOKEN")

if not TELEGRAM_CHAT_ID:
    warnings.warn("警告：TELEGRAM_CHAT_ID 未設定，部分通知功能可能無法正常運作")
