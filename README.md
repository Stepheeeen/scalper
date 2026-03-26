# XAUUSD Scalp Trading Bot

Institutional-grade scalping bot for Gold (XAUUSD) based on Market Structure (SMC) and Liquidity.

## Strategy: SMC Scalp
- **HTF Bias**: Trend determination on 15m and 5m using EMA and structure.
- **Liquidity**: Identifies Asian range and session highs/lows.
- **Execution**: 
  1. Wait for liquidity sweep on 1m.
  2. Confirm with displacement candle.
  3. Enter on Fair Value Gap (FVG) retracement.
- **Risk**: Position sizing based on % risk per trade with daily drawdown kill-switches.

## Quick Start
1. Install dependencies: `pip install -r requirements.txt`
2. Configure `config.py`.
3. Run: `python main.py`

## Architecture
- `engine/`: Core logic for structure, liquidity, and strategy.
- `data_feed/`: Modular data providers (MT5, Mock).
- `risk/`: Position sizing and drawdown management.
- `monitoring/`: Logging and notifications.
