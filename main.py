import time
import pandas as pd
from config import config
from data_feed.base import MockDataProvider
from engine.strategy import StrategyEngine
from risk.manager import RiskManager
from utils.logger import logger
from utils.telegram import TelegramNotifier
from utils.database import DatabaseManager
from utils.charting import generate_equity_chart

class ScalpBot:
    def __init__(self):
        self.config = config
        
        # Select Data Provider
        if config.provider == "mt5":
            from data_feed.mt5_feed import MT5DataProvider
            self.data_provider = MT5DataProvider(
                login=config.mt5_login, 
                password=config.mt5_password, 
                server=config.mt5_server,
                symbol_suffix=config.strategy.symbol_suffix
            )
        else:
            self.data_provider = MockDataProvider()
            
        self.strategy = StrategyEngine(config)
        self.risk_manager = RiskManager(config)
        self.notifier = TelegramNotifier(config.telegram_token, config.telegram_chat_id)
        self.db = DatabaseManager()
        self.is_running = False
        self.tg_offset = None
        self.last_equity_log = 0 

    def start(self):
        logger.info("[bold green]Starting XAUUSD Scalp Bot...[/bold green]")
        
        if not self.data_provider.connect():
            error_msg = "Failed to connect to data provider. Bot will not start."
            logger.error(error_msg)
            self.notifier.send_alert("ERROR", error_msg)
            return

        # Pre-Flight Account Check
        if self.config.provider == "mt5":
            acc = self.data_provider.get_account_info()
            if acc:
                balance_str = f"{acc['balance']} {acc['currency']}"
                logger.info(f"Account Info: {balance_str} | Leverage: 1:{acc['leverage']}")
                self.notifier.send_message(f"✅ *MT5 Connected*\n💰 *Balance:* `{balance_str}`\n📈 *Equity:* `{acc['equity']}`")
            else:
                logger.warning("Could not retrieve MT5 account info.")

        self.notifier.send_message(f"🚀 *XAUUSD Scalp Bot Started* ({self.config.provider.upper()})")
        self.is_running = True
        self.run_loop()

    def handle_commands(self):
        """
        Polls Telegram for commands and executes them.
        """
        try:
            updates = self.notifier.get_updates(offset=self.tg_offset)
            for update in updates:
                self.tg_offset = update['update_id'] + 1
                if 'message' in update and 'text' in update['message']:
                    text = update['message']['text']
                    chat_id = str(update['message']['chat']['id'])
                    
                    if chat_id != self.config.telegram_chat_id:
                        continue 
                        
                    if text == '/status':
                        status = (
                            f"📊 *Bot Status:* {'Running' if self.is_running else 'Stopped'}\n"
                            f"💰 *Provider:* `{self.config.provider}`\n"
                            f"📈 *Risk:* `{self.config.risk.risk_per_trade_percent}%`"
                        )
                        self.notifier.send_message(status)
                    elif text == '/stop':
                        self.notifier.send_message("🛑 *Stopping bot via command...*")
                        self.is_running = False
                    elif text.startswith('/risk'):
                        parts = text.split(' ')
                        if len(parts) > 1:
                            new_risk = float(parts[1])
                            self.config.risk.risk_per_trade_percent = new_risk
                            self.notifier.send_message(f"✅ *Risk updated to:* `{new_risk}%`")
                    elif text == '/report':
                        self.notifier.send_message("📊 *Generating your performance report...*")
                        equity_data = self.db.get_equity_data()
                        chart_path = generate_equity_chart(equity_data)
                        if chart_path:
                            self.notifier.send_photo(chart_path, "📈 *Your Equity Curve*")
                        else:
                            self.notifier.send_message("❌ *Not enough data yet to generate a chart.*")
        except Exception as e:
            logger.debug(f"Command handling error: {e}")

    def run_loop(self):
        while self.is_running:
            try:
                # 0. Handle Commands
                self.handle_commands()
                if not self.is_running: break

                # 0.5 Log Equity Snapshot (Every ~3 mins)
                now = time.time()
                if now - self.last_equity_log > 180: # 180s = 3 mins
                    acc = self.data_provider.get_account_info() if self.config.provider == "mt5" else None
                    if acc:
                        self.db.log_equity(acc['balance'], acc['equity'])
                    else:
                        self.db.log_equity(1000.0, 1000.0) # Mock
                    self.last_equity_log = now

                # 1. Fetch Data
                data = {
                    '1m': self.data_provider.get_latest_candles(self.config.strategy.symbol, "1m", 300),
                    '5m': self.data_provider.get_latest_candles(self.config.strategy.symbol, "5m", 300),
                    '15m': self.data_provider.get_latest_candles(self.config.strategy.symbol, "15m", 300)
                }

                # Check for fetch errors
                for tf, df in data.items():
                    if df is None or df.empty:
                        warn_msg = f"Failed to fetch {tf} data for {self.config.strategy.symbol}. Retrying next cycle..."
                        logger.warning(warn_msg)
                        self.notifier.send_alert("WARNING", warn_msg)
                        time.sleep(20)
                        continue

                logger.info(f"--- Cycle heartbeat [{time.strftime('%H:%M:%S')}] ---")

                # 2. Risk Check
                if not self.risk_manager.check_global_limits(10000): # Mock balance
                    limit_msg = "Global risk limits reached (Max trades or Drawdown). Skipping cycle."
                    logger.warning(limit_msg)
                    self.notifier.send_alert("WARNING", limit_msg)
                    time.sleep(60)
                    continue

                # 3. Analyze
                signal = self.strategy.analyze(data)
                
                if signal:
                    logger.info(f"[bold cyan]SIGNAL DETECTED:[/bold cyan] {signal['side']} at {signal['entry_price']} | {signal['reason']}")
                    self.notifier.send_signal(
                        signal['symbol'], signal['side'], signal['entry_price'], 
                        signal['stop_loss'], signal['reason']
                    )
                    
                    # 4. Execute (In Paper Mode)
                    if self.config.paper_trading:
                        # lot_size = self.risk_manager.calculate_position_size(...)
                        res = self.data_provider.execute_order(
                            signal['symbol'], signal['side'], 0.1, signal['stop_loss'], 0
                        )
                        logger.info(f"Execution response: {res}")
                        
                        # Log to DB
                        self.db.log_signal(
                            signal['symbol'], signal['side'], signal['reason'], signal['entry_price']
                        )

                time.sleep(10) # 10s polling for scalping
                
            except KeyboardInterrupt:
                logger.info("Shutting down bot...")
                self.notifier.send_message("🛑 *XAUUSD Scalp Bot Shutting Down*")
                self.is_running = False
            except Exception as e:
                logger.error(f"Error in main loop: {e}", exc_info=True)
                time.sleep(10)

if __name__ == "__main__":
    bot = ScalpBot()
    bot.start()
