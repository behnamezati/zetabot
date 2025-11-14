#
# ------------------------------------------------------------
# فایل: app/safety_service.py
# پیاده‌سازی منطق ایمنی (Safe Mode، Anti-Spam و Cooldown)
# ------------------------------------------------------------
#

import time
from typing import Dict, List

# وارد کردن تنظیمات V1.0
from config.settings import (
    MAX_CONSECUTIVE_LOSSES, MAX_TRADES_PER_MINUTE
)
# وارد کردن ماژول‌های وضعیت و گزارش‌دهی
from app.state_manager import state_manager
from infra.telegram_bot import telegram_reporter
# وارد کردن فرم‌های اطلاعاتی
from domain.models import MarketSafetyMode

# --- مقادیر ثابت زمان‌بندی ایمنی ---
# (اینها را می‌توان به settings.py منتقل کرد)
ANTI_SPAM_COOLDOWN_SECONDS: int = 15 # مدت زمان استراحت ضد اسپم (ثانیه)
EXIT_COOLDOWN_SECONDS: int = 30     # مدت زمان استراحت بعد از هر خروج (ثانیه)

class SafetyService:
    """
    سرویس مدیریت قوانین ریسک پیشگیرانه.
    (این فایل جایگزین منطق ایمنی است که قبلاً در state_manager بود)
    """

    def check_entry_allowed(self, symbol: str) -> bool:
        """
        چک لیست نهایی ایمنی قبل از ارسال سفارش (جلوگیری از ورود).
        """
        if symbol not in state_manager.market_states:
            return False # اگر نماد مدیریت نمی شود

        state = state_manager.market_states[symbol]
        current_time = int(time.time())

        # --- ۱. قانون Safe Mode (۳ ضرر متوالی) ---
        if state.consecutive_losses >= MAX_CONSECUTIVE_LOSSES:
            if state.safety_mode != MarketSafetyMode.SAFE_MODE:
                # اگر ربات تازه وارد Safe Mode شده، گزارش بده
                state.safety_mode = MarketSafetyMode.SAFE_MODE
                print(f"ALARM: {symbol} وارد SAFE_MODE شد (۳ ضرر متوالی).")
                telegram_reporter.send_safety_report(symbol, 'SAFE_MODE')
            return False # ورود ممنوع

        # --- ۲. قانون ضد اسپم (۸ ترید در دقیقه) ---
        # ابتدا ورودی‌های قدیمی‌تر از ۶۰ ثانیه را پاک کن
        state.entry_timestamps = [t for t in state.entry_timestamps if current_time - t < 60]
        
        if len(state.entry_timestamps) >= MAX_TRADES_PER_MINUTE:
            if state.safety_mode != MarketSafetyMode.COOLDOWN:
                # اگر تازه وارد Cooldown ضد اسپم شده، گزارش بده
                state.safety_mode = MarketSafetyMode.COOLDOWN
                state.last_cooldown_start = current_time # زمان شروع استراحت
                print(f"ALARM: {symbol} وارد COOLDOWN ضد اسپم شد (۸ ترید در دقیقه).")
                telegram_reporter.send_safety_report(symbol, 'COOLDOWN')
            return False # ورود ممنوع

        # --- ۳. قانون استراحت (Cooldown) ---
        if state.safety_mode == MarketSafetyMode.COOLDOWN:
            # (ما استراحت ضد اسپم (۱۵ ثانیه) و استراحت پس از خروج (۳۰ ثانیه) داریم)
            # (در V1.0 برای سادگی، هر دو را ۳۰ ثانیه در نظر می‌گیریم)
            
            if current_time - getattr(state, 'last_cooldown_start', 0) < EXIT_COOLDOWN_SECONDS:
                return False # هنوز در حال استراحت است
            else:
                # زمان استراحت تمام شد
                state.safety_mode = MarketSafetyMode.ACTIVE
        
        return True

    def update_state_on_exit(self, symbol: str, pnl_usdt: float):
        """ وضعیت ایمنی را پس از بسته شدن یک معامله به‌روزرسانی می‌کند. """
        
        if symbol not in state_manager.market_states:
            return

        state = state_manager.market_states[symbol]
        current_time = int(time.time())

        # ۱. تنظیم Cooldown ۳۰ ثانیه‌ای پس از هر خروج
        state.safety_mode = MarketSafetyMode.COOLDOWN
        state.last_cooldown_start = current_time

        # ۲. به‌روزرسانی شمارنده ضرر متوالی
        if pnl_usdt < 0:
            state.consecutive_losses += 1
        else:
            state.consecutive_losses = 0 # ریست در صورت سود


# --- نمونه سازی ---
safety_service = SafetyService()
