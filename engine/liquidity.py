import pandas as pd
from typing import Dict, List, Optional
from dataclasses import dataclass

@dataclass
class LiquidityZone:
    price: float
    type: str # 'BSL' (Buy Side Liquidity) or 'SSL' (Sell Side Liquidity)
    description: str

class LiquidityEngine:
    """
    Identifies institutional liquidity pools and detects sweeps.
    Focuses on: Asian Range, Previous Session Highs/Lows, and Equal Highs/Lows.
    """
    def __init__(self):
        self.zones: List[LiquidityZone] = []

    def get_asian_range(self, df: pd.DataFrame) -> Optional[Dict]:
        """
        Calculates the high and low of the Asian session (00:00 - 08:00 UTC).
        Assumes df index is datetime.
        """
        asian_df = df.between_time('00:00', '08:00')
        if asian_df.empty:
            return None
            
        high = asian_df['high'].max()
        low = asian_df['low'].min()
        
        return {
            "high": high, 
            "low": low, 
            "range": high - low
        }

    def is_in_session(self, current_time: pd.Timestamp, sessions: List[Dict]) -> bool:
        """
        Checks if the current time falls within any active trading session.
        """
        time_str = current_time.strftime('%H:%M')
        for session in sessions:
            if session['start'] <= time_str <= session['end']:
                return True
        return False

    def detect_sweep(self, current_price: float, zones: List[LiquidityZone]) -> Optional[LiquidityZone]:
        """
        Checks if current price has 'swept' a known liquidity zone.
        A sweep is defined as price moving past the zone and then rejecting.
        """
        for zone in zones:
            if zone.type == 'SSL' and current_price < zone.price:
                # Potential Sell-side sweep
                return zone
            if zone.type == 'BSL' and current_price > zone.price:
                # Potential Buy-side sweep
                return zone
        return None

    def find_equal_highs_lows(self, df: pd.DataFrame, threshold_pips: float = 2.0) -> List[LiquidityZone]:
        """
        Detects 'retail' double tops/bottoms (Equal Highs/Lows) which act as magnets.
        """
        zones = []
        # Logic to find clusters of highs/lows within threshold
        return zones

    def calculate_premium_discount(self, df: pd.DataFrame) -> Dict:
        """
        Calculates the 50% level of the recent range.
        Sells should only be in Premium (above 0.5).
        Buys should only be in Discount (below 0.5).
        """
        if df.empty: return {}
        
        high = df['high'].max()
        low = df['low'].min()
        mid = (high + low) / 2
        
        current_price = df['close'].iloc[-1]
        
        return {
            "high": high,
            "low": low,
            "mid": mid,
            "is_premium": current_price > mid,
            "is_discount": current_price < mid
        }

    def detect_liquidity_gaps(self, df: pd.DataFrame, min_gap_size: float = 5.0) -> List[Dict]:
        """
        Identifies sharp price movements that leave behind liquidity 'voids'.
        These are similar to FVGs but focus on pure momentum.
        """
        gaps = []
        if len(df) < 2: return gaps
        
        for i in range(1, len(df)):
            body = abs(df['close'].iloc[i] - df['open'].iloc[i])
            if body > min_gap_size:
                gaps.append({
                    "top": max(df['open'].iloc[i], df['close'].iloc[i]),
                    "bottom": min(df['open'].iloc[i], df['close'].iloc[i]),
                    "side": "BULLISH" if df['close'].iloc[i] > df['open'].iloc[i] else "BEARISH",
                    "index": i
                })
        return gaps
