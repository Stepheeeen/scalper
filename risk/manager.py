import math
from utils.logger import logger

class RiskManager:
    def __init__(self, config):
        self.config = config
        self.daily_trades = 0
        self.daily_loss_percent = 0.0
        self.consecutive_losses = 0
        self.initial_daily_balance = 0.0

    def calculate_position_size(self, balance: float, entry_price: float, stop_loss: float) -> float:
        """
        Calculates lot size based on User Defined dynamic risk %.
        Gold Formula: Lot Size = (Balance * Risk%) / (StopLoss Distance * 100)
        """
        if balance <= 0 or entry_price == stop_loss:
            return 0.01

        risk_amount = balance * (self.config.risk.risk_per_trade_percent / 100)
        sl_dist_price = abs(entry_price - stop_loss)
        
        if sl_dist_price == 0: return 0.01
        
        # Standard XAUUSD Calculation: $1 price move = $100 P/L for 1.00 Lot.
        lot_size = risk_amount / (sl_dist_price * 100)
        
        # Round to 2 decimal places and enforce min (0.01) and safe max (5.00)
        lot_size = round(max(0.01, min(lot_size, 5.0)), 2)
        
        logger.info(f"Risk: ${risk_amount:.2f} | SL Dist: {sl_dist_price:.2f} | Lots: {lot_size}")
        return lot_size

    def should_move_to_be(self, entry_price: float, current_price: float, side: str) -> bool:
        be_trigger = self.config.risk.be_profit_pips / 100
        if side == "BUY":
            return (current_price - entry_price) >= be_trigger
        else:
            return (entry_price - current_price) >= be_trigger

    def enforce_daily_limits(self, balance: float, equity: float) -> bool:
        """Enforces max trades, drawdown, and consecutive loss limits."""
        if self.initial_daily_balance == 0:
            self.initial_daily_balance = balance

        # 1. Max Trades Check
        if self.daily_trades >= self.config.risk.max_trades_per_day:
            logger.warning(f"Daily trade limit ({self.config.risk.max_trades_per_day}) reached.")
            return False
            
        # 2. Max Drawdown Check
        current_loss_percent = ((self.initial_daily_balance - equity) / self.initial_daily_balance) * 100
        if current_loss_percent >= self.config.risk.max_daily_drawdown_percent:
            logger.error(f"Daily drawdown limit ({self.config.risk.max_daily_drawdown_percent}%) reached. Trading Halted.")
            return False
            
        # 3. Max Consecutive Losses Check
        if self.consecutive_losses >= self.config.risk.max_consecutive_losses:
            logger.warning(f"Max consecutive losses ({self.config.risk.max_consecutive_losses}) reached. Stop for the day.")
            return False
            
        return True

    def register_trade_result(self, profit_dollars: float):
        """Updates daily statistics after a trade closes."""
        self.daily_trades += 1
        if profit_dollars <= 0:
            self.consecutive_losses += 1
        else:
            self.consecutive_losses = 0

    def reset_daily_stats(self, current_balance: float):
        self.daily_trades = 0
        self.consecutive_losses = 0
        self.initial_daily_balance = current_balance
