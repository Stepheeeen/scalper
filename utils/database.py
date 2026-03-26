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
        """Initialize the SQLite database and create tables if they don't exist."""
        try:
            with sqlite3.connect(self.db_path) as conn:
                cursor = conn.cursor()
                
                # Trades Table
                cursor.execute("""
                    CREATE TABLE IF NOT EXISTS trades (
                        id INTEGER PRIMARY KEY AUTOINCREMENT,
                        ticket INTEGER UNIQUE,
                        symbol TEXT,
                        type TEXT,
                        entry_price REAL,
                        sl REAL,
                        tp REAL,
                        profit REAL,
                        close_time DATETIME,
                        volume REAL
                    )
                """)
                
                # Signals/Events Table
                cursor.execute("""
                    CREATE TABLE IF NOT EXISTS signals (
                        id INTEGER PRIMARY KEY AUTOINCREMENT,
                        timestamp DATETIME DEFAULT CURRENT_TIMESTAMP,
                        symbol TEXT,
                        type TEXT,
                        reason TEXT,
                        price REAL
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
                logger.info(f"Database initialized at {self.db_path}")
        except Exception as e:
            logger.error(f"Failed to initialize database: {e}")

    def log_trade(self, trade_data: Dict[str, Any]):
        """Logs a completed trade to the database."""
        try:
            with sqlite3.connect(self.db_path) as conn:
                cursor = conn.cursor()
                cursor.execute("""
                    INSERT OR REPLACE INTO trades 
                    (ticket, symbol, type, entry_price, sl, tp, profit, close_time, volume)
                    VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
                """, (
                    trade_data.get('ticket'),
                    trade_data.get('symbol'),
                    trade_data.get('type'),
                    trade_data.get('entry_price'),
                    trade_data.get('sl'),
                    trade_data.get('tp'),
                    trade_data.get('profit'),
                    trade_data.get('close_time', datetime.now().isoformat()),
                    trade_data.get('volume')
                ))
                conn.commit()
        except Exception as e:
            logger.error(f"Error logging trade to DB: {e}")

    def log_signal(self, symbol: str, signal_type: str, reason: str, price: float):
        """Logs a strategy signal/event."""
        try:
            with sqlite3.connect(self.db_path) as conn:
                cursor = conn.cursor()
                cursor.execute("""
                    INSERT INTO signals (symbol, type, reason, price)
                    VALUES (?, ?, ?, ?)
                """, (symbol, signal_type, reason, price))
                conn.commit()
        except Exception as e:
            logger.error(f"Error logging signal to DB: {e}")

    def log_equity(self, balance: float, equity: float):
        """Logs a snapshot of the account balance and equity."""
        try:
            # We only log if the value has changed significantly or every hour
            # (To keep the DB small)
            with sqlite3.connect(self.db_path) as conn:
                cursor = conn.cursor()
                cursor.execute("""
                    INSERT INTO equity_history (balance, equity)
                    VALUES (?, ?)
                """, (balance, equity))
                conn.commit()
        except Exception as e:
            logger.error(f"Error logging equity to DB: {e}")

    def get_equity_data(self) -> List[Dict[str, Any]]:
        """Retrieves equity history for charting."""
        try:
            with sqlite3.connect(self.db_path) as conn:
                conn.row_factory = sqlite3.Row
                cursor = conn.cursor()
                cursor.execute("SELECT timestamp, balance, equity FROM equity_history ORDER BY timestamp ASC")
                return [dict(row) for row in cursor.fetchall()]
        except Exception as e:
            logger.error(f"Error fetching equity data: {e}")
            return []
