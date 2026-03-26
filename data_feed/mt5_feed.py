try:
    import MetaTrader5 as mt5
except ImportError:
    mt5 = None
import pandas as pd
from datetime import datetime
from typing import Dict, Optional
from .base import BaseDataProvider
from utils.logger import logger

class MT5DataProvider(BaseDataProvider):
    """
    Connects to MetaTrader 5 terminal for live or demo trading.
    """
    TIMEFRAMES = {
        "1m": mt5.TIMEFRAME_M1,
        "5m": mt5.TIMEFRAME_M5,
        "15m": mt5.TIMEFRAME_M15,
        "1h": mt5.TIMEFRAME_H1,
        "4h": mt5.TIMEFRAME_H4,
        "1d": mt5.TIMEFRAME_D1
    }

    def __init__(self, login: int, password: str, server: str, symbol_suffix: str = ""):
        self.login = login
        self.password = password
        self.server = server
        self.symbol_suffix = symbol_suffix
        self.is_connected = False

    def connect(self) -> bool:
        """
        Initializes and logs into the MT5 terminal.
        """
        if mt5 is None:
            logger.error("MetaTrader5 library is not installed or not supported on this OS (macOS/Linux).")
            return False
            
        if not mt5.initialize(login=self.login, password=self.password, server=self.server):
            logger.error(f"MT5 initialization failed: {mt5.last_error()}")
            return False
        
        self.is_connected = True
        logger.info(f"Connected to MT5 Server: {self.server} (Login: {self.login})")
        return True

    def _format_symbol(self, symbol: str) -> str:
        """
        Handles broker-specific symbol suffixes (e.g., XAUUSDm, XAUUSD.).
        """
        return f"{symbol.strip()}{self.symbol_suffix}"

    def get_account_info(self) -> Dict:
        """
        Retrieves current account balance and equity.
        """
        if not self.is_connected:
            return {}
            
        acc = mt5.account_info()
        if acc is None:
            return {}
            
        return {
            "balance": acc.balance,
            "equity": acc.equity,
            "currency": acc.currency,
            "leverage": acc.leverage
        }

    def get_latest_candles(self, symbol: str, timeframe: str, count: int) -> pd.DataFrame:
        """
        Fetches 'count' recent candles for the given symbol and timeframe.
        """
        if not self.is_connected:
            return pd.DataFrame()

        fmt_symbol = self._format_symbol(symbol)
        mt5_tf = self.TIMEFRAMES.get(timeframe)
        if mt5_tf is None:
            logger.error(f"Unsupported timeframe: {timeframe}")
            return pd.DataFrame()

        rates = mt5.copy_rates_from_pos(fmt_symbol, mt5_tf, 0, count)
        if rates is None or len(rates) == 0:
            logger.warning(f"Failed to fetch {timeframe} rates for {fmt_symbol}")
            return pd.DataFrame()

        df = pd.DataFrame(rates)
        df['time'] = pd.to_datetime(df['time'], unit='s')
        df.set_index('time', inplace=True)
        
        return df[['open', 'high', 'low', 'close', 'tick_volume', 'spread']]

    def execute_order(self, symbol: str, order_type: str, volume: float, sl: float, tp: float) -> Dict:
        """
        Sends a market order to the MT5 terminal.
        """
        if not self.is_connected:
            return {"status": "ERROR", "reason": "Not connected to MT5"}

        action = mt5.TRADE_ACTION_DEAL
        type_mt5 = mt5.ORDER_TYPE_BUY if order_type.upper() == "BUY" else mt5.ORDER_TYPE_SELL
        
        price = mt5.symbol_info_tick(symbol).ask if order_type.upper() == "BUY" else mt5.symbol_info_tick(symbol).bid
        
        request = {
            "action": action,
            "symbol": symbol,
            "volume": volume,
            "type": type_mt5,
            "price": price,
            "sl": float(sl),
            "tp": float(tp),
            "deviation": 20,
            "magic": 123456,
            "comment": "ScalpBot Trade",
            "type_time": mt5.ORDER_TIME_GTC,
            "type_filling": mt5.ORDER_FILLING_IOC,
        }

        result = mt5.order_send(request)
        if result.retcode != mt5.TRADE_RETCODE_DONE:
            logger.error(f"Order failed: {result.retcode} | {mt5.last_error()}")
            return {"status": "ERROR", "reason": f"MT5 Error: {result.retcode}"}

        logger.info(f"Order executed successfully: {order_type} {volume} lots at {result.price}")
        return {"status": "SUCCESS", "deal_id": result.deal, "price": result.price}

    def shutdown(self):
        """
        Safely shuts down the MT5 connection.
        """
        mt5.shutdown()
        self.is_connected = False
        logger.info("MT5 connection closed.")
