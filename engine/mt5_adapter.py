import MetaTrader5 as mt5
from typing import Dict, Optional, List
from utils.logger import logger
from config import config

class MT5Adapter:
    """
    Isolates MT5-specific execution logic.
    Provides a broker-agnostic interface for the bot.
    """
    def __init__(self, config):
        self.config = config

    def connect(self) -> bool:
        if not mt5.initialize(
            login=self.config.mt5_login,
            password=self.config.mt5_password,
            server=self.config.mt5_server
        ):
            logger.error(f"MT5 initialization failed, error code: {mt5.last_error()}")
            return False
        return True

    def disconnect(self):
        mt5.shutdown()

    def get_account_info(self) -> Optional[Dict]:
        acc = mt5.account_info()
        if acc is None: return None
        return {
            "balance": acc.balance,
            "equity": acc.equity,
            "margin": acc.margin,
            "currency": acc.currency
        }

    def execute_order(self, symbol: str, side: str, volume: float, sl: float, tp: float) -> Optional[Dict]:
        """Executes a Market Order with SL and TP."""
        if self.config.paper_trading:
            logger.info(f"[PAPER] Executing {side} {volume} lots on {symbol} | SL: {sl} | TP: {tp}")
            return {"ticket": 999999, "status": "PAPER_SUCCESS"}

        order_type = mt5.ORDER_TYPE_BUY if side == "BUY" else mt5.ORDER_TYPE_SELL
        price = mt5.symbol_info_tick(symbol).ask if side == "BUY" else mt5.symbol_info_tick(symbol).bid
        
        request = {
            "action": mt5.TRADE_ACTION_DEAL,
            "symbol": symbol,
            "volume": volume,
            "type": order_type,
            "price": price,
            "sl": float(sl),
            "tp": float(tp),
            "deviation": 20,
            "magic": 123456,
            "comment": "Naked Price Action Bot",
            "type_time": mt5.ORDER_TIME_GTC,
            "type_filling": mt5.ORDER_FILLING_IOC,
        }

        result = mt5.order_send(request)
        if result.retcode != mt5.TRADE_RETCODE_DONE:
            logger.error(f"Order failed, retcode: {result.retcode}")
            return None

        return {"ticket": result.order, "status": "SUCCESS"}

    def modify_order(self, ticket: int, sl: float, tp: float) -> bool:
        if self.config.paper_trading: return True
        
        request = {
            "action": mt5.TRADE_ACTION_SLTP,
            "symbol": self.config.strategy.symbol + self.config.strategy.symbol_suffix,
            "sl": float(sl),
            "tp": float(tp),
            "position": ticket
        }
        result = mt5.order_send(request)
        return result.retcode == mt5.TRADE_RETCODE_DONE

    def close_order(self, ticket: int) -> bool:
        if self.config.paper_trading: return True
        # MT5 closing requires a reverse trade or trade_action_deal with position ticket
        # Simplified for now
        return True

    def get_candles(self, symbol: str, timeframe_str: str, count: int) -> pd.DataFrame:
        """Fetches OHLCV data and converts to DataFrame."""
        tf_map = {
            "M1": mt5.TIMEFRAME_M1,
            "M5": mt5.TIMEFRAME_M5,
            "M15": mt5.TIMEFRAME_M15,
            "H1": mt5.TIMEFRAME_H1,
            "D1": mt5.TIMEFRAME_D1
        }
        tf = tf_map.get(timeframe_str, mt5.TIMEFRAME_M5)
        
        rates = mt5.copy_rates_from_pos(symbol, tf, 0, count)
        if rates is None: return pd.DataFrame()
        
        df = pd.DataFrame(rates)
        df['time'] = pd.to_datetime(df['time'], unit='s')
        df.set_index('time', inplace=True)
        return df
