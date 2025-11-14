#
# ------------------------------------------------------------
# فایل: domain/entry_policy.py
# (V2.0 - پیاده سازی منطق Trend/Range شما - بدون ML)
# ------------------------------------------------------------
#
from typing import Optional, List, Dict

# فعلاً از این دو استفاده نمی‌کنیم؛ برای تمیزی کد کامنت‌شون می‌کنیم
# from domain.models import MarketState, Position
# from config.settings import INITIAL_POSITION_SIZE_USDT

# --- مقادیر ثابت استراتژی ---

# اختلاف EMA به درصد، برای تشخیص Range/Trend
TREND_EMA_DISTANCE_PCT = 0.5   # قبلاً 0.10 بود، خیلی ریز بود

# فیلتر RSI در حالت Trend
RSI_TREND_MIN = 45.0
RSI_TREND_MAX = 68.0

# حد پایین RSI برای Range
RSI_RANGE_MIN = 30.0

# فیلتر ATR برای تشخیص Range/Trend (به درصد)
RANGE_MAX_ATR_PCT = 2.0        # زیر این، بازار می‌تونه Range باشد
TREND_MIN_ATR_PCT = 0.5        # بالاتر از این، بیشتر شبیه Trend است


class MarketMode:
    TREND = 1
    RANGE = 2

def _check_market_regime(atr_pct: float, indicators: dict, current_price: float) -> MarketMode:
    """
    تعیین رژیم بازار (Trend یا Range) با ترکیب EMA و ATR.
    """
    ema8 = indicators.get("EMA8", 0.0)
    ema21 = indicators.get("EMA21", 0.0)

    if ema8 == 0.0 or ema21 == 0.0 or current_price == 0.0:
        # اگر دیتا ناقص باشد، محافظه‌کارانه Trend فرض می‌کنیم
        return MarketMode.TREND

    # اختلاف EMA را به درصد نسبت به EMA21 حساب می‌کنیم
    ema_distance_pct = abs(ema8 - ema21) / ema21 * 100.0

    # ۱) اگر ATR کم و فاصله EMA هم کم باشد → Range
    if atr_pct < RANGE_MAX_ATR_PCT and ema_distance_pct < TREND_EMA_DISTANCE_PCT:
        return MarketMode.RANGE

    # ۲) اگر ATR و فاصله EMA هر دو بالاتر از حداقل ترند باشند → Trend
    if atr_pct >= TREND_MIN_ATR_PCT and ema_distance_pct >= TREND_EMA_DISTANCE_PCT:
        return MarketMode.TREND

    # ۳) بقیه حالت‌ها: محافظه‌کارانه Trend
    return MarketMode.TREND
def _evaluate_trend_entry(current_price: float, indicators: dict) -> bool:
    """ 
    (V2.0) منطق ورود در حالت روند (Trend).
    """
    ema8 = indicators.get('EMA8', 0)
    ema21 = indicators.get('EMA21', 0)
    rsi14 = indicators.get('RSI14', 50)
    
    # 1. جهت روند: روند صعودی است (Baseline)
    if ema8 <= ema21:
        return False
        
    # 2. فیلتر RSI: در محدوده مناسب باشد (نه اشباع)
    if rsi14 < RSI_TREND_MIN or rsi14 > RSI_TREND_MAX:
        return False
        
    # 3. ماشه لحظه‌ای (Trigger): قیمت لحظه‌ای باید بالای EMA8 باشد
    if current_price <= ema8:
        return False
    
    return True

def _evaluate_range_entry(current_price: float, indicators: dict) -> bool:
    """
    منطق ورود در حالت رنج (Range).
    """
    bb_lower = indicators.get("BB_LOWER", 0.0)
    rsi14 = indicators.get("RSI14", 50.0)

    if bb_lower == 0.0:
        return False  # اندیکاتور آماده نیست

    # ۱. قیمت باید نزدیک باند پایین باشد (نه فقط 0.05%)
    # 0.3% بالاتر از باند پایین را قبول می‌کنیم
    if current_price > bb_lower * 1.003:
        return False

    # ۲. RSI باید واقعا ناحیه اشباع فروش باشد
    if rsi14 >= RSI_RANGE_MIN:
        return False

    return True
# --- تابع اصلی (فراخوانی شده توسط bot_loop) ---

def get_final_signal(
    current_price: float,
    indicators: Dict[str, float],
    candles: Optional[List[dict]] = None,
) -> Optional[str]:
    atr_pct = indicators.get("ATR_PCT", 0.0)

    # فیلتر اولیه روی ATR (بازار خیلی مرده یا بیش‌ازحد وحشی را رد می‌کنیم)
    MIN_ATR_PCT = 0.2
    MAX_ATR_PCT = 5.0
    if atr_pct < MIN_ATR_PCT or atr_pct > MAX_ATR_PCT:
        return None

    regime = _check_market_regime(atr_pct, indicators, current_price)    
    # 2. بررسی قوانین Trend/Range
    entry_ok = False
    if regime == MarketMode.TREND:
        entry_ok = _evaluate_trend_entry(current_price, indicators)
    else: # MarketMode.RANGE
        entry_ok = _evaluate_range_entry(current_price, indicators)

    if not entry_ok:
        return None # سیگنال اولیه شکست خورد

    # 3. (منطق ML حذف شد)

    # 4. (منطق ATR Sizing حذف شد، از 3$ ثابت استفاده می‌شود)
    # position_size_usdt = INITIAL_POSITION_SIZE_USDT 
    
    # 5. صدور سیگنال نهایی
    return "BUY"
