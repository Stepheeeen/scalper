import pandas as pd
from datetime import datetime, time, timedelta
from typing import Dict, Optional, List
from config import config

class MarketDataManager:
    """
    Tracks session ranges (high/low), previous day high/low (PDH/PDL), and daily open.
    Handles timezone offsets for global session mapping.
    """
    def __init__(self, utc_offset: int = 0):
        self.utc_offset = utc_offset
        self.daily_stats = {}

    def get_session_status(self, current_time_utc: datetime) -> Dict:
        """
        Checks if the current UTC time falls within any defined kill zones.
        """
        current_time_str = current_time_utc.strftime("%H:%M")
        active_sessions = []
        
        for session in config.sessions:
            if session.start_time <= current_time_str <= session.end_time:
                active_sessions.append(session.name)
        
        return {
            "is_market_open": len(active_sessions) > 0,
            "active_sessions": active_sessions,
            "current_time_utc": current_time_str
        }

    def calculate_levels(self, h1_data: pd.DataFrame, d1_data: pd.DataFrame) -> Dict:
        """
        Identifies key naked price action levels: PDH, PDL, and Daily Open.
        """
        if d1_data.empty or len(d1_data) < 2:
            return {}

        prev_day = d1_data.iloc[-2]
        current_day = d1_data.iloc[-1]

        levels = {
            "pdh": prev_day['high'],
            "pdl": prev_day['low'],
            "daily_open": current_day['open'],
            "prev_close": prev_day['close']
        }
        
        return levels

    def get_session_extremes(self, df: pd.DataFrame, session_name: str) -> Dict:
        """
        Finds the high and low of a specific session window.
        """
        # This assumes df index is datetime and UTC
        session_config = next((s for s in config.sessions if s.name == session_name), None)
        if not session_config:
            return {}

        start_time = time.fromisoformat(session_config.start_time)
        end_time = time.fromisoformat(session_config.end_time)
        
        session_df = df.between_time(start_time, end_time)
        
        if session_df.empty:
            return {}

        return {
            "high": session_df['high'].max(),
            "low": session_df['low'].min(),
            "session": session_name
        }

    def is_volatility_sane(self, df: pd.DataFrame, threshold_atr_mult: float = 2.0) -> bool:
        """
        Sanity filter to avoid trading in abnormal/unstable volatility.
        Uses ATR comparison.
        """
        if len(df) < 20:
            return True
            
        high_low = df['high'] - df['low']
        high_close = (df['high'] - df['close'].shift()).abs()
        low_close = (df['low'] - df['close'].shift()).abs()
        
        tr = pd.concat([high_low, high_close, low_close], axis=1).max(axis=1)
        atr = tr.rolling(window=14).mean()
        
        current_atr = atr.iloc[-1]
        avg_atr = atr.iloc[-20:-1].mean()
        
        return current_atr < (avg_atr * threshold_atr_mult)
