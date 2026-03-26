import math
from typing import Dict, Optional

class RiskManager:
    """
    Handles position sizing and global risk controls.
    Ensures the 'preserve capital' philosophy is enforced.
    """
    def __init__(self, config):
        self.config = config
        self.daily_pnl = 0.0
        self.trades_today = 0
        self.start_balance = 0.0

    def calculate_position_size(self, balance: float, stop_loss_pips: float, symbol: str = "XAUUSD") -> float:
        """
        Calculates lot size based on % risk.
        lot_size = (balance * risk%) / (sl_pips * pip_value)
        """
        if stop_loss_pips <= 0:
            return 0.0
            
        risk_amount = balance * (self.config.risk.risk_per_trade_percent / 100)
        
        # XAUUSD lot size calculation (Standard: 1 lot = 100oz)
        # 1 pip in XAUUSD (0.10) for 1 lot = $10
        # If sl_pips is the price difference (e.g., 2.50 points = 25 pips)
        # lot_size = risk_amount / (stop_loss_points * 100)
        
        lot_size = risk_amount / (stop_loss_pips * 100)
        return round(lot_size, 2)

    def check_global_limits(self, current_balance: float) -> bool:
        """
        Enforces daily drawdown and max trades.
        """
        if self.trades_today >= self.config.risk.max_trades_per_day:
            return False
            
        if self.start_balance > 0:
            drawdown = (self.start_balance - current_balance) / self.start_balance * 100
            if drawdown >= self.config.risk.max_daily_drawdown_percent:
                return False
                
        return True

    def update_daily_stats(self, pnl: float):
        self.daily_pnl += pnl
        self.trades_today += 1

    def calculate_trailing_stop(self, current_price: float, side: str, atr_value: float) -> float:
        """
        Calculates a new stop loss based on ATR trailing.
        """
        multiplier = self.config.risk.move_to_breakeven_atr_multiple
        if side.upper() == "BUY":
            return current_price - (atr_value * multiplier)
        else:
            return current_price + (atr_value * multiplier)

    def calculate_partial_tp(self, entry_price: float, stop_loss: float, rr: float = 1.0) -> float:
        """
        Calculates the price for a partial take profit.
        Default is 1:1 risk-reward.
        """
        risk = abs(entry_price - stop_loss)
        if entry_price > stop_loss: # BUY
            return entry_price + (risk * rr)
        else: # SELL
            return entry_price - (risk * rr)
