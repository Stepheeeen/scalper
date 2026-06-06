import pandas as pd
import numpy as np

class AIFilter:
    def __init__(self):
        self.model = None
        self.threshold = 0.70
        
    def load_model(self, path: str):
        """Loads a pre-trained XGBoost model."""
        import xgboost as xgb
        import os
        if path and os.path.exists(path):
            try:
                self.model = xgb.XGBClassifier()
                self.model.load_model(path)
                # Keep a log of model load
                import logging
                logging.getLogger("AIFilter").info(f"XGBoost model loaded successfully from {path}")
            except Exception as e:
                import logging
                logging.getLogger("AIFilter").error(f"Failed to load XGBoost model from {path}: {e}")
                self.model = None

    def predict_reversal_probability(self, features: dict) -> float:
        """
        Evaluates features (ATR, RSI, Volume ratio, Wick ratio).
        Returns a probability score for institutional reversal.
        """
        if self.model is None:
            return 0.85
            
        try:
            X = np.array([[
                float(features.get("atr", 0.0)),
                float(features.get("rsi", 0.0)),
                float(features.get("volume_ratio", 1.0)),
                float(features.get("wick_ratio", 0.5))
            ]])
            prob = self.model.predict_proba(X)
            return float(prob[0][1])
        except Exception as e:
            import logging
            logging.getLogger("AIFilter").error(f"Error predicting reversal probability: {e}")
            return 0.85
        
    def is_signal_approved(self, features: dict) -> bool:
        prob = self.predict_reversal_probability(features)
        return prob >= self.threshold

class MacroContext:
    def __init__(self):
        self.swing_highs = []
        self.swing_lows = []
        
    def update_structure(self, df_4h: pd.DataFrame):
        """
        Maps structural market swing highs and lows to identify major liquidity pools.
        Assumes df_4h has columns: open, high, low, close
        """
        if len(df_4h) < 5:
            return
            
        self.swing_highs = []
        self.swing_lows = []
        
        # A swing point is a high/low surrounded by lower/higher points on both sides (2 bars left, 2 bars right)
        for i in range(2, len(df_4h) - 2):
            center_high = df_4h.iloc[i]['high']
            if (center_high > df_4h.iloc[i-1]['high'] and 
                center_high > df_4h.iloc[i-2]['high'] and 
                center_high > df_4h.iloc[i+1]['high'] and 
                center_high > df_4h.iloc[i+2]['high']):
                self.swing_highs.append(float(center_high))
                
            center_low = df_4h.iloc[i]['low']
            if (center_low < df_4h.iloc[i-1]['low'] and 
                center_low < df_4h.iloc[i-2]['low'] and 
                center_low < df_4h.iloc[i+1]['low'] and 
                center_low < df_4h.iloc[i+2]['low']):
                self.swing_lows.append(float(center_low))
        
    def get_nearest_liquidity_pools(self, current_price: float) -> dict:
        """Returns the closest major swing high and low relative to current price."""
        nearest_high = None
        nearest_low = None
        
        highs_above = [h for h in self.swing_highs if h > current_price]
        if highs_above:
            nearest_high = min(highs_above)
            
        lows_below = [l for l in self.swing_lows if l < current_price]
        if lows_below:
            nearest_low = max(lows_below)
            
        return {
            "nearest_high": nearest_high, 
            "nearest_low": nearest_low
        }

class AsianRangeTracker:
    def __init__(self):
        self.asian_high = None
        self.asian_low = None
        
    def calculate_range(self, df_15m: pd.DataFrame, target_date: pd.Timestamp):
        """
        Programmatically calculates the absolute max High and Low of the Asian session 
        for the given date based on config settings.
        """
        from config.settings import settings
        
        start_hour, start_min = map(int, settings.asian_session.start_utc.split(':'))
        end_hour, end_min = map(int, settings.asian_session.end_utc.split(':'))
        
        start_time = pd.Timestamp(f"{start_hour:02d}:{start_min:02d}").time()
        end_time = pd.Timestamp(f"{end_hour:02d}:{end_min:02d}").time()
        
        # Filter for the target date and Asian session hours
        asian_mask = (df_15m.index.date == target_date.date()) & \
                     (df_15m.index.time >= start_time) & \
                     (df_15m.index.time <= end_time)
                     
        asian_session_data = df_15m[asian_mask]
        
        if not asian_session_data.empty:
            self.asian_high = asian_session_data['high'].max()
            self.asian_low = asian_session_data['low'].min()
            
    def get_boundaries(self) -> dict:
        return {
            "asian_high": self.asian_high,
            "asian_low": self.asian_low
        }

class AIEngine:
    def __init__(self):
        self.filter = AIFilter()
        self.macro = MacroContext()
        self.asian_range = AsianRangeTracker()

ai_engine = AIEngine()
