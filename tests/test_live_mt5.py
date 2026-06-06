import asyncio
import logging
from config.settings import settings
from execution.mt5_router import mt5_router
import MetaTrader5 as mt5

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("TestLiveMT5")

async def test_live():
    logger.info("Connecting to MT5 terminal...")
    connected = await mt5_router.connect()
    if not connected:
        logger.error("MT5 Connection failed!")
        return
        
    try:
        # 1. Fetch Account Info
        logger.info("Fetching live account details...")
        acc_info = await mt5_router.get_account_info()
        if acc_info:
            logger.info(f"Account Login: {acc_info.get('login')}")
            logger.info(f"Broker/Company: {acc_info.get('company')}")
            logger.info(f"Server: {acc_info.get('server')}")
            logger.info(f"Balance: ${acc_info.get('balance'):,.2f}")
            logger.info(f"Equity: ${acc_info.get('equity'):,.2f}")
            logger.info(f"Leverage: 1:{acc_info.get('leverage')}")
        else:
            logger.error("Failed to retrieve account info.")
            return

        # 2. Fetch Gold Candles (XAUUSDm)
        logger.info(f"Fetching last 5 candles for Gold ({settings.symbol})...")
        gold_candles = await mt5_router.get_candles("M15", 5)
        if len(gold_candles) > 0:
            logger.info(f"Successfully fetched {len(gold_candles)} Gold candles.")
            logger.info(f"Latest Gold Candle Close: {gold_candles[-1]['close']}")
        else:
            logger.error("Failed to fetch Gold candles.")
            
        # 3. Fetch Dollar Index Candles (DXYm)
        logger.info("Fetching last 5 candles for Dollar Index (DXYm)...")
        dxy_candles = await mt5_router.get_candles("M15", 5, symbol="DXYm")
        if len(dxy_candles) > 0:
            logger.info(f"Successfully fetched {len(dxy_candles)} DXYm candles.")
            logger.info(f"Latest DXYm Candle Close: {dxy_candles[-1]['close']}")
        else:
            logger.error("Failed to fetch DXYm candles.")

        # 4. Perform live order execution and close check
        logger.info("Preparing mock bracket order (0.01 standard lot)...")
        tick = await asyncio.to_thread(mt5.symbol_info_tick, settings.symbol)
        if not tick:
            logger.error("Failed to retrieve tick for bracket execution check.")
            return
            
        entry_price = tick.ask
        sl_price = entry_price - 5.00  # SL $5 below entry
        tp_price = entry_price + 15.00 # TP $15 above entry
        
        logger.info(f"Placing Buy order at {entry_price:.2f}. SL: {sl_price:.2f}, TP: {tp_price:.2f}")
        order_res = await mt5_router.execute_bracket_order("BUY", 0.01, sl_price, tp_price)
        
        if order_res.get("success"):
            ticket = order_res["ticket"]
            logger.info(f"Order executed successfully! Ticket ID: {ticket}")
            
            # Close the position immediately to clean up the account
            logger.info(f"Closing position #{ticket}...")
            close_tick = await asyncio.to_thread(mt5.symbol_info_tick, settings.symbol)
            close_price = close_tick.bid
            
            close_request = {
                "action": mt5.TRADE_ACTION_DEAL,
                "symbol": settings.symbol,
                "volume": 0.01,
                "type": mt5.ORDER_TYPE_SELL,
                "position": ticket,
                "price": close_price,
                "deviation": 10,
                "magic": 123456,
                "comment": "Close Test Order",
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
            logger.error(f"Order placement failed: {order_res.get('error')}")

    except Exception as e:
        logger.error(f"Unexpected error during live MT5 test: {e}")
    finally:
        logger.info("Shutting down MT5 session...")
        await mt5_router.disconnect()

if __name__ == "__main__":
    asyncio.run(test_live())
