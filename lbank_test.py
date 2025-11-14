#
# ------------------------------------------------------------
# فایل: lbank_test.py
# تست مستقل و ساده اتصال به LBank (برای دیباگ کردن API Key و IP)
# ------------------------------------------------------------
#

import ccxt
import os

# --- کلیدهای API (برای تست مستقیم) ---
# (اینها از فایل .env شما کپی شده‌اند)
API_KEY    = "a206f8f1-ad82-4339-9823-4517d1d28bcb"
API_SECRET = "9C80D37F9729BA228E8DAEEE38F97A8C"
EXCHANGE_ID = "lbank"

print(f"⏳ در حال اتصال به {EXCHANGE_ID} با API Key: {API_KEY[:8]}...")

# --- ۱. تنظیمات اتصال CCXT ---
config = {
    'apiKey': API_KEY,
    'secret': API_SECRET,
    'enableRateLimit': True,
    'options': {'defaultType': 'spot'}
}

try:
    exchange_class = getattr(ccxt, EXCHANGE_ID)
    exchange = exchange_class(config)
    
    # --- ۲. تست احراز هویت (مهم‌ترین بخش) ---
    print("⏳ در حال تلاش برای احراز هویت و دریافت بالانس (fetch_balance)...")
    
    # این دستور اگر IP یا کلید اشتباه باشد، خطا می‌دهد
    balance_info = exchange.fetch_balance()
    
    print("\n" + "="*30)
    print("✅✅✅ تست اتصال موفقیت آمیز بود! ✅✅✅")
    print("="*30)
    print("API Key و IP آدرس شما توسط LBank تأیید شد.")
    print(f"موجودی USDT شما: {balance_info.get('USDT', {}).get('free', 'N/A')}")

except ccxt.AuthenticationError as e:
    print("\n" + "="*30)
    print("❌❌❌ خطای احراز هویت (AuthenticationError) ❌❌❌")
    print("="*30)
    print("دلیل: LBank کلید API یا امضای شما را رد کرد.")
    print("۱. مطمئن شوید API Key و Secret Key دقیقاً درست هستند.")
    print(f"۲. مطمئن شوید IP سرور شما ({os.popen('curl -s ifconfig.me').read().strip()}) دقیقاً با IP ثبت شده در LBank ({'152.228.206.120'}) مطابقت دارد.")
    print(f"متن کامل خطا: {e}")

except Exception as e:
    print("\n" + "="*30)
    print(f"❌❌❌ خطای عمومی اتصال ({type(e).__name__}) ❌❌❌")
    print("="*30)
    print(f"متن کامل خطا: {e}")
