#
# ------------------------------------------------------------
# فایل: config/settings.py
# (V2.2 - استفاده مستقیم از کلیدهای API و DATA_DIR ارائه شده توسط شما)
# ------------------------------------------------------------
#
import os
from typing import List

# --- 1. تنظیمات API و احراز هویت (بر اساس ورودی شما) ---
EXCHANGE_ID: str = "lbank"
API_KEY: str = "a206f8f1-ad82-4339-9823-4517d1d28bcb"
API_SECRET: str = "9C80D37F9729BA228E8DAEEE38F97A8C"
API_PASSWORD: str = "" 

# --- 2. تنظیمات تلگرام (بر اساس ورودی شما) ---
TELEGRAM_BOT_TOKEN: str = "7858697399:AAFkvumYZRTczNA0CpBNCTNCEQ4m5i-y_50"
# (ما از لیست برای مدیریت آسان‌تر استفاده می کنیم)
ADMIN_CHAT_IDS: List[str] = [
    "5188313696",
    "8043428280",
    "569233368"
]
# (مسیرهای ارسال پیام)
ROUTE_URGENT_TRADE: List[str] = ADMIN_CHAT_IDS
ROUTE_STATS_BACKUP: List[str] = ADMIN_CHAT_IDS
ROUTE_DAILY_SUMMARY: List[str] = ADMIN_CHAT_IDS

# --- 3. تنظیمات عمومی و حالت اجرا (بر اساس ورودی شما) ---
PAPER_MODE: bool = True # (LIVE_MODE=False شما به PAPER_MODE=True تبدیل شد)
DATA_DIR: str = "./data"    # (مسیر ذخیره داده‌ها)
BASE_SYMBOL: str = "BTC/USDT" 
TIME_FRAME: str = "1m"
CANDLE_BUFFER_SIZE: int = 100 
VIRTUAL_BALANCE_START: float = 200.0 # (بالانس دمو شما)
LOG_QUEUE_SIZE: int = 1000 # (مورد نیاز persistence_service)


# --- 4. تنظیمات ریسک و مالی (استراتژی V2.0 شما) ---
INITIAL_POSITION_SIZE_USDT: float = 3.0 # (حجم ثابت ۳ دلار)
INITIAL_SL_PCT: float = 0.01 # (1.0% حد ضرر)
FRICTION_COST_PCT: float = 0.003 # (0.3% هزینه)

# --- 5. تنظیمات خروج پله‌ای (R:R 1:1.5 شما) ---
FINAL_TP_PCT: float = 0.015               # 1.5% (حد سود نهایی)
RISK_FREE_TRIGGER_PCT: float = 0.0045   # 0.45% (ماشه ریسک-فری)
TP_STEP_1_TRIGGER_PCT: float = 0.0090   # 0.90% (ماشه قفل سود)
TP_STEP_1_SL_LOCK_PCT: float = 0.0045   # 0.45% (مقصد قفل سود)

# --- 6. تنظیمات ضد اسپم (قانون ۸ ترید شما) ---
MAX_ENTRIES_PER_MINUTE: int = 8 
FAST_COOLDOWN_SECONDS: int = 15 

# --- 7. تنظیمات ایمنی (جدید V2.1) ---
MAX_CONSECUTIVE_LOSSES: int = 3 # (۳ ضرر متوالی)
