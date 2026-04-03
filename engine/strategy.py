import pandas as pd
import numpy as np
from typing import Dict, Optional
from utils.logger import logger
from .structure import MarketStructureEngine, Trend

class StrategyEngine:
    """
    Implements a professional 5/20 EMA Crossover strategy for XAUUSD.
    Includes M15 Trend Filter and Swing-based SL logic.
    """
    def __init__(self, config):
        self.config = config
        self.structure = MarketStructureEngine()

    def analyze(self, data: Dict[str, pd.DataFrame]) -> Optional[Dict]:
        """
        Analyzes 1m/5m/15m data for EMA crossovers and trend alignment.
        """
        df_1m = data.get('1m')
        df_5m = data.get('5m')
        df_15m = data.get('15m')

        if any(df is None or df.empty for df in [df_1m, df_5m, df_15m]):
            return None

        # 1. Trend Filter (M15 200 EMA)
        ema_200_m15 = df_15m['close'].ewm(span=self.config.strategy.trend_ema, adjust=False).mean()
        current_price_m15 = df_15m['close'].iloc[-1]
        trend_m15 = Trend.BULLISH if current_price_m15 > ema_200_m15.iloc[-1] else Trend.BEARISH
        
        # 2. Crossover Detection (1m or 5m based on preference, here using 1m for scalping)
        ema_5 = df_1m['close'].ewm(span=self.config.strategy.ema_fast, adjust=False).mean()
        ema_20 = df_1m['close'].ewm(span=self.config.strategy.ema_slow, adjust=False).mean()

        # Check for crossover in the last 2 candles
        previous_fast = ema_5.iloc[-2]
        previous_slow = ema_20.iloc[-2]
        current_fast = ema_5.iloc[-1]
        current_slow = ema_20.iloc[-1]

        is_bullish_cross = previous_fast <= previous_slow and current_fast > current_slow
        is_bearish_cross = previous_fast >= previous_slow and current_fast < current_slow

        signal_side = None
        reason = ""

        if is_bullish_cross:
            if trend_m15 == Trend.BULLISH:
                signal_side = "BUY"
                reason = "5/20 EMA Bullish Cross aligned with M15 Trend"
            else:
                logger.debug("Bullish cross detected but M15 Trend is Bearish. Skipping.")

        elif is_bearish_cross:
            if trend_m15 == Trend.BEARISH:
                signal_side = "SELL"
                reason = "5/20 EMA Bearish Cross aligned with M15 Trend"
            else:
                logger.debug("Bearish cross detected but M15 Trend is Bullish. Skipping.")

        if not signal_side:
            return None

        # 3. Dynamic Stop Loss (Recent Swing High/Low)
        # Using previous 10 candles (excluding current) for swings
        lookback = 10
        min_sl_dist = 0.50 # 5 pips minimum for Gold
        max_sl_dist = 2.50 # 25 pips maximum
        entry = df_1m['close'].iloc[-1]

        if signal_side == "BUY":
            swing_low = df_1m['low'].iloc[-lookback-1:-1].min()
            sl = min(entry - min_sl_dist, max(swing_low, entry - max_sl_dist))
        else:
            swing_high = df_1m['high'].iloc[-lookback-1:-1].max()
            sl = max(entry + min_sl_dist, min(swing_high, entry + max_sl_dist))

        return {
            "symbol": self.config.strategy.symbol,
            "side": signal_side,
            "entry_price": df_1m['close'].iloc[-1],
            "stop_loss": sl,
            "reason": reason
        }

    def check_exit_condition(self, current_data: pd.DataFrame, side: str) -> bool:
        """
        Checks for a 'Reverse Crossover' to exit trades early.
        """
        if len(current_data) < 2: return False
        
        ema_5 = current_data['close'].ewm(span=self.config.strategy.ema_fast, adjust=False).mean()
        ema_20 = current_data['close'].ewm(span=self.config.strategy.ema_slow, adjust=False).mean()
        
        current_fast = ema_5.iloc[-1]
        current_slow = ema_20.iloc[-1]
        
        if side == "BUY" and current_fast < current_slow:
            return True # Exit on Bearish Cross
        if side == "SELL" and current_fast > current_slow:
            return True # Exit on Bullish Cross
            
        return False
