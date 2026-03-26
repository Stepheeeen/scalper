import logging
import sys
import os
from rich.logging import RichHandler

def setup_logger(name: str = "ScalpBot"):
    """
    Configures a beautiful logger with both Console (Rich) and File output.
    """
    # 1. Create logs directory if it doesn't exist
    log_dir = "logs"
    if not os.path.exists(log_dir):
        os.makedirs(log_dir)

    logging.basicConfig(
        level="INFO",
        format="%(asctime)s | %(levelname)s | %(message)s",
        datefmt="[%X]",
        handlers=[
            RichHandler(rich_tracebacks=True),
            logging.FileHandler(os.path.join(log_dir, "scalp_bot.log"), encoding="utf-8")
        ]
    )
    
    logger = logging.getLogger(name)
    return logger

logger = setup_logger()
