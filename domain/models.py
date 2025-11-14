#
# ------------------------------------------------------------
# فایل: domain/models.py
# تعریف ساختارهای داده‌ای (فرم‌های اطلاعاتی) برای ZetaBot V1.0
# ------------------------------------------------------------
#

from dataclasses import dataclass, field
from enum import Enum, auto
from typing import List

# --- ۱. برچسب‌های وضعیت ---

class MarketSafetyMode(Enum):
    """ وضعیت ایمنی هر نماد در ربات """
    ACTIVE = auto()         # در حال معامله
    SAFE_MODE = auto()      # متوقف شده (مثلاً ۳ ضرر متوالی)
    COOLDOWN = auto()       # استراحت کوتاه (مثلاً ۱۵ ثانیه ضد اسپم)

# --- ۲. دفتر حساب مجازی ---

@dataclass
class VirtualBalance:
    """ مدیریت بالانس ۲۰۰ دلاری مجازی برای Paper Trading """
    total_balance: float      # موجودی کل (با احتساب سود/ضرر)
    available_balance: float  # موجودی در دسترس برای معاملات جدید
    in_use_balance: float     # مجموع پول درگیر در معاملات باز

# --- ۳. فرم معامله باز ---

@dataclass
class Position:
    """ نگهدارنده وضعیت کامل یک پوزیشن باز و فعال """
    symbol: str
    entry_timestamp: int
    entry_price_actual: float   # قیمت واقعی پر شده
    initial_size_usdt: float    # حجم دلاری واقعی پوزیشن
    
    # بخش حیاتی مدیریت خروج (قفل سود پله‌ای)
    current_sl_price: float     # قیمت SL فعلی (که متحرک است)
    final_tp_price: float       # قیمت حد سود نهایی (مثلاً +۱.۵٪)
    
    # متادیتای مدیریت (برای جلوگیری از تکرار اقدامات)
    last_milestone_index: int = -1 # آخرین پله‌ای که SL به آنجا جابجا شده است

# --- ۴. وضعیت مارکت ---

@dataclass
class MarketState:
    """
    نگهدارنده وضعیت کلی هر نماد در ربات
    """
    symbol: str
    safety_mode: MarketSafetyMode = MarketSafetyMode.ACTIVE
    consecutive_losses: int = 0         # برای محاسبه ۳ ضرر متوالی
    
    # لیست زمان ورودها (برای قانون ضد اسپم ۸ ترید در دقیقه)
    entry_timestamps: List[int] = field(default_factory=list)
