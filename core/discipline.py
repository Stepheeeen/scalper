from datetime import datetime, timezone
import asyncio
from config.settings import settings
from config.database import db
import logging

logger = logging.getLogger(__name__)

class Warden:
    """
    Enforces strict operational constraints. Blocks order routing if violated.
    """
    def __init__(self):
        self.max_trades_per_day = 2

    def _is_within_session(self, current_time: datetime, session) -> bool:
        start_hour, start_min = map(int, session.start_utc.split(':'))
        end_hour, end_min = map(int, session.end_utc.split(':'))
        
        current_minutes = current_time.hour * 60 + current_time.minute
        start_minutes = start_hour * 60 + start_min
        end_minutes = end_hour * 60 + end_min
        
        return start_minutes <= current_minutes <= end_minutes

    def is_valid_trading_session(self, current_time: datetime = None) -> bool:
        """Checks if the current UTC time falls within London or NY sessions."""
        if current_time is None:
            current_time = datetime.now(timezone.utc)
            
        is_london = self._is_within_session(current_time, settings.london_session)
        is_ny = self._is_within_session(current_time, settings.ny_session)
        
        return is_london or is_ny

    async def is_news_embargo_active(self) -> bool:
        """
        Placeholder framework/hook for an economic calendar scraper.
        Returns True if within 30 minutes before/after a high-impact news release.
        """
        # TODO: Implement actual news scraping logic here
        return False

    async def check_overtrading_limit(self) -> bool:
        """
        Queries MongoDB to count filled orders for the current calendar day.
        Returns True if the limit (2 trades) has been reached.
        """
        if not db.trades:
            logger.warning("Database not connected, skipping overtrading check.")
            return False
            
        today_str = datetime.now(timezone.utc).strftime("%Y-%m-%d")
        
        # Count trades for today
        trade_count = await db.trades.count_documents({"date": today_str})
        
        if trade_count >= self.max_trades_per_day:
            logger.warning(f"Overtrading limit reached. {trade_count}/{self.max_trades_per_day} trades executed today.")
            return True
            
        return False

    async def is_execution_allowed(self) -> tuple[bool, str]:
        """
        Master gatekeeper method. Checks all constraints.
        Returns (is_allowed, reason_if_blocked)
        """
        if not self.is_valid_trading_session():
            return False, "Outside valid trading sessions (London/NY)."
            
        if await self.is_news_embargo_active():
            return False, "High-impact news embargo active."
            
        if await self.check_overtrading_limit():
            return False, "Daily maximum trade limit (2) reached."
            
        return True, "Execution allowed."

warden = Warden()
