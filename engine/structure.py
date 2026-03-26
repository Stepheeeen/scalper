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
    Analyzes price action for Break of Structure (BOS) and Change of Character (CHOCH).
    Handles trend bias calculation based on HTF (5m/15m).
    """
    def __init__(self, fast_ema: int = 50, slow_ema: int = 200):
        self.fast_ema = fast_ema
        self.slow_ema = slow_ema

    def calculate_bias(self, df: pd.DataFrame) -> Dict:
        """
        Determines the directional bias using EMAs and Structure.
        df must contain 'high', 'low', 'close' columns.
        """
        if len(df) < self.slow_ema:
            return {"bias": Trend.NEUTRAL, "reason": "Insufficient data"}

        # EMA Alignment
        ema_fast = df['close'].ewm(span=self.fast_ema, adjust=False).mean()
        ema_slow = df['close'].ewm(span=self.slow_ema, adjust=False).mean()
        
        last_close = df['close'].iloc[-1]
        last_fast = ema_fast.iloc[-1]
        last_slow = ema_slow.iloc[-1]

        ema_bullish = last_fast > last_slow and last_close > last_fast
        ema_bearish = last_fast < last_slow and last_close < last_fast

        # Simple Swing Detection for BOS/CHOCH
        # In a real bot, this would use fractal highs/lows
        highs = df['high'].rolling(window=5, center=True).max()
        lows = df['low'].rolling(window=5, center=True).min()
        
        # Determine Bias
        bias = Trend.NEUTRAL
        if ema_bullish:
            bias = Trend.BULLISH
        elif ema_bearish:
            bias = Trend.BEARISH

        return {
            "bias": bias,
            "ema_fast": last_fast,
            "ema_slow": last_slow,
            "ema_aligned": ema_bullish or ema_bearish
        }

    def detect_fractals(self, df: pd.DataFrame, window: int = 2) -> Dict:
        """
        Identifies fractal highs and lows.
        """
        highs = df['high'].values
        lows = df['low'].values
        fractal_highs = []
        fractal_lows = []
        
        for i in range(window, len(df) - window):
            if all(highs[i] > highs[i-j] for j in range(1, window+1)) and \
               all(highs[i] > highs[i+j] for j in range(1, window+1)):
                fractal_highs.append((i, highs[i]))
            if all(lows[i] < lows[i-j] for j in range(1, window+1)) and \
               all(lows[i] < lows[i+j] for j in range(1, window+1)):
                fractal_lows.append((i, lows[i]))
        
        return {"highs": fractal_highs, "lows": fractal_lows}

    def detect_fvg(self, df: pd.DataFrame) -> List[Dict]:
        """
        Identifies Fair Value Gaps (FVG) / Imbalances.
        A bullish FVG: Low of candle 3 > High of candle 1
        A bearish FVG: High of candle 3 < Low of candle 1
        """
        fvgs = []
        if len(df) < 3: return fvgs
        
        for i in range(2, len(df)):
            # Bullish FVG
            if df['low'].iloc[i] > df['high'].iloc[i-2]:
                fvgs.append({
                    "type": "BULLISH",
                    "top": df['low'].iloc[i],
                    "bottom": df['high'].iloc[i-2],
                    "index": i-1
                })
            # Bearish FVG
            elif df['high'].iloc[i] < df['low'].iloc[i-2]:
                fvgs.append({
                    "type": "BEARISH",
                    "top": df['low'].iloc[i-2],
                    "bottom": df['high'].iloc[i],
                    "index": i-1
                })
        return fvgs

    def detect_displacement(self, df: pd.DataFrame, atr_threshold: float) -> bool:
        """
        A displacement candle is a large momentum candle that shows strong 'intent'.
        Typically > 1.5x - 2x the recent ATR.
        """
        if len(df) < 2: return False
        body_size = abs(df['close'].iloc[-1] - df['open'].iloc[-1])
        return body_size > atr_threshold

    def detect_order_blocks(self, df: pd.DataFrame) -> List[Dict]:
        """
        Identifies Order Blocks (OB).
        Bullish OB: Last bearish candle before a strong bullish move.
        Bearish OB: Last bullish candle before a strong bearish move.
        """
        obs = []
        if len(df) < 5: return obs
        
        for i in range(1, len(df) - 1):
            # Bullish OB: Bearish candle followed by a strong Bullish candle
            if df['close'].iloc[i] < df['open'].iloc[i]: # Bearish candle
                if df['close'].iloc[i+1] > df['open'].iloc[i+1]: # Next is Bullish
                    # Check for displacement or BOS (Simplified here)
                    if (df['close'].iloc[i+1] - df['open'].iloc[i+1]) > (df['high'].iloc[i-3:i].max() - df['low'].iloc[i-3:i].min()):
                        obs.append({
                            "type": "BULLISH",
                            "top": df['high'].iloc[i],
                            "bottom": df['low'].iloc[i],
                            "index": i,
                            "timestamp": df.index[i]
                        })
            
            # Bearish OB: Bullish candle followed by a strong Bearish candle
            elif df['close'].iloc[i] > df['open'].iloc[i]: # Bullish candle
                if df['close'].iloc[i+1] < df['open'].iloc[i+1]: # Next is Bearish
                    if (df['open'].iloc[i+1] - df['close'].iloc[i+1]) > (df['high'].iloc[i-3:i].max() - df['low'].iloc[i-3:i].min()):
                        obs.append({
                            "type": "BEARISH",
                            "top": df['high'].iloc[i],
                            "bottom": df['low'].iloc[i],
                            "index": i,
                            "timestamp": df.index[i]
                        })
        return obs
