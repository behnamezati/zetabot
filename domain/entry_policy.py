#
# ------------------------------------------------------------
# فایل: domain/entry_policy.py
# (V2.0 - پیاده سازی منطق Trend/Range شما - بدون ML)
# ------------------------------------------------------------
#
from typing import Optional, List, Dict
from domain.models import MarketState, Position
from config.settings import INITIAL_POSITION_SIZE_USDT # <--- استفاده از 3$ ثابت

# --- مقادیر ثابت استراتژی شما ---
TREND_EMA_DISTANCE_PCT = 0.10 # (0.10% فاصله EMA برای تشخیص رنج)
RSI_TREND_MIN = 45.0
RSI_TREND_MAX = 68.0
RSI_RANGE_MIN = 30.0           

class MarketMode:
    TREND = 1
    RANGE = 2

def _check_market_regime(atr_pct: float, indicators: dict, current_price: float) -> MarketMode:
    """
    تعیین رژیم بازار (Trend یا Range).
    """
    ema8 = indicators.get('EMA8', 0)
    ema21 = indicators.get('EMA21', 0)
    
    if ema8 == 0 or ema21 == 0 or current_price == 0:
        return MarketMode.TREND # پیش‌فرض

    # محاسبه فاصله EMA (بر اساس فایل شما)
    ema_distance_pct = abs(ema8 - ema21) / current_price 
    
    if ema_distance_pct < (TREND_EMA_DISTANCE_PCT / 100.0):
        return MarketMode.RANGE
    
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
    """ (V2.0) منطق ورود در حالت رنج (Range). """
    
    bb_lower = indicators.get('BB_LOWER', 0)
    rsi14 = indicators.get('RSI14', 50)
    
    if bb_lower == 0: return False # اندیکاتور آماده نیست
    
    # 1. لمس باند پایین: قیمت لحظه‌ای باید به باند پایین BB نزدیک باشد
    if current_price > (bb_lower * 1.0005): # (کمی بالاتر از باند)
        return False
        
    # 2. کراس RSI: (RSI باید زیر 30 باشد)
    if rsi14 >= RSI_RANGE_MIN: 
        return False 
        
    return True

# --- تابع اصلی (فراخوانی شده توسط bot_loop) ---

def get_final_signal(
    symbol: str, 
    current_price: float, 
    candles: List[list], # (دیگر لازم نیست، چون اندیکاتورها محاسبه شده‌اند)
    indicators: dict,
    is_position_open: bool
) -> Optional[str]:
    """ 
    (V2.0) سرویس اصلی برای صدور سیگنال نهایی ورود.
    """
    
    # اگر پوزیشن باز داریم، سیگنال ورود نده
    if is_position_open:
        return None
        
    # --- (منطق V1.6 SMA Crossover حذف شد) ---
    
    # --- (منطق V2.0 شما اضافه شد) ---
    atr_pct = indicators.get('ATR_PCT', 0.0)
    
    # 1. تشخیص رژیم بازار
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
