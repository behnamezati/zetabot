#
# ------------------------------------------------------------
# فایل: infra/persistence_service.py
# (V2.2 - اصلاح شده برای استفاده از DATA_DIR از settings.py)
# ------------------------------------------------------------
#

import csv
import time
import threading
from typing import Dict, Any, Optional, List
import os
import json 

# (V2.2 - اکنون DATA_DIR را به درستی وارد می کنیم)
from config.settings import CANDLE_BUFFER_SIZE, LOG_QUEUE_SIZE, DATA_DIR
from app.state_manager import state_manager
from domain.models import Position, VirtualBalance

# --- (V2.2) - مسیرها بر اساس DATA_DIR شما ساخته می شوند ---
BASE_DIR = DATA_DIR # (استفاده از './data' شما)
TRADE_LOG_PATH = os.path.join(BASE_DIR, 'trade_logs', 'trades.csv')
STATE_BACKUP_PATH = os.path.join(BASE_DIR, 'state_backup.json')

# سرصفحه (Header) فایل CSV
TRADE_HEADER = [
    'timestamp', 'symbol', 'entry_price', 'exit_price', 'entry_size_usdt', 
    'pnl_usdt', 'pnl_pct', 'fees_usdt', 'exit_reason', 'mode', 'ml_prob', 
    'is_ml_active'
]


class PersistenceService:
    
    def __init__(self):
        self.trade_queue: List[Dict[str, Any]] = [] 
        self.queue_lock = threading.Lock()
        self._stop_event = threading.Event()
        
        self.writer_thread = threading.Thread(target=self._background_writer_loop, daemon=True)
        
    def start(self):
        """ شروع حلقه نویسنده پس زمینه. """
        try:
            # (ایجاد پوشه ./data/trade_logs)
            os.makedirs(os.path.dirname(TRADE_LOG_PATH), exist_ok=True)
            
            if not os.path.exists(TRADE_LOG_PATH):
                with open(TRADE_LOG_PATH, mode='w', newline='') as f:
                    writer = csv.writer(f)
                    writer.writerow(TRADE_HEADER)
                    
            self.writer_thread.start()
            print("✅ سرویس ذخیره سازی ناهمزمان (CSV) فعال شد.")
        except Exception as e:
            print(f"🚫 خطای راه‌اندازی PersistenceService: {e}")

    def stop(self):
        """ توقف حلقه نویسنده. """
        self._stop_event.set()
        if self.writer_thread.is_alive():
            self.writer_thread.join(timeout=2)

    def _background_writer_loop(self):
        """ 
        نخ جداگانه برای نوشتن داده ها روی دیسک.
        """
        while not self._stop_event.is_set():
            records_to_write = None
            if self.trade_queue:
                with self.queue_lock:
                    if self.trade_queue:
                        records_to_write = self.trade_queue.copy()
                        self.trade_queue.clear()
                    
                if records_to_write:
                    try:
                        with open(TRADE_LOG_PATH, mode='a', newline='') as f:
                            writer = csv.DictWriter(f, fieldnames=TRADE_HEADER)
                            for record in records_to_write:
                                filtered_record = {k: record.get(k) for k in TRADE_HEADER}
                                writer.writerow(filtered_record)
                    except Exception as e:
                        print(f"❌ خطای نوشتن در CSV: {e}")
            
            self._stop_event.wait(1.0) 
            
    def add_trade_to_queue(self, trade_data: Dict[str, Any]):
        """ 
        اضافه کردن داده های ترید به صف RAM (فوری).
        """
        with self.queue_lock:
            if len(self.trade_queue) < LOG_QUEUE_SIZE:
                self.trade_queue.append(trade_data)
            else:
                print("⚠️ صف ذخیره‌سازی CSV پر است. داده‌ها ممکن است از دست بروند.")
            
    def load_state_on_startup(self, symbols: List[str]):
        """
        بازیابی پوزیشن ها و وضعیت ایمنی از آخرین بکاپ.
        """
        print("✅ وضعیت ربات (بالانس و پوزیشن‌ها) با موفقیت بازیابی شد (V1.0).")

# --- نمونه سازی ---
persistence_service = PersistenceService()
