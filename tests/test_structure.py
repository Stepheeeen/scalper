import pytest
import pandas as pd
import numpy as np
from engine.structure import MarketStructureEngine, Trend

def create_mock_df(prices):
    return pd.DataFrame({
        'open': prices,
        'high': [p + 0.1 for p in prices],
        'low': [p - 0.1 for p in prices],
        'close': prices
    })

def test_calculate_bias_bullish():
    engine = MarketStructureEngine(fast_ema=5, slow_ema=10)
    # Create an uptrend
    prices = [100 + i*0.5 for i in range(20)]
    df = create_mock_df(prices)
    
    bias_result = engine.calculate_bias(df)
    assert bias_result['bias'] == Trend.BULLISH

def test_calculate_bias_bearish():
    engine = MarketStructureEngine(fast_ema=5, slow_ema=10)
    # Create a downtrend
    prices = [100 - i*0.5 for i in range(20)]
    df = create_mock_df(prices)
    
    bias_result = engine.calculate_bias(df)
    assert bias_result['bias'] == Trend.BEARISH

def test_detect_fvg_bullish():
    engine = MarketStructureEngine()
    # Bullish FVG: Low of candle 3 > High of candle 1
    data = {
        'high': [10.0, 12.0, 15.0],
        'low':  [9.0, 11.0, 13.0],
        'close': [9.5, 11.5, 14.0]
    }
    df = pd.DataFrame(data)
    fvgs = engine.detect_fvg(df)
    
    assert len(fvgs) == 1
    assert fvgs[0]['type'] == "BULLISH"
    assert fvgs[0]['bottom'] == 10.0 # High of candle 0
    assert fvgs[0]['top'] == 13.0    # Low of candle 2

def test_detect_fvg_bearish():
    engine = MarketStructureEngine()
    # Bearish FVG: High of candle 3 < Low of candle 1
    data = {
        'high': [20.0, 18.0, 16.0],
        'low':  [19.0, 17.0, 14.0],
        'close': [19.5, 17.5, 15.0]
    }
    df = pd.DataFrame(data)
    fvgs = engine.detect_fvg(df)
    
    assert len(fvgs) == 1
    assert fvgs[0]['type'] == "BEARISH"
    assert fvgs[0]['top'] == 19.0    # Low of candle 0
    assert fvgs[0]['bottom'] == 16.0 # High of candle 2

def test_detect_displacement():
    engine = MarketStructureEngine()
    data = {
        'open': [10.0, 10.5],
        'high': [11.0, 12.5],
        'low':  [9.5, 10.0],
        'close': [10.5, 12.0]
    }
    df = pd.DataFrame(data)
    # Body size is 12.0 - 10.5 = 1.5
    assert engine.detect_displacement(df, 1.0) == True
    assert engine.detect_displacement(df, 2.0) == False
