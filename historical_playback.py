import pandas as pd
from config import config
from data_feed.csv_feed import CSVDataProvider
from engine.backtest import BacktestEngine
from utils.logger import logger

def main():
    logger.info("🎬 *Starting Historical Playback*")
    
    # Configure for Backtest
    config.provider = "csv"
    
    # Initialize Data Provider with 30-day data
    file_paths = {
        "1m": "xauusd_1m.csv",
        "5m": "xauusd_5m.csv",
        "15m": "xauusd_15m.csv"
    }
    data_provider = CSVDataProvider(file_paths)
    
    # Initialize Backtest Engine
    engine = BacktestEngine(config, data_provider)
    
    # Run
    try:
        engine.run()
    except Exception as e:
        logger.error(f"Playback error: {e}")

if __name__ == "__main__":
    main()
