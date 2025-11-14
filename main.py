#
# ------------------------------------------------------------
# فایل: main.py
# نقطه ورود اصلی برای اجرای ربات ZetaBot (V1.0 - همزمان)
# ------------------------------------------------------------
#

import sys
import os
import threading
import time 

# اضافه کردن پوشه های پروژه به مسیر پایتون
current_dir = os.path.dirname(os.path.abspath(__file__))
if current_dir not in sys.path:
    sys.path.append(current_dir)
sys.path.append(os.path.join(current_dir, 'app'))
sys.path.append(os.path.join(current_dir, 'domain'))
sys.path.append(os.path.join(current_dir, 'infra'))
sys.path.append(os.path.join(current_dir, 'utils'))
sys.path.append(os.path.join(current_dir, 'config'))

# (ما دیگر به Application تلگرام نیازی نداریم)
from infra.telegram_bot import telegram_reporter 
from app.bot_loop import bot_loop # (این فایل را در قدم بعدی می سازیم)

if __name__ == "__main__":
    print("🚀 ZetaBot V1.0: شروع اجرای ربات (روش همزمان)...")
    
    try:
        # اجرای BotLoop به صورت مستقیم در نخ اصلی
        # (دقیقا مانند ربات قبلی شما)
        bot_loop.start_bot()
        
    except KeyboardInterrupt:
        bot_loop.stop_bot() # توقف ایمن ربات
        print("\n👋 ZetaBot: توقف دستی ربات توسط کاربر.")
    except Exception as e:
        print(f"\n❌ خطای بحرانی در main.py: {e}")
