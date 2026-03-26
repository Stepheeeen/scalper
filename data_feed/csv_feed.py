import pandas as pd
from .base import BaseDataProvider
from typing import Dict

class CSVDataProvider(BaseDataProvider):
    """
    Loads historical OHLCV data from CSV files for backtesting.
    """
    def __init__(self, file_paths: Dict[str, str]):
        self.data = {tf: pd.read_csv(path, index_col='datetime', parse_dates=True) for tf, path in file_paths.items()}
        self.current_idx = 0

    def connect(self) -> bool:
        return True

    def get_latest_candles(self, symbol: str, timeframe: str, count: int) -> pd.DataFrame:
        df = self.data.get(timeframe)
        if df is None or self.current_idx < count:
            return pd.DataFrame()
        return df.iloc[self.current_idx - count : self.current_idx]

    def execute_order(self, symbol: str, order_type: str, volume: float, sl: float, tp: float) -> Dict:
        # Simplified execution for backtesting - assuming fill at close
        return {"status": "SUCCESS", "price": 0.0} # Price will be determined by engine

    def advance(self):
        self.current_idx += 1
        return self.current_idx < len(next(iter(self.data.values())))
