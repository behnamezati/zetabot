#
# ------------------------------------------------------------
# فایل: domain/exit_policy.py
# (V2.0.1 - اصلاح خطای تایپی NameError 'ProgresssiveSLStep')
# ------------------------------------------------------------
#
from typing import Tuple, Optional, List
from config.settings import (
    INITIAL_SL_PCT, # 1.0%
    RISK_FREE_TRIGGER_PCT, # 0.45%
    TP_STEP_1_TRIGGER_PCT, # 0.90%
    TP_STEP_1_SL_LOCK_PCT, # 0.45%
    FINAL_TP_PCT, # 1.5%
    FRICTION_COST_PCT # هزینه کارمزد برای Breakeven
)
from domain.models import Position

# --- (این کلاس‌ها برای تعریف پلن خروج مورد نیاز است) ---
class ProgressiveSLStep:
    """ تعریف یک مرحله در پلن «قفل سود پله‌ای» """
    def __init__(self, trigger_at_pct: float, move_sl_to_pct: float, is_breakeven: bool = False):
        self.trigger_at_pct = trigger_at_pct
        self.move_sl_to_pct = move_sl_to_pct
        self.is_breakeven = is_breakeven

class ExitPlan:
    """ پلن کامل خروج """
    # --- (اصلاحیه V2.0.1) ---
    # خطای تایپی در 'ProgresssiveSLStep' اصلاح شد
    def __init__(self, final_tp_pct: float, progressive_sl_plan: List[ProgressiveSLStep]):
        self.final_tp_pct = final_tp_pct
        self.progressive_sl_plan = progressive_sl_plan
    # --- (پایان اصلاحیه) ---

# --- (تابع ساخت پلن خروج پیش‌فرض شما) ---
def get_default_exit_plan() -> ExitPlan:
    """
    ایجاد پلن خروج ثابت (1:1.5) شما.
    """
    
    # Trigger 1: ریسک-فری (ماشه در 0.45%)
    risk_free_step = ProgressiveSLStep(
        trigger_at_pct=RISK_FREE_TRIGGER_PCT, # 0.45%
        move_sl_to_pct=0.0, 
        is_breakeven=True # SL به نقطه ورود + هزینه ها (Breakeven) می رود
    )
    
    # Trigger 2: قفل سود (ماشه در 0.90%)
    milestone_1_lock = ProgressiveSLStep(
        trigger_at_pct=TP_STEP_1_TRIGGER_PCT, # 0.90%
        move_sl_to_pct=TP_STEP_1_SL_LOCK_PCT, # SL به 0.45% منتقل می شود
        is_breakeven=False
    )
    
    return ExitPlan(
        final_tp_pct=FINAL_TP_PCT, # 1.5%
        progressive_sl_plan=[risk_free_step, milestone_1_lock]
    )

# --- (توابع کمکی محاسبه قیمت) ---

def _calculate_price_from_pct(entry_price: float, target_pct: float) -> float:
    """ قیمت SL یا TP را بر اساس درصد محاسبه می کند. """
    return entry_price * (1.0 + target_pct)

def _get_risk_free_price(entry_price: float) -> float:
    """ قیمت دقیق ریسک-فری (Breakeven + Friction) را محاسبه می کند. """
    return entry_price * (1.0 + FRICTION_COST_PCT)

# --- (منطق اصلی مانیتورینگ خروج) ---

def check_sl_progression(position: Position, current_price: float) -> Optional[float]:
    """
    (V2.0) بررسی می کند که آیا SL نیاز به جابجایی دارد یا خیر.
    اگر نیاز باشد، قیمت جدید SL را برمی‌گرداند.
    """
    plan = position.exit_plan
    
    for index, step in enumerate(plan.progressive_sl_plan):
        
        if index <= position.last_milestone_index:
            continue 
            
        trigger_price = _calculate_price_from_pct(position.entry_price_actual, step.trigger_at_pct)
            
        if current_price >= trigger_price:
            
            if step.is_breakeven:
                new_sl_price = _get_risk_free_price(position.entry_price_actual)
            else:
                new_sl_price = _calculate_price_from_pct(position.entry_price_actual, step.move_sl_to_pct)

            if new_sl_price > position.current_sl_price:
                position.current_sl_price = new_sl_price
                position.last_milestone_index = index
                return new_sl_price 
    
    return None 

def check_for_exit(position: Position, current_price: float) -> Optional[str]:
    """
    (V2.0) بررسی می کند که آیا پوزیشن باید بسته شود (برخورد به SL یا Final TP).
    """
    
    # 1. برخورد به SL متحرک/ثابت
    if current_price <= position.current_sl_price:
        return "SL Hit"

    # 2. برخورد به Final TP
    final_tp_price = _calculate_price_from_pct(position.entry_price_actual, position.exit_plan.final_tp_pct)
    if current_price >= final_tp_price:
        return "TP Hit"
        
    return None
