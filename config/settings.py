import os
from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict
from typing import List, Optional

class SessionWindow(BaseSettings):
    name: str
    start_utc: str
    end_utc: str

class Settings(BaseSettings):
    # App configs
    symbol: str = Field("XAUUSDm", env="SYMBOL")
    paper_trading: bool = Field(True, env="PAPER_TRADING")
    bypass_session_check: bool = Field(False, env="BYPASS_SESSION_CHECK")
    
    # MongoDB configs
    mongodb_uri: str = Field("mongodb://localhost:27017", env="MONGODB_URI")
    db_name: str = Field("xauusd_algo_db", env="DB_NAME")
    
    # MT5 configs
    mt5_login: Optional[int] = Field(None, env="MT5_LOGIN")
    mt5_password: Optional[str] = Field(None, env="MT5_PASSWORD")
    mt5_server: Optional[str] = Field(None, env="MT5_SERVER")
    mt5_path: Optional[str] = Field(None, env="MT5_PATH") # Useful if custom install path
    xgboost_model_path: Optional[str] = Field(None, env="XGBOOST_MODEL_PATH")
    
    # Telegram configs
    telegram_token: Optional[str] = Field(None, env="TELEGRAM_TOKEN")
    telegram_chat_id: Optional[str] = Field(None, env="TELEGRAM_CHAT_ID")
    
    # Safety Guards
    max_spread_raw: float = Field(0.50, env="MAX_SPREAD_RAW") # e.g. 0.50 = 50 cents spread
    min_sl_raw: float = Field(2.00, env="MIN_SL_RAW") # e.g. 2.00 = $2.00 minimum stop loss distance
    
    # Trading Sessions
    asian_session: SessionWindow = SessionWindow(name="Asian Session", start_utc="00:00", end_utc="06:00")
    london_session: SessionWindow = SessionWindow(name="London Session", start_utc="07:00", end_utc="11:00")
    ny_session: SessionWindow = SessionWindow(name="New York Session", start_utc="12:00", end_utc="16:00")
    
    model_config = SettingsConfigDict(env_file=".env", env_file_encoding="utf-8", extra="ignore")

settings = Settings()
