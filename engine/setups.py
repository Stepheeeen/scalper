import pandas as pd
from typing import Dict, Optional, List
from .structure import MarketStructureEngine, Trend

class BaseDetector:
    def __init__(self, structure_engine: MarketStructureEngine):
        self.structure = structure_engine

    def is_pin_bar(self, candle: pd.Series) -> bool:
        """
        Detects a Pin Bar: Wick > 2/3 of total candle size.
        """
        body = abs(candle['open'] - candle['close'])
        total = candle['high'] - candle['low']
        if total == 0: return False
        
        # Wick size (upper or lower)
        upper_wick = candle['high'] - max(candle['open'], candle['close'])
        lower_wick = min(candle['open'], candle['close']) - candle['low']
        
        return (upper_wick > total * 0.66) or (lower_wick > total * 0.66)

    def is_engulfing(self, prev: pd.Series, curr: pd.Series) -> Optional[str]:
        """
        Detects Bullish or Bearish Engulfing.
        """
        if curr['close'] > curr['open'] and prev['close'] < prev['open']:
            if curr['close'] > prev['open'] and curr['open'] < prev['close']:
                return "BULLISH"
        elif curr['close'] < curr['open'] and prev['close'] > prev['open']:
            if curr['close'] < prev['open'] and curr['open'] > prev['close']:
                return "BEARISH"
        return None

class TrendPullbackDetector(BaseDetector):
    def detect(self, df: pd.DataFrame, bias: Dict) -> Optional[Dict]:
        """
        Logic: Trend + Retrace to Level + Rejection.
        """
        if bias['bias'] == Trend.NEUTRAL: return None
        
        curr = df.iloc[-1]
        prev = df.iloc[-2]
        
        # Area of Value (AOV): Retrace to previous swing level (flip S/R)
        last_high = bias['last_high']
        last_low = bias['last_low']
        
        if bias['bias'] == Trend.BULLISH:
            # Price pulls back to previous high (broken resistance)
            if curr['low'] <= last_high <= curr['high'] or abs(curr['low'] - last_high) < 0.10:
                if self.is_pin_bar(curr) or self.is_engulfing(prev, curr) == "BULLISH":
                    return {"type": "TREND_PULLBACK", "side": "BUY", "level": last_high}
        
        elif bias['bias'] == Trend.BEARISH:
            # Price pulls back to previous low (broken support)
            if curr['low'] <= last_low <= curr['high'] or abs(curr['high'] - last_low) < 0.10:
                if self.is_pin_bar(curr) or self.is_engulfing(prev, curr) == "BEARISH":
                    return {"type": "TREND_PULLBACK", "side": "SELL", "level": last_low}
        
        return None

class BreakoutTrapDetector(BaseDetector):
    def detect(self, df: pd.DataFrame, levels: Dict) -> Optional[Dict]:
        """
        Logic: Liquidity Sweep + Rejection Return to Range.
        Matches Spring (Bullish) and Upthrust (Bearish).
        """
        curr = df.iloc[-1]
        pdh = levels.get('pdh')
        pdl = levels.get('pdl')
        
        if not pdh or not pdl: return None

        # Upthrust (Bearish Trap)
        if curr['high'] > pdh and curr['close'] < pdh:
            if self.is_pin_bar(curr):
                return {"type": "BREAKOUT_TRAP", "side": "SELL", "level": pdh, "subtype": "UPTHRUST"}
        
        # Spring (Bullish Trap)
        if curr['low'] < pdl and curr['close'] > pdl:
            if self.is_pin_bar(curr):
                return {"type": "BREAKOUT_TRAP", "side": "BUY", "level": pdl, "subtype": "SPRING"}
                
        return None

class InsideBarDetector(BaseDetector):
    def detect(self, df: pd.DataFrame, bias: Dict) -> Optional[Dict]:
        """
        Logic: Child bar inside Mother bar + Breakout in trend direction.
        """
        if len(df) < 3: return None
        mother = df.iloc[-2]
        child = df.iloc[-1]
        
        is_inside = child['high'] < mother['high'] and child['low'] > mother['low']
        
        if is_inside:
            # We don't enter on the inside bar itself, but on the break of the mother bar.
            # This detector identifies the 'setup' phase.
            return {"type": "INSIDE_BAR_SETUP", "side": "WAIT", "mother_high": mother['high'], "mother_low": mother['low']}
            
        return None

class PinBarReversalDetector(BaseDetector):
    def detect(self, df: pd.DataFrame, levels: Dict) -> Optional[Dict]:
        """
        Logic: High-quality Pin Bar at a major S/R or session extreme.
        """
        curr = df.iloc[-1]
        if not self.is_pin_bar(curr): return None
        
        # Check if near key levels
        for name, level in levels.items():
            if abs(curr['high'] - level) < 0.10 or abs(curr['low'] - level) < 0.10:
                side = "BUY" if (curr['close'] - curr['low']) > (curr['high'] - curr['close']) else "SELL"
                return {"type": "PIN_BAR_REVERSAL", "side": side, "level": level, "level_name": name}
        
        return None

class SetupEngine:
    def __init__(self):
        self.structure = MarketStructureEngine()
        self.detectors = [
            TrendPullbackDetector(self.structure),
            BreakoutTrapDetector(self.structure),
            InsideBarDetector(self.structure),
            PinBarReversalDetector(self.structure)
        ]

    def scan(self, data: Dict[str, pd.DataFrame], levels: Dict) -> List[Dict]:
        """
        Scans for all qualified setups.
        """
        df_entry = data.get('entry') # M5 usually
        df_htf = data.get('htf')     # H1 usually
        
        if df_entry is None or df_htf is None: return []
        
        bias = self.structure.calculate_bias(df_htf)
        setups = []
        
        for detector in self.detectors:
            if isinstance(detector, TrendPullbackDetector) or isinstance(detector, InsideBarDetector):
                res = detector.detect(df_entry, bias)
            else:
                res = detector.detect(df_entry, levels)
            
            if res:
                res['bias_alignment'] = bias['bias'].value
                setups.append(res)
                
        return setups
