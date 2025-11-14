#
# ------------------------------------------------------------
# فایل: app/state_manager.py
# (V2.2.5 - اصلاح نهایی: مدیریت هیبرید int/str برای زمان)
# ------------------------------------------------------------
#

from typing import Dict, Optional, List, Any
import time
from datetime import datetime 

from config.settings import (
    VIRTUAL_BALANCE_START,
    FAST_COOLDOWN_SECONDS,    
    MAX_CONSECUTIVE_LOSSES,
    INITIAL_POSITION_SIZE_USDT, 
    CANDLE_BUFFER_SIZE
)
from domain.models import (
    Position, MarketState, VirtualBalance, MarketSafetyMode
)
from infra.telegram_bot import telegram_reporter 

class StateManager:
    
    def __init__(self):
        self.open_positions: Dict[str, Position] = {}     
        self.market_states: Dict[str, MarketState] = {}   
        self.candle_buffers: Dict[str, List[list]] = {} 

        self.virtual_balance = VirtualBalance(
            total_balance=VIRTUAL_BALANCE_START,
            available_balance=VIRTUAL_BALANCE_START,
            in_use_balance=0.0 
        )

    def add_symbol_to_manager(self, symbol: str):
        if symbol not in self.market_states:
            self.market_states[symbol] = MarketState(symbol=symbol)
            self.candle_buffers[symbol] = []

    def add_candle_to_buffer(self, symbol: str, kbar_data: dict):
        """ (V2.2.5) - اصلاح نهایی: مدیریت هیبرید int/str برای زمان """
        try:
            # --- (اصلاحیه V2.2.5) ---
            t_val = kbar_data.get('t')
            timestamp_ms = 0

            if isinstance(t_val, int):
                # 1. داده تاریخی (Warm-up) - از ccxt می آید (int)
                timestamp_ms = t_val
            elif isinstance(t_val, str):
                # 2. داده زنده (WebSocket) - از LBank می آید (str)
                try:
                    # (فرمت: YYYY-MM-DDTHH:MM:SS.sss)
                    dt = datetime.strptime(t_val, '%Y-%m-%dT%H:%M:%S.%f')
                    timestamp_ms = int(dt.timestamp() * 1000)
                except ValueError:
                    # (Fallback برای فرمت بدون میلی ثانیه)
                    dt = datetime.strptime(t_val, '%Y-%m-%dT%H:%M:%S')
                    timestamp_ms = int(dt.timestamp() * 1000)
            elif isinstance(t_val, float):
                # 3. حالت Fallback (اگر float بود)
                timestamp_ms = int(t_val)
            else:
                raise TypeError(f"فرمت زمان ناشناخته: {t_val}")

            candle_list = [
                timestamp_ms, # <--- (اکنون همیشه int است)
                float(kbar_data.get('o')),
                float(kbar_data.get('h')),
                float(kbar_data.get('l')),
                float(kbar_data.get('c')),
                float(kbar_data.get('v'))
            ]
            # --- (پایان اصلاحیه) ---
            
            buffer = self.candle_buffers.get(symbol)
            if buffer is None:
                buffer = []
                self.candle_buffers[symbol] = buffer
                
            # اکنون مقایسه (int < int) به درستی کار خواهد کرد
            if not buffer or buffer[-1][0] < candle_list[0]:
                buffer.append(candle_list)
            elif buffer and buffer[-1][0] == candle_list[0]:
                buffer[-1] = candle_list
            
            if len(buffer) > CANDLE_BUFFER_SIZE + 20: 
                self.candle_buffers[symbol] = buffer[-(CANDLE_BUFFER_SIZE + 10):]
        
        except Exception as e:
            print(f"خطای add_candle_to_buffer برای {symbol}: {e}")

    # --- منطق Paper Balance (بدون تغییر) ---
    def check_funding(self, size_usdt: float) -> bool:
        return size_usdt <= self.virtual_balance.available_balance

    def execute_entry(self, position: Position):
        size = position.initial_size_usdt
        if size > self.virtual_balance.available_balance:
            print(f"خطای بالانس: {size} مورد نیاز، {self.virtual_balance.available_balance} موجود")
            return 
            
        self.virtual_balance.available_balance -= size
        self.virtual_balance.in_use_balance += size 
        self.open_positions[position.symbol] = position

    def execute_exit(self, position: Position, pnl_usdt: float, fees_usdt: float):
        entry_size = position.initial_size_usdt
        net_return = entry_size + pnl_usdt - fees_usdt
        
        self.virtual_balance.in_use_balance -= entry_size 
        self.virtual_balance.total_balance += (pnl_usdt - fees_usdt)
        self.virtual_balance.available_balance += net_return

        if position.symbol in self.open_positions:
            del self.open_positions[position.symbol]

        if position.symbol in self.market_states:
            st = self.market_states[position.symbol]
            
            if pnl_usdt < 0:
                st.consecutive_losses += 1
            else:
                st.consecutive_losses = 0 
            
            if st.consecutive_losses >= MAX_CONSECUTIVE_LOSSES:
                st.safety_mode = MarketSafetyMode.SAFE_MODE
                st.last_safety_event_time = int(time.time())
                print(f"🔒 حالت ایمنی (Safe Mode) برای {position.symbol} به دلیل {MAX_CONSECUTIVE_LOSSES} ضرر متوالی فعال شد.")
                telegram_reporter.send_safety_report(position.symbol, 'SAFE_MODE')
            else:
                self.activate_cooldown(position.symbol)

    def activate_cooldown(self, symbol: str):
        if symbol not in self.market_states: return
        state = self.market_states[symbol]
        
        if state.safety_mode == MarketSafetyMode.SAFE_MODE:
            return
            
        state.safety_mode = MarketSafetyMode.COOLDOWN
        state.last_safety_event_time = int(time.time())

    def check_entry_allowed(self, symbol: str) -> bool:
        if symbol not in self.market_states:
            return False 
            
        state = self.market_states[symbol]
        now = int(time.time())

        if state.safety_mode == MarketSafetyMode.SAFE_MODE:
            return False

        if state.safety_mode == MarketSafetyMode.COOLDOWN:
            if now - state.last_safety_event_time < FAST_COOLDOWN_SECONDS:
                return False 
            
            state.safety_mode = MarketSafetyMode.ACTIVE
            if state.consecutive_losses > 0: 
                state.consecutive_losses = 0 

        if not self.check_funding(INITIAL_POSITION_SIZE_USDT):
            print(f"🚫 بودجه کافی برای ورود {symbol} وجود ندارد (نیاز: {INITIAL_POSITION_SIZE_USDT}).")
            return False

        return True 

# --- نمونه سازی ---
state_manager = StateManager()
