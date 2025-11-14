#
# ------------------------------------------------------------
# فایل: app/bot_loop.py
# (V2.1 - نهایی. ارتقا به 25 مارکت همزمان)
# ------------------------------------------------------------
#

import time
import threading
import websocket 
import json
from datetime import datetime
from typing import Dict, Any, List, Optional 

# --- وارد کردن ماژول‌ها ---
from config.settings import (
    PAPER_MODE, TIME_FRAME, CANDLE_BUFFER_SIZE, MAX_ENTRIES_PER_MINUTE
)
from infra.exchange_client import exchange_client
from infra.telegram_bot import telegram_reporter
from infra.persistence_service import persistence_service
from app.state_manager import state_manager
from app.trading_service import trading_service
from domain.entry_policy import get_final_signal 
from domain.models import MarketSafetyMode
from utils.indicators import calculate_all_indicators 
# --- (جدید V2.1) ---
from utils.market_selector import pick_top_pairs 

# --- متغیرهای سراسری ---
LBANK_WS_URL = "wss://www.lbkex.net/ws/V2/"
ACTIVE_SYMBOLS: List[str] = [] # (V2.1 - این لیست اکنون پویا است)
GLOBAL_STOP_FLAG = threading.Event() 

class BotLoop:

    def __init__(self):
        self.running = True 
        self.tick_lock = threading.Lock() 
        self.websocket_thread: Optional[threading.Thread] = None
        self.ws_app: Optional[websocket.WebSocketApp] = None 
        self.is_first_run = True 
        # (V2.1) - ضد اسپم (قانون ۸ ترید در دقیقه)
        self.entry_timestamps: Dict[str, List[int]] = {} 

    def _initialize_services(self):
        """ (V2.1) - راه‌اندازی سرویس‌ها و انتخاب ۲۵ مارکت. """
        
        global ACTIVE_SYMBOLS
        
        persistence_service.start()
        
        # --- (جدید V2.1) انتخاب ۲۵ مارکت برتر ---
        if not exchange_client or not exchange_client.is_connected:
             print("🚫 خطای بحرانی: exchange_client در زمان Warm-up متصل نیست.")
             self.stop_bot()
             return
             
        ACTIVE_SYMBOLS = pick_top_pairs(exchange_client.exchange, n=25)
        if not ACTIVE_SYMBOLS:
            print("🚫 هیچ مارکتی انتخاب نشد. ربات متوقف می‌شود.")
            self.stop_bot()
            return
            
        print(f"--- 🚀 ربات V2.1 روی {len(ACTIVE_SYMBOLS)} مارکت فعال شد ---")
        
        persistence_service.load_state_on_startup(ACTIVE_SYMBOLS)
        
        for symbol in ACTIVE_SYMBOLS:
            state_manager.add_symbol_to_manager(symbol)
            self.entry_timestamps[symbol] = [] # (V2.1) - راه‌اندازی ضد اسپم
        
        # --- Warm-up: بارگیری داده‌های تاریخی (فقط برای ۵ مارکت اول) ---
        print(f"⏳ در حال بارگیری {CANDLE_BUFFER_SIZE} کندل تاریخی برای مارکت‌های اولیه...")
        try:
            for i, symbol in enumerate(ACTIVE_SYMBOLS[:5]): # (فقط ۵ تای اول برای سرعت)
                print(f"   ... در حال بارگیری {symbol} ({i+1}/5)")
                
                # (تبدیل btc_usdt به BTC/USDT برای API)
                symbol_api = symbol.replace('_', '/').upper() 
                
                initial_candles = exchange_client.fetch_candles(symbol_api, TIME_FRAME, CANDLE_BUFFER_SIZE)
                if len(initial_candles) < 50: 
                     print(f"   ... ⚠️ هشدار: داده کافی برای {symbol} دریافت نشد.")
                     continue
                 
                for candle_data in initial_candles:
                     kbar_dict = {
                         't': candle_data[0], 'o': candle_data[1], 'h': candle_data[2],
                         'l': candle_data[3], 'c': candle_data[4], 'v': candle_data[5]
                     }
                     state_manager.add_candle_to_buffer(symbol_api, kbar_dict)
            
            print(f"✅ Warm-up کامل شد.")
                 
        except Exception as e:
            print(f"🚫 خطای بحرانی در زمان Warm-up: {e}")
            self.stop_bot()
            return

    # (V2.1) - بررسی قانون ۸ ترید در دقیقه
    def _check_antispam_cooldown(self, symbol: str) -> bool:
        """
        قانون ضد اسپم: چک می کند که آیا تعداد ورودها در 60 ثانیه اخیر مجاز است یا خیر.
        """
        current_time = int(time.time())
        
        # حذف زمان های قدیمی تر از 60 ثانیه
        valid_times = [t for t in self.entry_timestamps[symbol] if current_time - t < 60]
        self.entry_timestamps[symbol] = valid_times # به روز رسانی لیست

        if len(valid_times) >= MAX_ENTRIES_PER_MINUTE:
            print(f"🚦 محدودیت فرکانس (Anti-Spam) برای {symbol} فعال شد (بیش از {MAX_ENTRIES_PER_MINUTE} ترید در دقیقه).")
            # (فعال کردن Cooldown در state_manager)
            state_manager.activate_cooldown(symbol)
            return False 
        
        return True

    def _process_tick(self, symbol: str, price: float, candles: List[list], indicators: dict):
        """ 
        (V2.1) - منطق اصلی معاملات (اکنون با ضد اسپم).
        """
        if not self.running: return

        # (قفل باید برای هر نماد جداگانه باشد، اما برای سادگی فعلاً سراسری است)
        with self.tick_lock:
            
            is_position_open = symbol in state_manager.open_positions

            # 1. مانیتور کردن پوزیشن‌های باز (چک کردن SL/TP پله‌ای)
            if is_position_open:
                trading_service.monitor_open_positions(symbol, price)
                is_position_open = symbol in state_manager.open_positions

            # 2. بررسی سیگنال‌های استراتژی (Trend/Range)
            signal_action = get_final_signal( price, indicators, candles,)
            if signal_action == "BUY":
                
                # ۳. بررسی ایمنی (Safe Mode / Cooldown)
                if not state_manager.check_entry_allowed(symbol):
                    return # (ورود مجاز نیست)
                    
                # ۴. (جدید V2.1) - بررسی ضد اسپم (قانون ۸ ترید)
                if not self._check_antispam_cooldown(symbol):
                    return # (ورود مجاز نیست)

                # ۵. اجرای ورود
                position = trading_service.process_entry_signal(symbol, price)
                if position:
                    # (ثبت زمان ورود برای قانون ضد اسپم)
                    self.entry_timestamps[symbol].append(int(time.time()))


    # --- مدیریت WebSocket ---

    def _websocket_on_message(self, ws, message):
        """ (V2.1) - مدیریت پیام‌های همزمان ۲۵ مارکت. """
        try:
            data = json.loads(message)
            
            if data.get('action') == 'ping':
                 pong_msg = json.dumps({'action': 'pong', 'pong': data['ping']})
                 ws.send(pong_msg)
                 return # (পিং نیازی به پردازش بیشتر ندارد)

            # (V2.1) - شناسایی مارکت از پیام
            symbol_pair = data.get('pair', '').lower() # 'btc_usdt'
            if not symbol_pair:
                return
                
            symbol_api = symbol_pair.replace('_', '/').upper() # 'BTC/USDT'
            
            # (مطمئن شوید این مارکت جزو ۲۵ مارکت ماست)
            if symbol_pair not in ACTIVE_SYMBOLS:
                return 

            if data.get('type') == 'kbar':
                kbar_data = data.get('kbar', {})
                
                # ۱. افزودن/آپدیت کندل در حافظه
                state_manager.add_candle_to_buffer(symbol_api, kbar_data)
                
                candles_buffer = state_manager.candle_buffers[symbol_api]
                current_price = float(kbar_data.get('c', 0))
                
                if current_price > 0 and len(candles_buffer) >= 50:
                    
                    # ۲. محاسبه اندیکاتورها (EMA, RSI, BB, ATR)
                    all_indicators = calculate_all_indicators(candles_buffer)
                    if not all_indicators:
                        return 
                    
                    # (لاگ‌ها را محدود می‌کنیم تا ترمینال منفجر نشود)
                    if symbol_api == "BTC/USDT":
                         print(f"KBAR (BTC): Price={current_price:.2f}, RSI={all_indicators.get('RSI14', 0):.1f}")

                    # ۳. اجرای منطق معاملات
                    self._process_tick(symbol_api, current_price, candles_buffer, all_indicators)
            
        except Exception as e:
            print(f"خطای پردازش پیام WebSocket: {e}")

    def _websocket_on_error(self, ws, error):
        print(f"خطای WebSocket: {error}")
        telegram_reporter.send_error_report("خطای WebSocket", str(error))

    def _websocket_on_close(self, ws, close_status_code, close_msg):
        print("اتصال WebSocket قطع شد. تلاش برای اتصال مجدد...")
        if not GLOBAL_STOP_FLAG.is_set():
            telegram_reporter.send_error_report("اتصال WebSocket قطع شد", "تلاش برای اتصال مجدد...")
            time.sleep(5) 
            self.start_websocket()

    def _websocket_on_open(self, ws):
        """ (V2.1) - اشتراک در ۲۵ مارکت. """
        print(f"✅ WebSocket اتصال یافت. در حال ارسال پیام اشتراک برای {len(ACTIVE_SYMBOLS)} مارکت...")
        
        for symbol_pair in ACTIVE_SYMBOLS:
            # pair (btc_usdt) قبلاً در فرمت صحیح است
            sub_kbar = {
                "action": "subscribe", "subscribe": "kbar",
                "kbar": TIME_FRAME.replace('m', 'min'), 
                "pair": symbol_pair
            }
            ws.send(json.dumps(sub_kbar))
            
        print("✅ پیام‌های اشتراک ارسال شدند.")
            
    def start_websocket(self):
        if not exchange_client or not exchange_client.is_connected:
            print("🚫 WebSocket شروع نشد: اتصال REST اولیه ناموفق بود.")
            self.running = False
            return
        print(f"⏳ در حال اتصال به WebSocket LBank در {LBANK_WS_URL}...")
        self.ws_app = websocket.WebSocketApp(
            LBANK_WS_URL,
            on_message=self._websocket_on_message,
            on_error=self._websocket_on_error,
            on_close=self._websocket_on_close,
            on_open=self._websocket_on_open 
        )
        self.websocket_thread = threading.Thread(
            target=self.ws_app.run_forever,
            daemon=True 
        )
        self.websocket_thread.start()

    def run_scheduled_tasks(self):
        if self.is_first_run:
            if exchange_client and exchange_client.is_connected:
                telegram_reporter.send_system_report(f"🟢 ربات V2.1 راه‌اندازی شد ({len(ACTIVE_SYMBOLS)} مارکت)", 
                                                    f"حالت اجرا: {'Paper Mode' if PAPER_MODE else 'Live Trade'}")
            self.is_first_run = False
        while not GLOBAL_STOP_FLAG.is_set():
            GLOBAL_STOP_FLAG.wait(60) 

    def start_bot(self):
        self._initialize_services()
        if not self.running: 
            print("🚫 ربات متوقف شد. لطفاً خطاهای Warm-up را بررسی کنید.")
            return
        self.start_websocket() 
        self.run_scheduled_tasks() 
        
    def stop_bot(self):
        GLOBAL_STOP_FLAG.set() 
        if self.ws_app:
            self.ws_app.close() 
        print("👋 ZetaBot: BotLoop متوقف شد.")

# --- ساخت نمونه ---
bot_loop = BotLoop()
