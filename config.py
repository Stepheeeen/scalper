import os
from pydantic import BaseModel, Field
from typing import List, Optional
from dotenv import load_dotenv

# Load environment variables from .env file
load_dotenv()

class SessionSettings(BaseModel):
    name: str
    start_time: str  # HH:MM UTC
    end_time: str    # HH:MM UTC
    enabled: bool = True

class RiskSettings(BaseModel):
    risk_per_trade_percent: float = 0.5  # User defined 0.5%
    max_daily_drawdown_percent: float = 2.0
    max_trades_per_day: int = 3
    max_consecutive_losses: int = 2
    min_rr_ratio: float = 2.0
    preferred_rr_ratio: float = 3.0
    max_rr_ratio: float = 5.0
    be_profit_pips: float = 10.0
    news_filter_enabled: bool = True

class StrategySettings(BaseModel):
    symbol: str = "XAUUSD"
    symbol_suffix: str = "m"
    max_spread_pips: float = 20
    min_confluence_score: int = 70
    htf_timeframe: str = "H1"
    entry_timeframe: str = "M5"

class AISettings(BaseModel):
    provider: str = "openai"
    model: str = "gpt-4-turbo-preview" # Latest stable stable
    api_key: Optional[str] = os.getenv("OPENAI_API_KEY")
    enabled: bool = True

class Config(BaseModel):
    trading_enabled: bool = True
    paper_trading: bool = True # Default Mode 1
    provider: str = "mt5"
    timezone_utc_offset: int = 0 # Configurable for local mapping
    
    sessions: List[SessionSettings] = [
        SessionSettings(name="London Kill Zone", start_time="07:00", end_time="10:00"),
        SessionSettings(name="New York Kill Zone", start_time="12:00", end_time="15:00"),
        SessionSettings(name="London-NY Overlap", start_time="12:00", end_time="14:00")
    ]
    
    risk: RiskSettings = RiskSettings()
    strategy: StrategySettings = StrategySettings()
    ai: AISettings = AISettings()
    
    # Credentials from Environment Variables
    mt5_login: Optional[int] = int(os.getenv("MT5_LOGIN", 0)) if os.getenv("MT5_LOGIN") else None
    mt5_password: Optional[str] = os.getenv("MT5_PASSWORD")
    mt5_server: Optional[str] = os.getenv("MT5_SERVER")
    
    telegram_token: Optional[str] = os.getenv("TELEGRAM_TOKEN")
    telegram_chat_id: Optional[str] = os.getenv("TELEGRAM_CHAT_ID")
    
    log_skipped_setups: bool = True

# Default configuration instance
config = Config()
