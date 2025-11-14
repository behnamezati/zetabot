#
# ------------------------------------------------------------
# فایل: infra/exchange_client.py
# (FIX V1.6 - اصلاح تابع place_order برای پذیرش 'order_type')
# ------------------------------------------------------------
#

import ccxt
import time
from typing import Dict, Any, Optional, List

# وارد کردن تنظیمات
from config.settings import (
    EXCHANGE_ID, API_KEY, API_SECRET, API_PASSWORD, PAPER_MODE
)

class ExchangeClient:
    """
    مسئول ارتباط با LBank (ارسال سفارش، دریافت وضعیت).
    """

    def __init__(self):
        self.exchange: Optional[ccxt.Exchange] = None
        self.is_connected: bool = False
        try:
            self._connect_rest()
        except Exception as e:
            print(f"🚫 خطای کشنده در زمان اتصال REST: {e}")
            self.is_connected = False # اطمینان از False بودن در صورت خطا

    def _connect_rest(self):
        """ اتصال و احراز هویت به REST API صرافی LBank. """
        
        if not API_KEY or not API_SECRET:
            print("🚫 API Key یا Secret Key در فایل .env یافت نشد.")
            self.is_connected = False
            raise ValueError("API Key/Secret در .env تنظیم نشده است.")

        config = {
            'apiKey': API_KEY,
            'secret': API_SECRET,
            'password': API_PASSWORD,
            'enableRateLimit': True, 
            'options': {'defaultType': 'spot'}
        }
        
        try:
            exchange_class = getattr(ccxt, EXCHANGE_ID)
            self.exchange = exchange_class(config)
            
            print("⏳ در حال تست احراز هویت با fetch_balance()...")
            self.exchange.fetch_balance() 
            
            print(f"✅ اتصال REST و احراز هویت به {EXCHANGE_ID} برقرار شد.")
            self.is_connected = True
            
        except ccxt.AuthenticationError as e:
            print(f"🚫 خطای احراز هویت: API Key/Secret اشتباه است یا مجوز Trade/Read فعال نیست.")
            self.is_connected = False
            raise e 
            
        except Exception as e:
            print(f"🚫 خطای عمومی اتصال REST: {e}")
            self.is_connected = False
            raise e 

            
    # --- توابع دریافت داده ---

    def fetch_price(self, symbol: str) -> Optional[float]:
        if not self.is_connected: return None
        try:
            ticker = self.exchange.fetch_ticker(symbol)
            price = ticker.get("last") or ticker.get("close")
            return float(price) if price is not None else None
        except Exception as e:
            print(f"خطای fetch_price برای {symbol}: {e}")
            return None

    def fetch_candles(self, symbol: str, timeframe: str, limit: int = 100) -> List[list]:
        if not self.is_connected: return []
        try:
            data = self.exchange.fetch_ohlcv(symbol, timeframe=timeframe, limit=limit)
            return data or []
        except Exception:
            return []

    # --- (اصلاحیه نهایی V1.6) ---
    def place_order(self, symbol: str, side: str, order_type: str, amount_usdt: float, price: float) -> Optional[Dict[str, Any]]:
        """ 
        ارسال سفارش (اکنون order_type را به عنوان آرگومان می‌پذیرد).
        """
        if not self.is_connected: return None
        
        if price is None or price == 0:
            print(f"ERROR: قیمت نامعتبر {price} برای {symbol}")
            return None
        amount_coin = amount_usdt / price
        
        if PAPER_MODE:
            print(f"PAPER_MODE: ارسال سفارش {side} {amount_coin:.6f} {symbol} در قیمت {price} (Type: {order_type})")
            return {'id': f'virtual_{symbol}_{int(time.time())}', 'status': 'closed', 'filled': amount_coin, 'price': price}
            
        try:
            # (اصلاحیه: 'type' هاردکد شده با 'order_type' داینامیک جایگزین شد)
            order = self.exchange.create_order(
                symbol=symbol,
                type=order_type, # <--- اینجا اصلاح شد
                side=side, 
                amount=amount_coin,
                price=price,
                params={'timeInForce': 'IOC'} # (سفارش سریع IOC)
            )
            return order
        except Exception as e:
            print(f"ERROR: خطای place_order برای {symbol}: {e}")
            raise e 

    def cancel_order(self, symbol: str, order_id: str):
        """ لغو یک سفارش فعال (برای جابجایی SL). """
        if not self.is_connected: return None
        if PAPER_MODE:
            return {'status': 'canceled'}
        
        try:
            return self.exchange.cancel_order(order_id, symbol)
        except Exception as e:
            print(f"ERROR: خطای cancel_order برای {order_id}: {e}")
            raise e

# --- نمونه سازی ---
# (این بخش باید در try/except باشد تا ربات در صورت خطای اتصال متوقف شود)
try:
    exchange_client = ExchangeClient()
except Exception:
    exchange_client = None 
    print("🚫 نمونه exchange_client ساخته نشد. ربات متوقف خواهد شد.")
