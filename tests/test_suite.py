import unittest
import pandas as pd
from datetime import datetime, timezone
from core.risk_manager import risk_manager
from core.sweep_sensor import sweep_sensor
from core.discipline import warden
from core.ai_engine import AsianRangeTracker
from config.settings import settings

class TestRiskManager(unittest.TestCase):
    def test_calculate_lot_size_normal(self):
        # 1% risk of 10000 balance is 100.
        # Entry = 2000, SL = 1995. SL distance = 5.0.
        # Tick size = 0.01. points_at_risk = 500.
        # Contract size = 100, tick value = 1.0.
        # Loss per lot = 500 * 1 = 500.
        # Raw lot size = 100 / 500 = 0.2.
        lot_size, adjusted_sl = risk_manager.calculate_lot_size(10000.0, 2000.0, 1995.0)
        self.assertEqual(lot_size, 0.20)
        self.assertEqual(adjusted_sl, 1995.0)

    def test_calculate_lot_size_below_floor(self):
        # Entry = 2000, SL = 1999.5. SL distance = 0.5.
        # settings.min_sl_raw is 2.00.
        # The sl_dist should be adjusted to 2.00.
        # Adjusted SL price = 2000 - 2 = 1998.0 (for long).
        # Loss per lot = (2.0 / 0.01) * 1.0 = 200.
        # Risk amount = 100.
        # Lot size = 100 / 200 = 0.5.
        lot_size, adjusted_sl = risk_manager.calculate_lot_size(10000.0, 2000.0, 1999.5)
        self.assertEqual(adjusted_sl, 1998.0)
        self.assertEqual(lot_size, 0.50)

    def test_calculate_take_profit(self):
        # Entry = 2000, SL = 1995. SL distance = 5.0.
        # With R:R ratio = 3.0, TP distance = 15.0.
        # TP price = 2015.0 for long.
        tp_price = risk_manager.calculate_take_profit(2000.0, 1995.0)
        self.assertEqual(tp_price, 2015.0)


class TestSweepSensor(unittest.TestCase):
    def test_bullish_sweep(self):
        # Boundary at 2000.0
        # Candle sweeps below but closes above:
        # Low = 1990, Close = 2005, High = 2010, Open = 2000
        # Candle range = 20. lower wick = 2000 - 1990 = 10. wick ratio = 10/20 = 50%.
        candle = pd.Series({
            'open': 2000.0,
            'high': 2010.0,
            'low': 1990.0,
            'close': 2005.0
        })
        signal = sweep_sensor.check_for_sweep(candle, [2000.0])
        self.assertIsNotNone(signal)
        self.assertEqual(signal['type'], 'bullish_sweep')
        self.assertEqual(signal['level_swept'], 2000.0)
        self.assertEqual(signal['entry'], 2005.0)
        self.assertEqual(signal['stop_loss'], 1990.0)

    def test_bearish_sweep(self):
        # Boundary at 2000.0
        # Candle sweeps above but closes below:
        # High = 2010, Close = 1995, Low = 1990, Open = 2000
        # Candle range = 20. upper wick = 2010 - 2000 = 10. wick ratio = 10/20 = 50%.
        candle = pd.Series({
            'open': 2000.0,
            'high': 2010.0,
            'low': 1990.0,
            'close': 1995.0
        })
        signal = sweep_sensor.check_for_sweep(candle, [2000.0])
        self.assertIsNotNone(signal)
        self.assertEqual(signal['type'], 'bearish_sweep')
        self.assertEqual(signal['level_swept'], 2000.0)
        self.assertEqual(signal['entry'], 1995.0)
        self.assertEqual(signal['stop_loss'], 2010.0)

    def test_no_sweep_breakout(self):
        # Boundary at 2000.0
        # Low = 1990, Close = 1995. Closes below the boundary, so it's a breakout, not a sweep.
        candle = pd.Series({
            'open': 2000.0,
            'high': 2010.0,
            'low': 1990.0,
            'close': 1995.0
        })
        signal = sweep_sensor.check_for_sweep(candle, [2000.0])
        # Low is below, but close is also below.
        # Check bearish sweep: high is 2010 > 2000, close is 1995 < 2000.
        # Upper wick is 2010 - 2000 = 10. Range is 20. Ratio is 50%. So it matches bearish sweep!
        # Wait, what if we test something that is neither?
        # e.g., low = 1990, close = 1995, open = 1995, high = 1998.
        # Boundary at 2000.0
        # Neither low is below and close is above, nor high is above and close is below.
        candle_no_sweep = pd.Series({
            'open': 1995.0,
            'high': 1998.0,
            'low': 1990.0,
            'close': 1996.0
        })
        signal = sweep_sensor.check_for_sweep(candle_no_sweep, [2000.0])
        self.assertIsNone(signal)

    def test_insufficient_wick(self):
        # Boundary at 2000.0
        # Candle Low = 1998, Close = 2005, High = 2010, Open = 2005.
        # Candle range = 12. lower wick = 2005 - 1998 = 7. Wick ratio = 7 / 12 = 58.3% (passes ratio).
        # Let's make wick ratio fail (< 50%):
        # Low = 1998, Close = 2005, High = 2018, Open = 2006.
        # Range = 20. lower wick = 2005 - 1998 = 7. Wick ratio = 7 / 20 = 35% (< 50%).
        candle = pd.Series({
            'open': 2006.0,
            'high': 2018.0,
            'low': 1998.0,
            'close': 2005.0
        })
        signal = sweep_sensor.check_for_sweep(candle, [2000.0])
        self.assertIsNone(signal)


class TestWarden(unittest.TestCase):
    def setUp(self):
        self.original_bypass = settings.bypass_session_check
        settings.bypass_session_check = False

    def tearDown(self):
        settings.bypass_session_check = self.original_bypass

    def test_london_session_valid(self):
        # London Session: 07:00 to 11:00 UTC
        dt = datetime(2026, 6, 5, 8, 30, tzinfo=timezone.utc)
        self.assertTrue(warden.is_valid_trading_session(dt))

    def test_ny_session_valid(self):
        # NY Session: 12:00 to 16:00 UTC
        dt = datetime(2026, 6, 5, 13, 15, tzinfo=timezone.utc)
        self.assertTrue(warden.is_valid_trading_session(dt))

    def test_asian_session_invalid(self):
        # Asian Session (not London/NY): 03:00 UTC
        dt = datetime(2026, 6, 5, 3, 0, tzinfo=timezone.utc)
        self.assertFalse(warden.is_valid_trading_session(dt))

    def test_market_closed_weekend(self):
        # Saturday is closed
        dt_sat = datetime(2026, 6, 6, 12, 0, tzinfo=timezone.utc)
        self.assertTrue(warden.is_market_closed(dt_sat))
        # Friday after 22:00 UTC is closed
        dt_fri_night = datetime(2026, 6, 5, 22, 30, tzinfo=timezone.utc)
        self.assertTrue(warden.is_market_closed(dt_fri_night))
        # Friday before 22:00 UTC is open
        dt_fri_day = datetime(2026, 6, 5, 15, 0, tzinfo=timezone.utc)
        self.assertFalse(warden.is_market_closed(dt_fri_day))
        # Sunday after 22:00 UTC is open
        dt_sun_night = datetime(2026, 6, 7, 22, 30, tzinfo=timezone.utc)
        self.assertFalse(warden.is_market_closed(dt_sun_night))
        # Sunday before 22:00 UTC is closed
        dt_sun_day = datetime(2026, 6, 7, 15, 0, tzinfo=timezone.utc)
        self.assertTrue(warden.is_market_closed(dt_sun_day))

    def test_seconds_until_market_open(self):
        # Saturday June 6, 12:00 UTC. Next open is Sunday June 7, 22:00 UTC.
        # Difference should be 34 hours = 122400 seconds.
        dt_sat = datetime(2026, 6, 6, 12, 0, tzinfo=timezone.utc)
        seconds = warden.get_seconds_until_market_open(dt_sat)
        self.assertEqual(seconds, 34 * 3600.0)

    def test_seconds_until_next_session(self):
        # Tuesday, June 9, 02:00 UTC.
        # London Session starts at 07:00 UTC.
        # Difference should be 5 hours = 18000 seconds.
        dt_tue = datetime(2026, 6, 9, 2, 0, tzinfo=timezone.utc)
        seconds = warden.get_seconds_until_next_session(dt_tue)
        self.assertEqual(seconds, 5 * 3600.0)


class TestAsianRangeTracker(unittest.TestCase):
    def test_calculate_range(self):
        # Create a sample DataFrame representing M15 bars
        times = pd.date_range("2026-06-05 00:00:00", "2026-06-05 08:00:00", freq="15min", tz="UTC")
        # Let's set some distinct highs and lows during the Asian session (00:00 to 06:00 UTC)
        # Asian Session covers indices from 00:00 to 06:00.
        highs = [1900 + i for i in range(len(times))] # Highs will increase
        lows = [1850 - i for i in range(len(times))] # Lows will decrease
        
        # Asian session high should be at 06:00 index, which is index 24.
        # Let's verify Asian session high is max during 00:00 to 06:00.
        # Let's build the DataFrame:
        df = pd.DataFrame({
            'high': highs,
            'low': lows
        }, index=times)
        
        tracker = AsianRangeTracker()
        target_date = pd.Timestamp("2026-06-05", tz="UTC")
        tracker.calculate_range(df, target_date)
        
        boundaries = tracker.get_boundaries()
        self.assertIsNotNone(boundaries['asian_high'])
        self.assertIsNotNone(boundaries['asian_low'])
        
        # The max high between 00:00 and 06:00 (inclusive of 06:00) should be at 06:00 (i.e. i = 24)
        # 00:00 to 06:00 contains 25 M15 elements
        expected_high = 1900 + 24
        expected_low = 1850 - 24
        
        self.assertEqual(boundaries['asian_high'], expected_high)
        self.assertEqual(boundaries['asian_low'], expected_low)


class TestMacroContext(unittest.TestCase):
    def test_swing_high_low_detection(self):
        from core.ai_engine import MacroContext
        # Let's make a DataFrame with 7 bars
        # Index 3 (4th bar) is a swing high (higher than index 1, 2, 4, 5) and a swing low (lower than index 1, 2, 4, 5)
        highs = [10.0, 11.0, 12.0, 15.0, 11.5, 11.0, 10.5]
        lows = [9.0, 8.0, 7.0, 4.0, 7.5, 8.0, 8.5]
        
        df = pd.DataFrame({
            'high': highs,
            'low': lows
        })
        
        macro = MacroContext()
        macro.update_structure(df)
        
        self.assertEqual(macro.swing_highs, [15.0])
        self.assertEqual(macro.swing_lows, [4.0])
        
        # Test nearest pools
        pools = macro.get_nearest_liquidity_pools(11.0)
        self.assertEqual(pools['nearest_high'], 15.0)
        self.assertEqual(pools['nearest_low'], 4.0)

        # Test pools when price is above nearest high (so no high is above)
        pools_above = macro.get_nearest_liquidity_pools(16.0)
        self.assertIsNone(pools_above['nearest_high'])
        self.assertEqual(pools_above['nearest_low'], 4.0)


if __name__ == "__main__":
    unittest.main()
