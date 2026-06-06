from datetime import datetime, timezone, timedelta
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
        if settings.bypass_session_check:
            return True
            
        if current_time is None:
            current_time = datetime.now(timezone.utc)
            
        is_london = self._is_within_session(current_time, settings.london_session)
        is_ny = self._is_within_session(current_time, settings.ny_session)
        
        return is_london or is_ny

    def is_market_closed(self, current_time: datetime = None) -> bool:
        """Checks if the global forex/gold market is closed (weekends: Fri 22:00 to Sun 22:00 UTC)."""
        if current_time is None:
            current_time = datetime.now(timezone.utc)
        weekday = current_time.weekday() # Mon = 0, Sun = 6
        hour = current_time.hour
        
        if weekday == 4: # Friday
            return hour >= 22
        elif weekday == 5: # Saturday
            return True
        elif weekday == 6: # Sunday
            return hour < 22
        return False

    def get_seconds_until_market_open(self, current_time: datetime = None) -> float:
        """Calculates the number of seconds until the next Sunday 22:00 UTC market open."""
        if current_time is None:
            current_time = datetime.now(timezone.utc)
        
        days_to_sunday = (6 - current_time.weekday()) % 7
        target_sunday = current_time.replace(hour=22, minute=0, second=0, microsecond=0)
        target_sunday += timedelta(days=days_to_sunday)
        
        if target_sunday <= current_time:
            target_sunday += timedelta(days=7)
            
        return (target_sunday - current_time).total_seconds()

    def get_seconds_until_next_session(self, current_time: datetime = None) -> float:
        """
        Calculates seconds until the start of the next London or NY session.
        If currently within a session, returns 0.
        """
        if current_time is None:
            current_time = datetime.now(timezone.utc)
            
        if self.is_valid_trading_session(current_time):
            return 0.0
            
        # Parse start times
        l_hour, l_min = map(int, settings.london_session.start_utc.split(':'))
        n_hour, n_min = map(int, settings.ny_session.start_utc.split(':'))
        
        # Candidate times for today
        london_today = current_time.replace(hour=l_hour, minute=l_min, second=0, microsecond=0)
        ny_today = current_time.replace(hour=n_hour, minute=n_min, second=0, microsecond=0)
        
        # Candidate times for tomorrow
        london_tomorrow = london_today + timedelta(days=1)
        ny_tomorrow = ny_today + timedelta(days=1)
        
        candidates = [london_today, ny_today, london_tomorrow, ny_tomorrow]
        # Filter out candidates in the past or on weekends
        valid_candidates = []
        for c in candidates:
            if c > current_time and not self.is_market_closed(c):
                valid_candidates.append(c)
                    
        if not valid_candidates:
            # If no weekday candidates (e.g. it's Friday night), use the next market open
            return self.get_seconds_until_market_open(current_time)
            
        next_session_time = min(valid_candidates)
        return (next_session_time - current_time).total_seconds()

    async def is_news_embargo_active(self) -> bool:
        """
        Fetches economic calendar data from Yahoo Finance and checks if we are
        within a 30-minute embargo window (before or after) of a high-impact US news release.
        """
        import requests
        import re
        import json
        from datetime import datetime, timezone, timedelta
        
        headers = {
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36'
        }
        
        url = 'https://finance.yahoo.com/calendar/economic'
        try:
            # Fetch Yahoo Finance calendar asynchronously to avoid blocking the event loop
            response = await asyncio.to_thread(requests.get, url, headers=headers, timeout=10)
            if response.status_code != 200:
                logger.warning(f"Failed to fetch economic calendar: HTTP {response.status_code}")
                return False
                
            # Search for economicEvents script
            scripts = re.findall(r'<script.*?>((?:.|\n)*?)</script>', response.text)
            events_data = []
            for s in scripts:
                if "economicEvents" in s:
                    try:
                        payload = json.loads(s.strip())
                        body = json.loads(payload["body"])
                        events_data = body["finance"]["result"]["economicEvents"]
                        break
                    except Exception:
                        continue
                        
            if not events_data:
                logger.warning("Could not parse economic calendar script from Yahoo Finance.")
                return False
                
            now_utc = datetime.now(timezone.utc)
            high_impact_keywords = {"payrolls", "cpi", "fomc", "gdp", "interest rate", "unemployment rate", "fed", "retail sales"}
            
            for day in events_data:
                for record in day.get('records', []):
                    # Check if the country is US
                    if record.get('countryCode') == 'US':
                        event_name = record.get('event', '').lower()
                        # Check if high impact
                        if any(kw in event_name for kw in high_impact_keywords):
                            event_time_ms = record.get('eventTime')
                            if event_time_ms:
                                event_dt = datetime.fromtimestamp(event_time_ms / 1000.0, timezone.utc)
                                time_diff = abs((now_utc - event_dt).total_seconds())
                                # Check if within 30 minutes (1800 seconds)
                                if time_diff <= 1800:
                                    logger.warning(f"NEWS EMBARGO ACTIVE: Near {record.get('event')} at {event_dt.isoformat()}")
                                    return True
            return False
        except Exception as e:
            logger.error(f"Error checking news embargo: {e}")
            return False

    async def check_overtrading_limit(self) -> bool:
        """
        Queries MongoDB to count filled orders for the current calendar day.
        Returns True if the limit (2 trades) has been reached.
        """
        if db.trades is None:
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
