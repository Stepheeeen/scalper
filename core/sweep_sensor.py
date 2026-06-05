import pandas as pd
from typing import Optional, Dict

class SweepSensor:
    def __init__(self):
        # We consider a wick "prominent" if it's at least X% of the entire candle's range
        # or greater than a specific pip threshold, but for now we just check basic structure.
        self.wick_threshold_ratio = 0.5 

    def check_for_sweep(self, candle: pd.Series, boundaries: list[float]) -> Optional[Dict]:
        """
        Monitors 15M candle action.
        A raw trade signal is generated ONLY if the candle spikes outside a level 
        but aggressively closes back *inside* the boundary, leaving a prominent stop-running wick.
        
        boundaries: List of important price levels (e.g., 4H highs/lows, Asian high/low)
        """
        open_p = candle['open']
        high_p = candle['high']
        low_p = candle['low']
        close_p = candle['close']
        
        candle_range = high_p - low_p
        if candle_range == 0:
            return None
            
        # Check against each boundary
        for level in boundaries:
            if level is None:
                continue
                
            # Bullish Sweep (Sweeps below a support level, then closes above it)
            if low_p < level and close_p > level:
                lower_wick = min(open_p, close_p) - low_p
                # Ensure the wick is prominent
                if lower_wick / candle_range >= self.wick_threshold_ratio:
                    return {
                        "type": "bullish_sweep",
                        "level_swept": level,
                        "entry": close_p,
                        "stop_loss": low_p, # SL at the extreme tip of the rejection wick
                    }
                    
            # Bearish Sweep (Sweeps above a resistance level, then closes below it)
            elif high_p > level and close_p < level:
                upper_wick = high_p - max(open_p, close_p)
                # Ensure the wick is prominent
                if upper_wick / candle_range >= self.wick_threshold_ratio:
                    return {
                        "type": "bearish_sweep",
                        "level_swept": level,
                        "entry": close_p,
                        "stop_loss": high_p, # SL at the extreme tip of the rejection wick
                    }
                    
        return None

sweep_sensor = SweepSensor()
