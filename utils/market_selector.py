#
# ------------------------------------------------------------
# فایل: utils/market_selector.py
# (V2.1 - انتخاب 25 مارکت برتر بر اساس حجم و نوسان)
# ------------------------------------------------------------
#
from __future__ import annotations
import time
from typing import List, Tuple, Dict, Any

# توکن های اهرمی یا شورت را حذف می کنیم
BAD_TOKENS = ("UP/", "DOWN/", "BULL/", "BEAR/", "3L/", "3S/")

def _is_good_usdt(symbol: str) -> bool:
    if not symbol.endswith("/USDT"):
        return False
    return not any(bad in symbol for bad in BAD_TOKENS)

def _volatility_from_ticker(t: dict) -> float:
    # تلاش برای گرفتن نوسان نسبی روز
    try:
        h = float(t.get("high") or 0)
        l = float(t.get("low") or 0)
        c = float(t.get("close") or t.get("last") or 0)
        if h > 0 and l > 0 and c > 0:
            return max(0.0, (h - l) / c)
    except Exception:
        pass
    return 0.0

def _volume_from_ticker(t: dict) -> float:
    # اولویت با quoteVolume (حجم دلاری)
    try:
        qv = float(t.get("quoteVolume") or 0)
        if qv > 0:
            return qv
    except Exception:
        pass
    # اگر نبود، (baseVolume * last price)
    try:
        bv = float(t.get("baseVolume") or 0)
        last = float(t.get("last") or t.get("close") or 0)
        return bv * last
    except Exception:
        return 0.0

def pick_top_pairs(exchange, n: int = 25, min_quote_vol: float = 500_000.0) -> List[str]:
    """
    25 مارکت برتر USDT را بر اساس حجم و نوسان انتخاب می کند.
    خروجی: لیستی از pair ها به فرمت LBank (مثلاً 'btc_usdt').
    """
    print(f"⏳ در حال انتخاب {n} مارکت برتر از LBank...")
    try:
        if not getattr(exchange, "markets", None):
            exchange.load_markets()
    except Exception as e:
        print(f"خطای load_markets در market_selector: {e}")
        return ["btc_usdt"] # بازگشت به حالت امن

    pairs: List[Tuple[str, float]] = []
    
    try:
        tickers = exchange.fetch_tickers()
    except Exception as e:
        print(f"خطای fetch_tickers در market_selector: {e}")
        return ["btc_usdt"]

    for symbol, t in tickers.items():
        if not _is_good_usdt(symbol):
            continue
            
        vol_q = _volume_from_ticker(t)
        if vol_q < min_quote_vol: # حذف مارکت های با حجم کم
            continue
            
        volat = _volatility_from_ticker(t)
        
        # امتیازدهی: (حجم * نوسان)
        score = vol_q * max(0.0001, volat) 
        pairs.append((symbol, score))

    # مرتب سازی بر اساس بیشترین امتیاز
    pairs.sort(key=lambda x: x[1], reverse=True)
    
    # تبدیل فرمت 'BTC/USDT' به 'btc_usdt'
    top = [sym.replace("/", "_").lower() for sym, _ in pairs[:n]]
    
    if not top:
        print("🚫 هیچ مارکتی با حداقل حجم یافت نشد. فقط از btc_usdt استفاده می شود.")
        return ["btc_usdt"]
        
    print(f"✅ {len(top)} مارکت برتر انتخاب شدند (مانند: {top[0]}, {top[1]}, ...)")
    return top
