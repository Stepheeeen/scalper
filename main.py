import time
import schedule
from datetime import datetime
from config import config
from data_feed.mt5_adapter import MT5Adapter
from data_feed.market_data import MarketDataManager
from engine.setups import SetupEngine
from engine.confirmation import ConfirmationEngine
from engine.trade_manager import TradeManager
from risk.manager import RiskManager
from utils.telegram import TelegramNotifier
from utils.ai_assistant import AIAssistant
from utils.database import DatabaseManager
from utils.logger import logger

class NakedPriceActionBot:
    def __init__(self):
        self.config = config
        self.broker = MT5Adapter(config)
        self.market_data = MarketDataManager()
        self.setup_engine = SetupEngine()
        self.risk_manager = RiskManager(config)
        self.confirmation = ConfirmationEngine(config)
        self.trade_manager = TradeManager(self.broker, self.risk_manager)
        self.notifier = TelegramNotifier(config.telegram_token, config.telegram_chat_id)
        self.ai = AIAssistant(config.ai.api_key)
        self.db = DatabaseManager()
        
        self.is_running = False

    def start(self):
        """Initializes and starts the bot."""
        if not self.broker.connect():
            self.notifier.send_alert("ERROR", "Failed to connect to MT5.")
            return

        self.is_running = True
        logger.info("Naked Price Action Bot Started.")
        self.notifier.send_alert("SUCCESS", "Bot Online: Mode 1 (Paper Trading / Rule Engine Only)")
        
        # Schedule Daily Open Summary
        schedule.every().day.at("06:45").do(self.send_daily_outlook)
        
        self.run_loop()

    def send_daily_outlook(self):
        """Generates and sends the daily market overview via Telegram."""
        # Fetch HTF data for bias
        df_htf = self.broker.get_candles(
            config.strategy.symbol + config.strategy.symbol_suffix, 
            config.strategy.htf_timeframe, 100
        )
        df_d1 = self.broker.get_candles(
            config.strategy.symbol + config.strategy.symbol_suffix, "D1", 5
        )
        
        levels = self.market_data.calculate_levels(df_htf, df_d1)
        bias_info = self.setup_engine.structure.calculate_bias(df_htf)
        
        summary_data = {
            "date": datetime.now().strftime("%Y-%m-%d"),
            "symbol": config.strategy.symbol,
            "bias": bias_info['bias'].value,
            "pdh": levels.get('pdh'),
            "pdl": levels.get('pdl'),
            "sessions": "London: 07:00-10:00 | NY: 12:00-15:00 UTC",
            "scenarios": f"Looking for {bias_info['bias'].value} setups at prior structural levels."
        }
        self.notifier.send_daily_open(summary_data)

    def run_loop(self):
        """Main execution loop."""
        while self.is_running:
            try:
                now_utc = datetime.utcnow()
                session_status = self.market_data.get_session_status(now_utc)
                
                # Update account and risk stats
                acc = self.broker.get_account_info()
                if acc:
                    self.db.log_equity(acc['balance'], acc['equity'])
                    # Daily stats check
                    if not self.risk_manager.enforce_daily_limits(acc['balance'], acc['equity']):
                        time.sleep(60)
                        continue

                # 1. Manage Active Positions
                tick = {"bid": mt5.symbol_info_tick(config.strategy.symbol + config.strategy.symbol_suffix).bid,
                        "ask": mt5.symbol_info_tick(config.strategy.symbol + config.strategy.symbol_suffix).ask}
                self.trade_manager.manage_lifecycle(tick)

                # 2. Scanning Block (Only during sessions)
                if session_status['is_market_open']:
                    symbol = config.strategy.symbol + config.strategy.symbol_suffix
                    df_entry = self.broker.get_candles(symbol, config.strategy.entry_timeframe, 100)
                    df_htf = self.broker.get_candles(symbol, config.strategy.htf_timeframe, 100)
                    df_d1 = self.broker.get_candles(symbol, "D1", 5)
                    
                    levels = self.market_data.calculate_levels(df_htf, df_d1)
                    market_context = {
                        "is_market_open": True,
                        "bias": self.setup_engine.structure.calculate_bias(df_htf)['bias'].value,
                        **levels
                    }

                    setups = self.setup_engine.scan({"entry": df_entry, "htf": df_htf}, levels)
                    
                    for setup in setups:
                        # Validation & Confirmation
                        valid_setup = self.confirmation.validate_setup(setup, market_context)
                        
                        if valid_setup:
                            self.handle_execution(valid_setup, acc['balance'])
                        elif config.log_skipped_setups:
                            # Log skipped setup for auditing
                            ai_explanation = self.ai.explain_skipped_setup(setup, "Low confluence or poor RR")
                            self.db.log_skipped_setup({
                                "symbol": config.strategy.symbol,
                                "strategy": setup['type'],
                                "reason": ai_explanation,
                                "score": setup.get('confluence_score', 0),
                                "context": str(market_context)
                            })

                schedule.run_pending()

            except Exception as e:
                logger.error(f"Main loop error: {e}")
                time.sleep(30)
            
            time.sleep(10)

    def handle_execution(self, setup: Dict, balance: float):
        """Processes a validated setup and executes if possible."""
        # Calculate Risk and Position
        lots = self.risk_manager.calculate_position_size(balance, setup['entry_price'], setup['stop_loss'])
        
        # AI Commentary
        commentary = self.ai.generate_setup_commentary(setup, {"bias": setup['bias_alignment']})
        
        res = self.broker.execute_order(
            config.strategy.symbol + config.strategy.symbol_suffix,
            setup['side'], lots, setup['stop_loss'], setup['tp']
        )
        
        if res:
            trade_data = {
                "strategy": setup['type'],
                "side": setup['side'],
                "entry": setup['entry_price'],
                "sl": setup['stop_loss'],
                "tp": setup['tp'],
                "rr": setup['rr'],
                "risk_percent": config.risk.risk_per_trade_percent,
                "rationale": commentary
            }
            self.notifier.send_entry_alert(trade_data)
            self.trade_manager.add_position(res['ticket'], setup['side'], setup['entry_price'], setup['stop_loss'], setup['tp'], lots)

    def stop(self):
        self.is_running = False
        self.broker.disconnect()

if __name__ == "__main__":
    import MetaTrader5 as mt5
    bot = NakedPriceActionBot()
    bot.start()
