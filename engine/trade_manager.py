from typing import Dict, List, Optional
from utils.logger import logger
from config import config
from .mt5_adapter import MT5Adapter
from risk.manager import RiskManager

class TradeManager:
    """
    Monitors active positions and handles real-time trade management.
    - BE logic
    - Partial profit taking (if enabled)
    - Early exit logic (if structure shifts)
    """
    def __init__(self, broker: MT5Adapter, risk_manager: RiskManager):
        self.broker = broker
        self.risk_manager = risk_manager
        self.active_positions = []

    def update_positions(self, symbol: str):
        """
        Synchronizes local position list with broker.
        """
        # In a real bot, we'd fetch actual open positions from MT5
        # For now, we'll use a local list to track tickets
        pass

    def manage_lifecycle(self, current_tick: Dict):
        """
        Main loop for managing open trades.
        """
        bid = current_tick['bid']
        ask = current_tick['ask']

        for pos in self.active_positions[:]:
            side = pos['side']
            entry = pos['entry']
            tp = pos['tp']
            sl = pos['sl']
            price = bid if side == "BUY" else ask
            
            # 1. Check for Break-Even Trigger
            if not pos.get('is_be') and self.risk_manager.should_move_to_be(entry, price, side):
                success = self.broker.modify_order(pos['ticket'], entry, tp)
                if success:
                    pos['is_be'] = True
                    logger.info(f"Trade {pos['ticket']} moved to Break-Even at {entry}")
                    # In a full flow, this would trigger a Telegram alert

            # 2. Check if SL or TP hit (For Paper Trading mostly)
            if config.paper_trading:
                if side == "BUY":
                    if price <= sl: self.close_trade(pos, "SL_HIT", price)
                    elif price >= tp: self.close_trade(pos, "TP_HIT", price)
                else:
                    if price >= sl: self.close_trade(pos, "SL_HIT", price)
                    elif price <= tp: self.close_trade(pos, "TP_HIT", price)

    def close_trade(self, pos: Dict, reason: str, exit_price: float):
        """Closes a trade and handles post-trade logic."""
        success = self.broker.close_order(pos['ticket'])
        if success:
            profit = (exit_price - pos['entry']) if pos['side'] == "BUY" else (pos['entry'] - exit_price)
            # Gold: $1 move = $100 for 1.0 lot
            profit_dollars = profit * pos['lots'] * 100
            
            self.risk_manager.register_trade_result(profit_dollars)
            self.active_positions.remove(pos)
            
            logger.info(f"Trade Closed: {pos['ticket']} | Side: {pos['side']} | Reason: {reason} | P/L: ${profit_dollars:.2f}")

    def add_position(self, ticket: int, side: str, entry: float, sl: float, tp: float, lots: float):
        self.active_positions.append({
            "ticket": ticket,
            "side": side,
            "entry": entry,
            "sl": sl,
            "tp": tp,
            "lots": lots,
            "is_be": False
        })
