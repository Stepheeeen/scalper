from pydantic import BaseModel, Field
from typing import List, Optional
from datetime import time

class SessionSettings(BaseModel):
    name: str
    start_time: str  # HH:MM
    end_time: str    # HH:MM
    enabled: bool = True

class RiskSettings(BaseModel):
    risk_per_trade_percent: float = 0.5
    max_daily_drawdown_percent: float = 3.0
    max_trades_per_day: int = 5
    min_rr_ratio: float = 1.5
    move_to_breakeven_atr_multiple: float = 1.0
    partial_tp_atr_multiple: float = 1.5
    partial_tp_percent: float = 50.0

class StrategySettings(BaseModel):
    symbol: str = "XAUUSD"
    timeframes: List[str] = ["1m", "5m", "15m"]
    ema_fast: int = 50
    ema_slow: int = 200
    atr_period: int = 14
    min_atr_threshold: float = 0.5  # Minimum ATR for XAUUSD to consider market 'awake'
    max_spread_pips: float = 30     # Max spread in points/pips for XAUUSD
    momentum_threshold_multiplier: float = 1.5 # Displacement candle vs recent ATR
    symbol_suffix: str = "m"         # Set to "m" for Exness Mini, "." for Pro, etc.

class Config(BaseModel):
    trading_enabled: bool = True
    paper_trading: bool = True
    provider: str = "mt5"  # "mock" or "mt5"
    sessions: List[SessionSettings] = [
        SessionSettings(name="London", start_time="08:00", end_time="12:00"),
        SessionSettings(name="New York", start_time="13:00", end_time="17:00"),
        SessionSettings(name="Overlap", start_time="13:00", end_time="16:00")
    ]
    risk: RiskSettings = RiskSettings()
    strategy: StrategySettings = StrategySettings()
    
    # API Keys & Connection
    mt5_login: Optional[int] = 435013147
    mt5_password: Optional[str] = 'Tally-couture55'
    mt5_server: Optional[str] = 'Exness-MT5Trial9'
    
    telegram_token: Optional[str] = "8313068465:AAGnzQQDYu6aa4wdVx7y0E394wQJPvDNLvE"
    telegram_chat_id: Optional[str] = "5266233158"

# Default configuration instance
config = Config()
