import asyncio
import logging
import pandas as pd
import numpy as np
from datetime import datetime, timezone
import uvicorn
from multiprocessing import Process

from config.settings import settings
from config.database import db
from core.discipline import warden
from core.ai_engine import ai_engine
from core.sweep_sensor import sweep_sensor
from core.risk_manager import risk_manager
from core.notifier import notifier
from execution.mt5_router import mt5_router

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
    handlers=[
        logging.FileHandler("system.log", encoding="utf-8"),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger("SystemCore")

async def system_log(message: str, level: str = "INFO", notify: bool = False):
    """Helper to log locally and to MongoDB."""
    if level == "INFO":
        logger.info(message)
    elif level == "WARNING":
        logger.warning(message)
    elif level == "ERROR":
        logger.error(message)
    elif level == "CRITICAL":
        logger.critical(message)
        
    if db.system_logs is not None:
        await db.system_logs.insert_one({
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "level": level,
            "message": message
        })
        
    if notify:
        prefix = "🟢" if level == "INFO" else "🟡" if level == "WARNING" else "🔴"
        await notifier.send_message(f"{prefix} <b>XAUUSD System</b>\n{message}")

def run_dashboard():
    """Runs the FastAPI dashboard on a separate process."""
    uvicorn.run("dashboard.api:app", host="0.0.0.0", port=8000, log_level="info")

async def trading_loop():
    """The core asynchronous trading loop."""
    await system_log("Trading loop starting...", "INFO")
    
    while True:
        try:
            # Weekend Market Close Check
            if warden.is_market_closed():
                sleep_seconds = warden.get_seconds_until_market_open()
                hours = sleep_seconds / 3600.0
                await system_log(f"Market is closed for the weekend. Sleeping for {hours:.2f} hours.", "INFO")
                await asyncio.sleep(sleep_seconds)
                continue

            # Weekday Session Close Check (if not bypassed)
            if not settings.bypass_session_check and not warden.is_valid_trading_session():
                sleep_seconds = warden.get_seconds_until_next_session()
                hours = sleep_seconds / 3600.0
                await system_log(f"Outside valid trading sessions (London/NY). Sleeping for {hours:.2f} hours.", "INFO")
                await asyncio.sleep(sleep_seconds)
                continue

            # 1. Gatekeeper Check
            is_allowed, reason = await warden.is_execution_allowed()
            if not is_allowed:
                await system_log(f"Execution blocked: {reason}", "INFO")
                await asyncio.sleep(60) # Sleep and check again in a minute
                continue
                
            if risk_manager.is_auto_killed:
                await system_log("System is frozen due to Daily Drawdown Auto-Kill.", "CRITICAL", notify=True)
                await asyncio.sleep(300)
                continue

            # 2. Fetch Market Data
            raw_4h = await mt5_router.get_candles("H4", 100)
            raw_15m = await mt5_router.get_candles("M15", 100)
            
            if raw_4h is None or len(raw_4h) == 0 or raw_15m is None or len(raw_15m) == 0:
                await system_log("Failed to fetch MT5 market data.", "WARNING")
                await asyncio.sleep(10)
                continue
                
            # Convert to Pandas DataFrames
            df_4h = pd.DataFrame(raw_4h)
            df_4h['time'] = pd.to_datetime(df_4h['time'], unit='s')
            df_4h.set_index('time', inplace=True)
            if 'tick_volume' in df_4h.columns:
                df_4h.rename(columns={'tick_volume': 'volume'}, inplace=True)
            
            df_15m = pd.DataFrame(raw_15m)
            df_15m['time'] = pd.to_datetime(df_15m['time'], unit='s')
            df_15m.set_index('time', inplace=True)
            if 'tick_volume' in df_15m.columns:
                df_15m.rename(columns={'tick_volume': 'volume'}, inplace=True)
            
            # Calculate Indicators for AI Filter
            high_low = df_15m['high'] - df_15m['low']
            high_cp = np.abs(df_15m['high'] - df_15m['close'].shift(1))
            low_cp = np.abs(df_15m['low'] - df_15m['close'].shift(1))
            tr = pd.concat([high_low, high_cp, low_cp], axis=1).max(axis=1)
            df_15m['atr'] = tr.rolling(window=14).mean()
            
            delta = df_15m['close'].diff()
            gain = (delta.where(delta > 0, 0)).rolling(window=14).mean()
            loss = (-delta.where(delta < 0, 0)).rolling(window=14).mean()
            rs = gain / (loss + 1e-10)
            df_15m['rsi'] = 100 - (100 / (1 + rs))
            
            vol_sma = df_15m['volume'].rolling(20).mean()
            df_15m['volume_ratio'] = df_15m['volume'] / (vol_sma + 1e-10)
            
            # 3. Time-frame Architecture & Feature Extraction
            current_date = pd.Timestamp(datetime.now(timezone.utc))
            ai_engine.macro.update_structure(df_4h)
            ai_engine.asian_range.calculate_range(df_15m, current_date)
            
            boundaries = []
            asian_b = ai_engine.asian_range.get_boundaries()
            if asian_b['asian_high']: boundaries.append(asian_b['asian_high'])
            if asian_b['asian_low']: boundaries.append(asian_b['asian_low'])
            
            # We check the most recently *closed* 15m candle (index -2 usually, if -1 is active)
            # Assuming MT5 returns active candle at -1
            closed_candle = df_15m.iloc[-2] 
            
            # Fetch macro structure swing points and add to boundaries
            pools = ai_engine.macro.get_nearest_liquidity_pools(closed_candle['close'])
            if pools.get('nearest_high'):
                boundaries.append(pools['nearest_high'])
            if pools.get('nearest_low'):
                boundaries.append(pools['nearest_low'])
                
            await system_log(f"Active boundaries for sweep check: {boundaries}", "INFO")
            
            # 4. Trigger Check
            signal = sweep_sensor.check_for_sweep(closed_candle, boundaries)
            
            if signal:
                await system_log(f"Raw Signal Detected: {signal['type']} at level {signal['level_swept']}", "INFO")
                
                # 5. AI Filter
                features = {
                    "atr": float(closed_candle.get("atr", 0.0)),
                    "rsi": float(closed_candle.get("rsi", 0.0)),
                    "volume_ratio": float(closed_candle.get("volume_ratio", 1.0)),
                    "wick_ratio": float(signal.get("wick_ratio", 0.5))
                }
                
                if ai_engine.filter.is_signal_approved(features):
                    await system_log("Signal APPROVED by AI Filter.", "INFO")
                    
                    # 6. Risk Management & Execution
                    acc_info = await mt5_router.get_account_info()
                    if not acc_info:
                        await system_log("Could not retrieve account info for execution.", "ERROR")
                        continue
                        
                    balance = acc_info.get('balance', 0.0)
                    equity = acc_info.get('equity', 0.0)
                    
                    risk_manager.set_daily_starting_balance(balance)
                    
                    if risk_manager.check_daily_drawdown(equity):
                        continue # Auto-kill triggered
                        
                    lot_size, adjusted_sl = risk_manager.calculate_lot_size(balance, signal['entry'], signal['stop_loss'])
                    
                    if lot_size <= 0:
                        await system_log("Calculated lot size is invalid.", "ERROR")
                        continue
                        
                    tp_price = risk_manager.calculate_take_profit(signal['entry'], adjusted_sl)
                    
                    # Determine Buy or Sell
                    side = "BUY" if signal['type'] == "bullish_sweep" else "SELL"
                    
                    await system_log(f"Executing {side} {lot_size} lots. SL: {adjusted_sl}, TP: {tp_price}", "INFO", notify=True)
                    
                    if not settings.paper_trading:
                        result = await mt5_router.execute_bracket_order(side, lot_size, adjusted_sl, tp_price)
                        
                        if result['success']:
                            # Log trade to DB
                            trade_doc = {
                                "date": datetime.now(timezone.utc).strftime("%Y-%m-%d"),
                                "timestamp": datetime.now(timezone.utc).isoformat(),
                                "ticket": result['ticket'],
                                "type": side,
                                "entry": result['price'],
                                "sl": adjusted_sl,
                                "tp": tp_price,
                                "volume": result['volume']
                            }
                            await db.trades.insert_one(trade_doc)
                            await system_log(f"Trade successfully logged to MongoDB. Ticket: {result['ticket']}", "INFO", notify=True)
                        else:
                            await system_log(f"Order failed: {result.get('error')}", "ERROR", notify=True)
                    else:
                        await system_log("PAPER TRADING: Execution skipped.", "INFO", notify=True)

                else:
                    await system_log("Signal REJECTED by AI Filter.", "INFO")
            else:
                await system_log("No liquidity sweep detected on the last closed candle.", "INFO")
            
            # Sleep until next potential candle check
            await asyncio.sleep(60)

        except Exception as e:
            await system_log(f"Unexpected error in trading loop: {str(e)}", "ERROR")
            await asyncio.sleep(30)

async def main():
    await system_log("Starting XAUUSD Algo System...", "INFO", notify=True)
    
    # Init DB
    await db.connect()
    
    # Load AI Filter model
    if settings.xgboost_model_path:
        ai_engine.filter.load_model(settings.xgboost_model_path)
    
    # Init MT5
    connected = await mt5_router.connect()
    if not connected:
        await system_log("Failed to connect to MT5. Exiting...", "CRITICAL", notify=True)
        return
        
    # Start Dashboard on a separate process
    dashboard_process = Process(target=run_dashboard)
    dashboard_process.start()
    
    try:
        await trading_loop()
    except asyncio.CancelledError:
        pass
    finally:
        await mt5_router.disconnect()
        await db.disconnect()
        dashboard_process.terminate()
        await system_log("System Shutdown.", "INFO")

if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        logger.info("Keyboard interrupt received. Shutting down.")
