import asyncio
import logging
from config.settings import settings
import MetaTrader5 as mt5

logger = logging.getLogger(__name__)

class MT5Router:
    def __init__(self):
        self.connected = False

    async def connect(self) -> bool:
        """Initialize connection to MetaTrader 5 terminal asynchronously."""
        # mt5 functions are synchronous blocking C-calls, so we wrap them in asyncio.to_thread
        # to prevent blocking the async event loop.
        logger.info("Initializing MetaTrader 5 connection...")
        
        # Build kwargs for mt5.initialize
        kwargs = {}
        if settings.mt5_path:
            kwargs['path'] = settings.mt5_path
        if settings.mt5_login:
            kwargs['login'] = settings.mt5_login
        if settings.mt5_password:
            kwargs['password'] = settings.mt5_password
        if settings.mt5_server:
            kwargs['server'] = settings.mt5_server
            
        success = await asyncio.to_thread(mt5.initialize, **kwargs)
        if not success:
            logger.error(f"MT5 initialize() failed, error code: {mt5.last_error()}")
            self.connected = False
            return False
            
        self.connected = True
        logger.info("MT5 connection successful.")
        
        # Ensure symbol is visible in Market Watch
        symbol_selected = await asyncio.to_thread(mt5.symbol_select, settings.symbol, True)
        if not symbol_selected:
            logger.error(f"Failed to select symbol {settings.symbol}")
            
        return True

    async def disconnect(self):
        if self.connected:
            await asyncio.to_thread(mt5.shutdown)
            self.connected = False
            logger.info("MT5 disconnected.")

    async def get_account_info(self) -> dict:
        """Fetches live account data."""
        if not self.connected:
            return {}
            
        acc_info = await asyncio.to_thread(mt5.account_info)
        if acc_info is None:
            logger.error(f"Failed to get account info: {mt5.last_error()}")
            return {}
            
        return acc_info._asdict()

    async def get_candles(self, timeframe: str, count: int, symbol: str = None) -> list:
        """Fetches OHLCV data."""
        if not self.connected:
            return []
            
        # Map timeframe strings to mt5 constants
        tf_map = {
            "M15": mt5.TIMEFRAME_M15,
            "H4": mt5.TIMEFRAME_H4,
            "D1": mt5.TIMEFRAME_D1
        }
        
        mt5_tf = tf_map.get(timeframe.upper())
        if not mt5_tf:
            logger.error(f"Unsupported timeframe {timeframe}")
            return []
            
        target_symbol = symbol if symbol else settings.symbol
        # Ensure symbol is visible in Market Watch
        await asyncio.to_thread(mt5.symbol_select, target_symbol, True)
        
        rates = await asyncio.to_thread(mt5.copy_rates_from_pos, target_symbol, mt5_tf, 0, count)
        if rates is None:
            logger.error(f"Failed to get rates for {target_symbol}: {mt5.last_error()}")
            return []
            
        return rates

    async def execute_bracket_order(self, order_type: str, lot_size: float, sl: float, tp: float) -> dict:
        """
        Dispatches a single atomic request payload containing Entry, hard SL, and fixed TP.
        Trailing stops are forbidden.
        """
        if not self.connected:
            return {"success": False, "error": "Not connected to MT5"}
            
        mt5_type = mt5.ORDER_TYPE_BUY if order_type.lower() == "buy" else mt5.ORDER_TYPE_SELL
        
        # Get current tick for accurate price info
        tick = await asyncio.to_thread(mt5.symbol_info_tick, settings.symbol)
        if tick is None:
            return {"success": False, "error": "Failed to get symbol tick"}
            
        spread_raw = tick.ask - tick.bid
        if spread_raw > settings.max_spread_raw:
            logger.warning(f"Spread guard triggered! Current spread: {spread_raw} > Max allowed: {settings.max_spread_raw}")
            return {"success": False, "error": f"Spread too high: {spread_raw}"}
            
        price = tick.ask if mt5_type == mt5.ORDER_TYPE_BUY else tick.bid
        
        # Prepare standard order request
        request = {
            "action": mt5.TRADE_ACTION_DEAL,
            "symbol": settings.symbol,
            "volume": float(lot_size),
            "type": mt5_type,
            "price": price,
            "sl": float(sl),
            "tp": float(tp),
            "deviation": 10,
            "magic": 123456,
            "comment": "XAUUSD AI Sweep",
            "type_time": mt5.ORDER_TIME_GTC,
            "type_filling": mt5.ORDER_FILLING_IOC,
        }
        
        # Send atomic bracket order
        logger.info(f"Sending atomic order payload: {request}")
        result = await asyncio.to_thread(mt5.order_send, request)
        
        if result is None or result.retcode != mt5.TRADE_RETCODE_DONE:
            err = mt5.last_error()
            retcode = result.retcode if result else "N/A"
            logger.error(f"Order failed, retcode={retcode}, error={err}")
            return {"success": False, "error": f"Retcode: {retcode}", "raw_result": result}
            
        logger.info(f"Order executed successfully: Ticket #{result.order}")
        return {
            "success": True, 
            "ticket": result.order, 
            "price": result.price, 
            "volume": result.volume
        }

mt5_router = MT5Router()
