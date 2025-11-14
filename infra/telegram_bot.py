#
# ------------------------------------------------------------
# فایل: infra/telegram_bot.py
# (FIX V1.5 - افزودن تابع send_system_report برای پیام‌های غیر-خطا)
# ------------------------------------------------------------
#

import requests 
from typing import List, Optional

# وارد کردن تنظیمات
from config.settings import (
    TELEGRAM_BOT_TOKEN, ROUTE_URGENT_TRADE, 
    ROUTE_STATS_BACKUP, ROUTE_DAILY_SUMMARY
)

class TelegramReporter:
    
    def __init__(self):
        if not TELEGRAM_BOT_TOKEN:
            print("TOKEN تلگرام یافت نشد. سرویس تلگرام غیرفعال است.")
            self.bot_token = None
            self.base_url = ""
            return

        self.bot_token = TELEGRAM_BOT_TOKEN
        self.base_url = f"https://api.telegram.org/bot{self.bot_token}/sendMessage"
        print("✅ سرویس تلگرام (Requests - V1.5) فعال شد.")

    
    def send_message_to_chat_ids(
        self, 
        chat_ids: List[str], 
        message_text: str, 
        parse_mode: Optional[str] = "HTML"
    ):
        """ 
        پیام را با استفاده از requests (همزمان و بدون خطا) ارسال می کند.
        """
        if not self.bot_token:
            return 

        for chat_id in chat_ids:
            if not chat_id: continue
            
            payload = {
                'chat_id': chat_id,
                'text': message_text,
                'parse_mode': parse_mode,
                'disable_web_page_preview': True
            }
            
            try:
                response = requests.post(self.base_url, data=payload, timeout=5)
                if not response.json().get('ok', False):
                     print(f"❌ خطای API تلگرام: {response.text}")
                     
            except requests.exceptions.Timeout:
                print(f"❌ خطای ارسال پیام تلگرام (Timeout) به {chat_id}")
            except requests.exceptions.RequestException as e:
                print(f"❌ خطای ارسال پیام تلگرام (Requests) به {chat_id}: {e}")

    # --- توابع گزارش‌دهی ---

    # --- (تابع جدید V1.5) ---
    def send_system_report(self, title: str, message: str):
        """ گزارش‌های سیستمی (مانند راه‌اندازی) """
        msg = f"ℹ️ <b>ZetaBot V1.5 Info</b> ℹ️\n\n<b>{title}</b>\n{message}"
        self.send_message_to_chat_ids(ROUTE_URGENT_TRADE, msg, "HTML")

    def send_entry_report(self, position):
        """ گزارش ورود به معامله """
        msg = (
            f"🚀 <b>ورود جدید</b> (Paper Mode)\n\n"
            f"📈 <b>نماد:</b> {position.symbol}\n"
            f"💵 <b>قیمت ورود:</b> {position.entry_price_actual}\n"
            f"💰 <b>حجم:</b> {position.initial_size_usdt:.2f} USDT"
        )
        self.send_message_to_chat_ids(ROUTE_URGENT_TRADE, msg, "HTML")

    def send_exit_report(self, position, exit_price, pnl_usdt, reason):
        """ گزارش خروج از معامله """
        pnl_pct = (pnl_usdt / position.initial_size_usdt) * 100
        duration = "N/A" 
        
        emoji = "✅" if pnl_usdt >= 0 else "⛔️"
        
        msg = (
            f"{emoji} <b>خروج از پوزیشن</b> (Paper Mode)\n\n"
            f"📈 <b>نماد:</b> {position.symbol}\n"
            f"Reason: {reason}\n\n"
            f"Entry: {position.entry_price_actual}\n"
            f"Exit: {exit_price}\n"
            f"Duration: {duration}\n\n"
            f"💰 <b>P&L (USDT):</b> {pnl_usdt:+.2f} $\n"
            f"📊 <b>P&L (%):</b> {pnl_pct:+.2f} %"
        )
        self.send_message_to_chat_ids(ROUTE_URGENT_TRADE, msg, "HTML")

    def send_error_report(self, title: str, message: str):
        """ گزارش خطاهای سیستمی """
        msg = f"⚠️ <b>ZetaBot V1.5 Error</b> ⚠️\n\n<b>{title}</b>\n{message}"
        self.send_message_to_chat_ids(ROUTE_URGENT_TRADE, msg, "HTML")

    def send_safety_report(self, symbol: str, mode: str):
        """ گزارش فعال شدن حالت ایمنی """
        msg = ""
        if mode == 'SAFE_MODE':
            msg = f"🔒 <b>حالت ایمنی فعال شد</b> 🔒\n\nنماد: {symbol}\nبه دلیل ۳ ضرر متوالی، معاملات متوقف شد."
        elif mode == 'COOLDOWN':
            msg = f"🚦 <b>محدودیت فرکانس</b> 🚦\n\nنماد: {symbol}\nتعداد معاملات بیش از حد مجاز (Anti-Spam)."
        
        self.send_message_to_chat_ids(ROUTE_URGENT_TRADE, msg, "HTML")

# --- نمونه سازی ---
telegram_reporter = TelegramReporter()
