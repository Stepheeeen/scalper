import pandas as pd
import numpy as np
from typing import Dict, Optional, List
from enum import Enum

class Trend(Enum):
    BULLISH = "BULLISH"
    BEARISH = "BEARISH"
    NEUTRAL = "NEUTRAL"

class MarketStructureEngine:
    """
    Analyzes price action for HH/HL (Bullish) and LH/LL (Bearish) trends.
    Detects Break of Structure (BOS) and Liquidity Pools.
    """
    def __init__(self, window: int = 5):
        self.window = window

    def calculate_bias(self, df: pd.DataFrame) -> Dict:
        """
        Determines the directional bias using HH/HL and LH/LL swing structure.
        """
        if len(df) < 50:
            return {"bias": Trend.NEUTRAL, "reason": "Insufficient data"}

        swings = self.detect_fractals(df)
        highs = [h[1] for h in swings["highs"]]
        lows = [l[1] for l in swings["lows"]]

        if len(highs) < 2 or len(lows) < 2:
            return {"bias": Trend.NEUTRAL, "reason": "No clear structure"}

        # Check for HH/HL (Bullish)
        is_hh = highs[-1] > highs[-2]
        is_hl = lows[-1] > lows[-2]
        
        # Check for LH/LL (Bearish)
        is_lh = highs[-1] < highs[-2]
        is_ll = lows[-1] < lows[-2]

        bias = Trend.NEUTRAL
        reason = "Ranging / No clear trend"

        if is_hh and is_hl:
            bias = Trend.BULLISH
            reason = "Market making Higher Highs and Higher Lows"
        elif is_lh and is_ll:
            bias = Trend.BEARISH
            reason = "Market making Lower Highs and Lower Lows"
        elif is_hh and not is_hl:
            bias = Trend.BULLISH
            reason = "Bullish BOS detected, waiting for HL"
        elif is_ll and not is_lh:
            bias = Trend.BEARISH
            reason = "Bearish BOS detected, waiting for LH"

        return {
            "bias": bias,
            "reason": reason,
            "last_high": highs[-1],
            "last_low": lows[-1],
            "prev_high": highs[-2],
            "prev_low": lows[-2]
        }

    def detect_fractals(self, df: pd.DataFrame) -> Dict[str, List]:
        """
        Identifies fractal highs and lows (swing points).
        Uses a configurable window (default 5).
        """
        highs = df['high'].values
        lows = df['low'].values
        fractal_highs = []
        fractal_lows = []
        
        for i in range(self.window, len(df) - self.window):
            # Fractal High: Highest in the window
            if all(highs[i] >= highs[i-j] for j in range(1, self.window+1)) and \
               all(highs[i] > highs[i+j] for j in range(1, self.window+1)):
                fractal_highs.append((i, highs[i]))
            
            # Fractal Low: Lowest in the window
            if all(lows[i] <= lows[i-j] for j in range(1, self.window+1)) and \
               all(lows[i] < lows[i+j] for j in range(1, self.window+1)):
                fractal_lows.append((i, lows[i]))
        
        return {"highs": fractal_highs, "lows": fractal_lows}

    def find_liquidity_pools(self, df: pd.DataFrame) -> Dict[str, List[float]]:
        """
        Identifies 'Equal Highs' and 'Equal Lows' where liquidity resides.
        """
        swings = self.detect_fractals(df)
        highs = [h[1] for h in swings["highs"]]
        lows = [l[1] for l in swings["lows"]]
        
        eqh = []
        eql = []
        threshold = 0.0005 # 5 pips for XAUUSD (pips are 0.01, so 0.0005 is 0.05 points)
        # Actually for Gold, 0.10 points is 10 pips. 0.05 points = 5 pips.
        
        for i in range(len(highs)-1):
            for j in range(i+1, len(highs)):
                if abs(highs[i] - highs[j]) < 0.10: # ~10 pips
                    eqh.append(max(highs[i], highs[j]))
                    
        for i in range(len(lows)-1):
            for j in range(i+1, len(lows)):
                if abs(lows[i] - lows[j]) < 0.10:
                    eql.append(min(lows[i], lows[j]))
                    
        return {"equal_highs": list(set(eqh)), "equal_lows": list(set(eql))}

    def detect_bos_choch(self, df: pd.DataFrame) -> Dict:
        """
        Detects Break of Structure (BOS) and Change of Character (CHOCH).
        BOS: Trend continuation.
        CHOCH: Shift in trend.
        """
        swings = self.detect_fractals(df)
        if len(swings['highs']) < 2 or len(swings['lows']) < 2:
            return {"type": None}

        last_high = swings['highs'][-1][1]
        last_low = swings['lows'][-1][1]
        current_price = df['close'].iloc[-1]

        # Simplified logic:
        if current_price > last_high:
            return {"type": "BOS", "side": "BULLISH", "level": last_high}
        elif current_price < last_low:
            return {"type": "BOS", "side": "BEARISH", "level": last_low}
            
        return {"type": None}
