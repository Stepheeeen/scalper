import pandas as pd
from utils.logger import logger
from engine.strategy import StrategyEngine
from risk.manager import RiskManager

class BacktestEngine:
    def __init__(self, config, data_provider):
        self.config = config
        self.data_provider = data_provider
        self.strategy = StrategyEngine(config)
        self.risk_manager = RiskManager(config)
        self.balance = 10000.0
        self.trades = []
        self.equity_curve = []

    def run(self):
        logger.info("Starting Backtest...")
        while self.data_provider.advance():
            data = {
                '1m': self.data_provider.get_latest_candles("XAUUSD", "1m", 300),
                '5m': self.data_provider.get_latest_candles("XAUUSD", "5m", 300),
                '15m': self.data_provider.get_latest_candles("XAUUSD", "15m", 300)
            }
            
            if data['1m'].empty: continue

            # 1. Manage existing trades (SL, TP, BE, Reverse Cross)
            self.manage_trades(data['1m'])

            # 2. Analyze for new signal
            signal = self.strategy.analyze(data)
            if signal:
                # Only one trade at a time for this strategy
                if not any(t['status'] == 'OPEN' for t in self.trades):
                    self.execute_trade(signal, data['1m'].iloc[-1])

            self.equity_curve.append(self.balance)

        self.report()

    def execute_trade(self, signal, current_candle):
        lots = self.risk_manager.calculate_position_size(
            self.balance, signal['entry_price'], signal['stop_loss']
        )
        
        if lots > 0:
            sl_dist = abs(signal['entry_price'] - signal['stop_loss'])
            tp = signal['entry_price'] + (sl_dist * self.config.risk.min_rr_ratio) if signal['side'] == "BUY" else signal['entry_price'] - (sl_dist * self.config.risk.min_rr_ratio)
            
            trade = {
                'entry_time': current_candle.name,
                'side': signal['side'],
                'entry_price': signal['entry_price'],
                'stop_loss': signal['stop_loss'],
                'original_sl': signal['stop_loss'],
                'tp': tp,
                'lots': lots,
                'status': 'OPEN',
                'is_be': False
            }
            self.trades.append(trade)
            logger.info(f"BACKTEST: Opened {trade['side']} at {trade['entry_price']}")

    def manage_trades(self, df_1m):
        candle = df_1m.iloc[-1]
        for trade in self.trades:
            if trade['status'] == 'OPEN':
                # Prevent Managing on the same candle it was opened
                if candle.name == trade['entry_time']:
                    continue
                
                # A. Check SL/TP
                if trade['side'] == 'BUY':
                    if candle['low'] <= trade['stop_loss']:
                        self.close_trade(trade, trade['stop_loss'], candle.name, "SL")
                        continue
                    if candle['high'] >= trade['tp']:
                        self.close_trade(trade, trade['tp'], candle.name, "TP")
                        continue
                else: # SELL
                    if candle['high'] >= trade['stop_loss']:
                        self.close_trade(trade, trade['stop_loss'], candle.name, "SL")
                        continue
                    if candle['low'] <= trade['tp']:
                        self.close_trade(trade, trade['tp'], candle.name, "TP")
                        continue

                # B. Check for Break-Even Trigger
                if not trade['is_be'] and self.risk_manager.should_move_to_be(trade['entry_price'], candle['close'], trade['side']):
                    trade['stop_loss'] = trade['entry_price']
                    trade['is_be'] = True
                    logger.debug(f"BACKTEST: Trade moved to BE at {candle.name}")

                # C. Check for Reverse Crossover Exit
                if self.strategy.check_exit_condition(df_1m, trade['side']):
                    self.close_trade(trade, candle['close'], candle.name, "Reverse Cross")

    def close_trade(self, trade, price, time, reason):
        # 1 lot = 100oz. PnL = (price_diff) * 100 * lots
        pnl = (price - trade['entry_price']) * 100 * trade['lots'] if trade['side'] == 'BUY' else (trade['entry_price'] - price) * 100 * trade['lots']
        self.balance += pnl
        trade['status'] = 'CLOSED'
        trade['exit_price'] = price
        trade['exit_time'] = time
        trade['pnl'] = pnl
        logger.info(f"BACKTEST: Closed {reason} at {price} | PnL: ${pnl:.2f}")

    def report(self):
        df_trades = pd.DataFrame([t for t in self.trades if t['status'] == 'CLOSED'])
        if df_trades.empty:
            logger.warning("No trades executed during backtest.")
            return

        logger.info("\n" + "="*80)
        logger.info(f"{'Time':<20} | {'Side':<4} | {'Entry':<8} | {'Exit':<8} | {'PnL ($)':<10} | {'Result'}")
        logger.info("-" * 80)
        for _, row in df_trades.iterrows():
            res = "✅" if row['pnl'] > 0 else "❌"
            logger.info(f"{str(row['entry_time']):<20} | {row['side']:<4} | {row['entry_price']:<8.2f} | {row['exit_price']:<8.2f} | {row['pnl']:<10.2f} | {res}")
        logger.info("="*80 + "\n")

        win_rate = (df_trades['pnl'] > 0).mean() * 100
        total_pnl = df_trades['pnl'].sum()
        
        # Performance Metrics
        gross_profit = df_trades[df_trades['pnl'] > 0]['pnl'].sum()
        gross_loss = abs(df_trades[df_trades['pnl'] < 0]['pnl'].sum())
        profit_factor = gross_profit / gross_loss if gross_loss != 0 else float('inf')
        
        # Max Drawdown
        equity_series = pd.Series(self.equity_curve)
        rolling_max = equity_series.cummax()
        drawdown = (rolling_max - equity_series) / rolling_max * 100
        max_drawdown = drawdown.max()

        logger.info("\n" + "="*30)
        logger.info("   🚀 BACKTEST SUMMARY 🚀   ")
        logger.info("="*30)
        logger.info(f"Total Trades:      {len(df_trades)}")
        logger.info(f"Win Rate:          {win_rate:.1f}%")
        logger.info(f"Profit Factor:     {profit_factor:.2f}")
        logger.info(f"Max Drawdown:      {max_drawdown:.1f}%")
        logger.info(f"Total Net Profit:  ${total_pnl:.2f}")
        logger.info(f"Final Balance:     ${self.balance:.2f}")
        logger.info("="*30 + "\n")
