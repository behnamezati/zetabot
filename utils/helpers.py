#
# ------------------------------------------------------------
# فایل: utils/helpers.py
# توابع کمکی عمومی (مثل فرمت دهی زمان و PnL)
# ------------------------------------------------------------
#

import time
from datetime import timedelta
from typing import Tuple

def format_duration(start_time: int, end_time: int) -> str:
    """ تبدیل ثانیه ها به فرمت خوانا (مثلا 1h 25m 30s) """
    
    if not start_time or not end_time or end_time < start_time:
        return "N/A"
        
    duration_seconds = end_time - start_time
    
    td = timedelta(seconds=duration_seconds)
    
    parts = []
    
    days = td.days
    if days > 0:
        parts.append(f"{days}d")
        
    hours = td.seconds // 3600
    if hours > 0:
        parts.append(f"{hours}h")
        
    minutes = (td.seconds % 3600) // 60
    if minutes > 0:
        parts.append(f"{minutes}m")
        
    seconds = td.seconds % 60
    if not parts or seconds > 0:
        parts.append(f"{seconds}s")
        
    return " ".join(parts)


def calculate_pnl(entry_price: float, exit_price: float, size_usdt: float) -> Tuple[float, float]:
    """
    محاسبه سود/زیان (PnL) بر حسب درصد و دلار.
    
    Returns:
        (PnL_Percent, PnL_USDT)
    """
    
    if entry_price == 0:
        return 0.0, 0.0

    # ۱. محاسبه PnL بر حسب درصد
    pnl_pct = ((exit_price - entry_price) / entry_price) * 100.0
    
    # ۲. محاسبه PnL بر حسب دلار
    pnl_usdt = (pnl_pct / 100.0) * size_usdt
    
    return pnl_pct, pnl_usdt
