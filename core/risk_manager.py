import logging

logger = logging.getLogger(__name__)

class RiskManager:
    def __init__(self):
        self.risk_percent = 0.01 # 1% Capital Rule
        self.max_daily_drawdown = 0.03 # 3% Daily Drawdown Auto-Kill
        
        # Gold Contract Specs (Broker dependent, typically 1 lot = 100 oz)
        self.contract_size = 100 
        self.tick_size = 0.01
        self.tick_value = self.contract_size * self.tick_size # Value of 1 tick per standard lot
        
        self.daily_starting_balance = None
        self.is_auto_killed = False

    def set_daily_starting_balance(self, balance: float):
        """Sets the baseline capital for the day to calculate the 3% DD limit."""
        if self.daily_starting_balance is None:
            self.daily_starting_balance = balance

    def check_daily_drawdown(self, current_equity: float) -> bool:
        """
        Track rolling 24-hour balance drawdowns.
        Returns True if system should be auto-killed.
        """
        if self.daily_starting_balance is None:
            return False
            
        drawdown_amount = self.daily_starting_balance - current_equity
        drawdown_percent = drawdown_amount / self.daily_starting_balance
        
        if drawdown_percent >= self.max_daily_drawdown:
            self.is_auto_killed = True
            logger.critical(f"AUTO-KILL ENGAGED: Daily drawdown limit breached ({drawdown_percent*100:.2f}%).")
            return True
            
        return False

    def calculate_lot_size(self, account_balance: float, entry_price: float, sl_price: float) -> tuple[float, float]:
        """
        Dynamic Gold Lot Sizing:
        Lot Size = (Account Balance * 0.01) / (SL_dist * Tick Value / Tick Size)
        Returns (lot_size, adjusted_sl_price) to ensure SL distance floor is respected.
        """
        from config.settings import settings
        risk_amount = account_balance * self.risk_percent
        
        # SL distance in raw price difference
        sl_dist = abs(entry_price - sl_price)
        
        if sl_dist < settings.min_sl_raw:
            logger.warning(f"SL distance ({sl_dist}) < floor ({settings.min_sl_raw}). Adjusting to floor.")
            sl_dist = settings.min_sl_raw
            # Adjust the actual SL price to give the trade room to breathe
            if entry_price > sl_price: # Long position
                sl_price = entry_price - sl_dist
            else: # Short position
                sl_price = entry_price + sl_dist
        
        if sl_dist == 0:
            logger.error("SL distance is zero, cannot calculate lot size.")
            return 0.0, sl_price
            
        # For XAUUSD, points = price difference / tick_size
        points_at_risk = sl_dist / self.tick_size
        
        # Total loss for 1 standard lot = points_at_risk * tick_value
        loss_per_lot = points_at_risk * self.tick_value
        
        # Calculate precise lot size
        raw_lot_size = risk_amount / loss_per_lot
        
        # MT5 usually requires lot sizes in increments of 0.01
        lot_size = round(raw_lot_size, 2)
        
        # Enforce minimum lot size 
        lot_size = max(0.01, lot_size)
        
        return lot_size, sl_price

    def calculate_take_profit(self, entry_price: float, sl_price: float, rr_ratio: float = 3.0) -> float:
        """
        Calculates Take-Profit target at a minimum 1:3 Risk-to-Reward ratio.
        """
        sl_dist = abs(entry_price - sl_price)
        reward_dist = sl_dist * rr_ratio
        
        if entry_price > sl_price:
            # Long position
            return entry_price + reward_dist
        else:
            # Short position
            return entry_price - reward_dist

risk_manager = RiskManager()
