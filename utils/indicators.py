#
# ------------------------------------------------------------
# فایل: utils/indicators.py
# (جدید V2.0 - محاسبه اندیکاتورهای مورد نیاز استراتژی)
# ------------------------------------------------------------
#
import pandas as pd
import numpy as np
from typing import List, Dict, Any

# --- پارامترهای ثابت اندیکاتور (توافق نهایی) ---
RSI_PERIOD = 14
ATR_PERIOD = 14
BB_PERIOD = 20
BB_STD_DEV = 2
EMA_FAST_PERIOD = 8
EMA_SLOW_PERIOD = 21

def calculate_all_indicators(candles_list: List[list]) -> Dict[str, Any]:
    """
    محاسبه تمام اندیکاتورهای مورد نیاز ربات بر اساس لیست کندل ها.
    ورودی: لیست خام کندل ها [[ts, o, h, l, c, v], ...]
    """
    if not candles_list or len(candles_list) < max(BB_PERIOD, EMA_SLOW_PERIOD):
        return {} # داده کافی برای محاسبه وجود ندارد

    # تبدیل به DataFrame برای محاسبات سریع
    try:
        df = pd.DataFrame(candles_list, columns=['timestamp', 'open', 'high', 'low', 'close', 'volume'])
        df['close'] = df['close'].astype(float)
        df['high'] = df['high'].astype(float)
        df['low'] = df['low'].astype(float)
    except Exception as e:
        print(f"خطای ساخت DataFrame در indicators: {e}")
        return {}

    indicators = {}

    # 1. محاسبه EMA (میانگین متحرک نمایی)
    indicators['EMA8'] = df['close'].ewm(span=EMA_FAST_PERIOD, adjust=False).mean().iloc[-1]
    indicators['EMA21'] = df['close'].ewm(span=EMA_SLOW_PERIOD, adjust=False).mean().iloc[-1]

    # 2. محاسبه ATR (میانگین محدوده واقعی)
    high_low = df['high'] - df['low']
    high_close = np.abs(df['high'] - df['close'].shift())
    low_close = np.abs(df['low'] - df['close'].shift())
    tr = pd.concat([high_low, high_close, low_close], axis=1).max(axis=1)
    indicators['ATR14'] = tr.ewm(span=ATR_PERIOD, adjust=False).mean().iloc[-1]

    # 3. محاسبه RSI (شاخص قدرت نسبی)
    delta = df['close'].diff()
    gain = (delta.where(delta > 0, 0)).ewm(span=RSI_PERIOD, adjust=False).mean()
    loss = (-delta.where(delta < 0, 0)).ewm(span=RSI_PERIOD, adjust=False).mean()
    rs = gain / loss
    indicators['RSI14'] = 100 - (100 / (1 + rs)).iloc[-1]

    # 4. محاسبه Bollinger Bands (BB)
    rolling_mean = df['close'].rolling(BB_PERIOD).mean()
    rolling_std = df['close'].rolling(BB_PERIOD).std()
    indicators['BB_UPPER'] = (rolling_mean + (rolling_std * BB_STD_DEV)).iloc[-1]
    indicators['BB_LOWER'] = (rolling_mean - (rolling_std * BB_STD_DEV)).iloc[-1]

    # 5. محاسبه ATR% (حیاتی برای منطق ریسک)
    last_close = df['close'].iloc[-1]
    if last_close > 0:
        indicators['ATR_PCT'] = (indicators['ATR14'] / last_close) * 100
    else:
        indicators['ATR_PCT'] = 0.0

    return indicators
