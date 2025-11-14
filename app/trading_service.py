#
# ------------------------------------------------------------
# فایل: app/trading_service.py
# (V2.0 - ارتقا یافته برای استفاده از منطق خروج پله‌ای شما)
# ------------------------------------------------------------
#

import time
from typing import Optional, Dict, Any

from config.settings import (
    INITIAL_POSITION_SIZE_USDT, # <--- (مهم: استفاده از 3$ ثابت)
    INITIAL_SL_PCT, 
    PAPER_MODE
)
from domain.models import Position, VirtualBalance
# --- (جدید V2.0) ---
from domain.exit_policy import (
    check_sl_progression, check_for_exit, get_default_exit_plan
)
# --- (پایان جدید V2.0) ---
from infra.exchange_client import exchange_client
from infra.telegram_bot import telegram_reporter
from infra.persistence_service import persistence_service
from app.state_manager import state_manager
from utils.helpers import calculate_pnl, format_duration


class TradingService:
    
    def __init__(self):
        self.active_sl_orders: Dict[str, str] = {} # {symbol: order_id}
        
    def process_entry_signal(self, symbol: str, entry_price: float) -> Optional[Position]:
        """
        (V2.0) - دریافت سیگنال و اجرای سفارش ورود (با حجم ثابت 3$).
        """
        
        # ۱. (جدید V2.0) - حجم ثابت ۳ دلار
        target_size_usdt = INITIAL_POSITION_SIZE_USDT
        amount_coin = target_size_usdt / entry_price

        # ۲. ارسال سفارش (Limit IOC)
        order_info = exchange_client.place_order(
            symbol=symbol,
            order_type='limit', # (V1.6)
            side='buy',
            amount_usdt=target_size_usdt, # (V1.6)
            price=entry_price
        )
        
        if not order_info or order_info.get('status') != 'closed':
            print(f"هشدار: سفارش ورود {symbol} پر نشد (IOC).")
            return None
        
        filled_size_usdt = order_info.get('filled', 0.0) * entry_price
        if filled_size_usdt < 1.0: # حداقل ۱ دلار
            return None
            
        # ۳. ساخت Position Object (با پلن خروج V2.0)
        initial_sl_price = entry_price * (1.0 - INITIAL_SL_PCT)
        
        position = Position(
            symbol=symbol,
            entry_timestamp=int(time.time()),
            entry_price_actual=entry_price, 
            initial_size_usdt=filled_size_usdt,
            current_sl_price=initial_sl_price,
            initial_sl_price=initial_sl_price,
            exit_plan=get_default_exit_plan(), # <--- (مهم: استفاده از پلن خروج V2.0)
            last_milestone_index=-1 # (مورد نیاز برای پلن V2.0)
        )
        
        # ۴. اجرای ورود در State Manager
        state_manager.execute_entry(position)
        
        # ۵. ثبت SL اولیه در صرافی
        # (در Paper Mode، فقط در حافظه ثبت می‌شود)
        self.active_sl_orders[symbol] = "virtual_sl_order"
        
        # ۶. ارسال گزارش تلگرام
        telegram_reporter.send_entry_report(position)
        
        return position

    def monitor_open_positions(self, symbol: str, current_price: float):
        """
        (V2.0) - چک کردن SL متحرک و خروج نهایی برای پوزیشن باز.
        """
        
        if symbol not in state_manager.open_positions:
            return
            
        position = state_manager.open_positions[symbol]

        # --- ۱. بررسی جابجایی SL (منطق پله‌ای V2.0) ---
        new_sl_price = check_sl_progression(position, current_price)
        
        if new_sl_price:
            # اگر قیمت SL جدید برگشت، آن را به صرافی می فرستیم.
            print(f"SL UPDATE: {symbol} SL به {new_sl_price} منتقل شد.")
            # (منطق exchange_client.update_sl(position, new_sl_price) باید اینجا باشد)
            # (در Paper Mode، قیمت SL در حافظه آپدیت شده است)
            
        # --- ۲. بررسی خروج نهایی (برخورد به SL متحرک یا Final TP) ---
        exit_reason = check_for_exit(position, current_price)
            
        if exit_reason:
            print(f"EXIT SIGNAL: {symbol} به دلیل {exit_reason} بسته می‌شود.")
            self._execute_final_exit(position, current_price, exit_reason)

    def _execute_final_exit(self, position: Position, exit_price: float, reason: str):
        """ (V2.0) - اجرای نهایی Market Sell و آپدیت لاگ ها. """
        
        symbol = position.symbol
        
        # ۱. لغو سفارش SL فعال (اگر در صرافی واقعی بود)
        if symbol in self.active_sl_orders:
            # exchange_client.cancel_order(symbol, self.active_sl_orders[symbol])
            del self.active_sl_orders[symbol]
        
        # ۲. Market Sell (ارسال سفارش خروج)
        exit_order = exchange_client.place_order(
            symbol=symbol,
            order_type='market',
            side='sell',
            amount_usdt=position.initial_size_usdt, # (V1.6)
            price=exit_price # (قیمت برای محاسبه amount_coin لازم است)
        )
        
        if not exit_order:
             print(f"خطای بحرانی: سفارش خروج {symbol} شکست خورد.")
             # (در اینجا ربات باید وارد حالت اضطراری شود)
             return

        # ۳. محاسبه PnL
        pnl_pct, pnl_usdt = calculate_pnl(position.entry_price_actual, exit_price, position.initial_size_usdt)
        fees_usdt = 0 # (در Paper Mode ساده)
        
        # ۴. آپدیت بالانس دمو و وضعیت ایمنی
        state_manager.execute_exit(position, pnl_usdt, fees_usdt)
        
        # ۵. گزارش و ذخیره سازی
        telegram_reporter.send_exit_report(position, exit_price, pnl_usdt, reason)
        
        trade_log_data = {
            'timestamp': int(time.time()), 
            'symbol': symbol, 
            'entry_price': position.entry_price_actual, 
            'exit_price': exit_price,
            'entry_size_usdt': position.initial_size_usdt,
            'pnl_usdt': pnl_usdt,
            'pnl_pct': pnl_pct,
            'fees_usdt': fees_usdt,
            'exit_reason': reason,
            'mode': "Paper",
            'ml_prob': 0.0,
            'is_ml_active': False
        }
        persistence_service.add_trade_to_queue(trade_log_data)
        
# --- نمونه سازی ---
trading_service = TradingService()
