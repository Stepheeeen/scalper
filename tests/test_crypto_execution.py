import asyncio
import logging
import MetaTrader5 as mt5
from config.settings import settings
from execution.mt5_router import mt5_router

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("TestCryptoExecution")

async def test_crypto():
    logger.info("Connecting to MT5 terminal...")
    connected = await mt5_router.connect()
    if not connected:
        logger.error("MT5 Connection failed!")
        return
        
    symbol = "BTCUSDm"
    try:
        # Enable the symbol
        await asyncio.to_thread(mt5.symbol_select, symbol, True)
        
        # 1. Fetch Account Info
        logger.info("Fetching live account details...")
        acc_info = await mt5_router.get_account_info()
        if acc_info:
            logger.info(f"Balance: ${acc_info.get('balance'):,.2f}")
            logger.info(f"Equity: ${acc_info.get('equity'):,.2f}")
        else:
            logger.error("Failed to retrieve account info.")
            return

        # 2. Get symbol info
        logger.info(f"Retrieving symbol info for {symbol}...")
        sym_info = await asyncio.to_thread(mt5.symbol_info, symbol)
        if not sym_info:
            logger.error(f"Failed to get symbol info for {symbol}")
            return
            
        tick = await asyncio.to_thread(mt5.symbol_info_tick, symbol)
        if not tick:
            logger.error("Failed to get tick info.")
            return
            
        logger.info(f"Bid: {tick.bid}, Ask: {tick.ask}, Spread: {tick.ask - tick.bid:.2f}")

        # 3. Perform live order execution and close check
        logger.info(f"Preparing bracket order for {symbol} (0.01 standard lot)...")
        
        entry_price = tick.ask
        # Set a wide stop loss/take profit so we don't immediately hit it, e.g. SL $100 below, TP $200 above
        sl_price = entry_price - 100.00
        tp_price = entry_price + 200.00
        
        logger.info(f"Placing Buy order at {entry_price:.2f}. SL: {sl_price:.2f}, TP: {tp_price:.2f}")
        
        request = {
            "action": mt5.TRADE_ACTION_DEAL,
            "symbol": symbol,
            "volume": 0.01,
            "type": mt5.ORDER_TYPE_BUY,
            "price": entry_price,
            "sl": sl_price,
            "tp": tp_price,
            "deviation": 10,
            "magic": 123456,
            "comment": "BTCUSD Test Order",
            "type_time": mt5.ORDER_TIME_GTC,
            "type_filling": mt5.ORDER_FILLING_IOC,
        }
        
        logger.info(f"Sending order request: {request}")
        result = await asyncio.to_thread(mt5.order_send, request)
        
        if result is None:
            logger.error(f"Order send returned None! Last error: {mt5.last_error()}")
            return
            
        logger.info(f"Order result code: {result.retcode}")
        if result.retcode == mt5.TRADE_RETCODE_DONE:
            ticket = result.order
            logger.info(f"Order executed successfully! Ticket ID: {ticket}")
            
            # Close the position immediately
            logger.info(f"Closing position #{ticket}...")
            close_tick = await asyncio.to_thread(mt5.symbol_info_tick, symbol)
            close_price = close_tick.bid
            
            close_request = {
                "action": mt5.TRADE_ACTION_DEAL,
                "symbol": symbol,
                "volume": 0.01,
                "type": mt5.ORDER_TYPE_SELL,
                "position": ticket,
                "price": close_price,
                "deviation": 10,
                "magic": 123456,
                "comment": "Close BTCUSD Test Order",
                "type_time": mt5.ORDER_TIME_GTC,
                "type_filling": mt5.ORDER_FILLING_IOC,
            }
            
            close_res = await asyncio.to_thread(mt5.order_send, close_request)
            if close_res and close_res.retcode == mt5.TRADE_RETCODE_DONE:
                logger.info(f"Position #{ticket} closed successfully at {close_price:.2f}!")
            else:
                ret = close_res.retcode if close_res else "None"
                logger.error(f"Failed to close position: retcode={ret}, error={mt5.last_error()}")
        else:
            logger.error(f"Order placement failed: retcode={result.retcode}, comment={result.comment}, error={mt5.last_error()}")

    except Exception as e:
        logger.error(f"Unexpected error: {e}")
    finally:
        logger.info("Shutting down MT5 session...")
        await mt5_router.disconnect()

if __name__ == "__main__":
    asyncio.run(test_crypto())
