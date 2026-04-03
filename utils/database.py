import sqlite3
import os
from datetime import datetime
from typing import Dict, Any, List
from .logger import logger

class DatabaseManager:
    def __init__(self, db_path: str = "bot_data.db"):
        self.db_path = db_path
        self._init_db()

    def _init_db(self):
        """Initialize the SQLite database with professional journaling schema."""
        try:
            with sqlite3.connect(self.db_path) as conn:
                cursor = conn.cursor()
                
                # Trades Table (Expanded)
                cursor.execute("""
                    CREATE TABLE IF NOT EXISTS trades (
                        id INTEGER PRIMARY KEY AUTOINCREMENT,
                        ticket INTEGER UNIQUE,
                        symbol TEXT,
                        side TEXT,
                        strategy TEXT,
                        entry_price REAL,
                        sl REAL,
                        tp REAL,
                        profit_dollars REAL,
                        profit_percent REAL,
                        pnl_r REAL,
                        confluence_score INTEGER,
                        ai_note TEXT,
                        close_time DATETIME,
                        volume REAL
                    )
                """)
                
                # Skipped Setups Table (New)
                cursor.execute("""
                    CREATE TABLE IF NOT EXISTS skipped_setups (
                        id INTEGER PRIMARY KEY AUTOINCREMENT,
                        timestamp DATETIME DEFAULT CURRENT_TIMESTAMP,
                        symbol TEXT,
                        strategy TEXT,
                        reason_skipped TEXT,
                        confluence_score INTEGER,
                        market_context TEXT
                    )
                """)
                
                # Equity History Table
                cursor.execute("""
                    CREATE TABLE IF NOT EXISTS equity_history (
                        id INTEGER PRIMARY KEY AUTOINCREMENT,
                        timestamp DATETIME DEFAULT CURRENT_TIMESTAMP,
                        balance REAL,
                        equity REAL
                    )
                """)
                
                conn.commit()
        except Exception as e:
            logger.error(f"Failed to initialize database: {e}")

    def log_trade(self, trade_data: Dict[str, Any]):
        """Logs a completed trade with all confluences and AI commentary."""
        try:
            with sqlite3.connect(self.db_path) as conn:
                cursor = conn.cursor()
                cursor.execute("""
                    INSERT OR REPLACE INTO trades 
                    (ticket, symbol, side, strategy, entry_price, sl, tp, 
                     profit_dollars, profit_percent, pnl_r, confluence_score, ai_note, close_time, volume)
                    VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """, (
                    trade_data.get('ticket'),
                    trade_data.get('symbol'),
                    trade_data.get('side'),
                    trade_data.get('strategy'),
                    trade_data.get('entry_price'),
                    trade_data.get('sl'),
                    trade_data.get('tp'),
                    trade_data.get('profit_dollars'),
                    trade_data.get('profit_percent'),
                    trade_data.get('pnl_r'),
                    trade_data.get('confluence_score'),
                    trade_data.get('ai_note'),
                    trade_data.get('close_time', datetime.now().isoformat()),
                    trade_data.get('volume')
                ))
                conn.commit()
        except Exception as e:
            logger.error(f"Error logging trade to DB: {e}")

    def log_skipped_setup(self, setup_data: Dict[str, Any]):
        """Logs valid-looking setups that were rejected by rules."""
        try:
            with sqlite3.connect(self.db_path) as conn:
                cursor = conn.cursor()
                cursor.execute("""
                    INSERT INTO skipped_setups (symbol, strategy, reason_skipped, confluence_score, market_context)
                    VALUES (?, ?, ?, ?, ?)
                """, (
                    setup_data.get('symbol'),
                    setup_data.get('strategy'),
                    setup_data.get('reason'),
                    setup_data.get('score'),
                    setup_data.get('context')
                ))
                conn.commit()
        except Exception as e:
            logger.error(f"Error logging skipped setup to DB: {e}")

    def log_equity(self, balance: float, equity: float):
        try:
            with sqlite3.connect(self.db_path) as conn:
                cursor = conn.cursor()
                cursor.execute("INSERT INTO equity_history (balance, equity) VALUES (?, ?)", (balance, equity))
                conn.commit()
        except Exception as e:
            logger.error(f"Error logging equity: {e}")
