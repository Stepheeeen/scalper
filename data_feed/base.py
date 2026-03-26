import pandas as pd
from abc import ABC, abstractmethod
from typing import Optional, Dict

class BaseDataProvider(ABC):
    """
    Abstract base class for data providers (MT5, OANDA, Mock, etc.)
    """
    @abstractmethod
    def connect(self) -> bool:
        pass

    @abstractmethod
    def get_latest_candles(self, symbol: str, timeframe: str, count: int) -> pd.DataFrame:
        pass

    @abstractmethod
    def execute_order(self, symbol: str, order_type: str, volume: float, sl: float, tp: float) -> Dict:
        pass

class MockDataProvider(BaseDataProvider):
    """
    Mock provider for testing and development.
    """
    def connect(self) -> bool:
        return True

    def get_latest_candles(self, symbol: str, timeframe: str, count: int) -> pd.DataFrame:
        """
        Generates a more realistic mock dataset that includes:
        1. A range (Asian session mock)
        2. A liquidity sweep (SSL)
        3. Displacement and FVG
        """
        # Base prices
        prices = [2000.0] * count
        highs = [2001.0] * count
        lows = [1999.0] * count
        opens = [2000.0] * count
        
        # 1. Create a "Range" for the first 80 candles
        # (This acts as the liquidity pool)
        
        # 2. Candle 81-85: Sell-side Sweep (SSL)
        # Price drops below 1999.0
        for i in range(80, 85):
            lows[i] = 1990.0 - (i-80)
            prices[i] = 1992.0
            
        # 3. Candle 86-90: Bullish Displacement & FVG
        # Large movement up
        # Candle 86: Open 1992, Close 2005 (Huge displacement)
        opens[86] = 1992.0
        prices[86] = 2005.0
        highs[86] = 2006.0
        lows[86] = 1991.0
        
        # Candle 87: Open 2005, Close 2015
        opens[87] = 2005.0
        prices[87] = 2015.0
        highs[87] = 2016.0
        lows[87] = 2004.0
        
        # Candle 88 (FVG creation): Open 2015, Close 2025
        # High of 86 (2006) < Low of 88 (2020) -> Gap!
        opens[88] = 2015.0
        prices[88] = 2025.0
        highs[88] = 2026.0
        lows[88] = 2020.0
        
        data = {
            'open': opens,
            'high': highs,
            'low': lows,
            'close': prices
        }
        df = pd.DataFrame(data)
        df.index = pd.date_range(start='2024-03-18 00:00', periods=count, freq='1min')
        return df

    def execute_order(self, symbol: str, order_type: str, volume: float, sl: float, tp: float) -> Dict:
        return {"status": "SUCCESS", "order_id": 12345}
