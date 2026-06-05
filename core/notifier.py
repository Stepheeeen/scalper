import asyncio
import requests
import logging
from config.settings import settings

logger = logging.getLogger(__name__)

class TelegramNotifier:
    def __init__(self):
        self.token = settings.telegram_token
        self.chat_id = settings.telegram_chat_id
        self.base_url = f"https://api.telegram.org/bot{self.token}/sendMessage" if self.token else None

    async def send_message(self, text: str):
        """Asynchronously sends a message via Telegram."""
        if not self.base_url or not self.chat_id:
            return

        payload = {
            "chat_id": self.chat_id,
            "text": text,
            "parse_mode": "HTML"
        }
        
        try:
            # Run the synchronous requests.post in a background thread
            response = await asyncio.to_thread(requests.post, self.base_url, data=payload, timeout=5)
            if response.status_code != 200:
                logger.error(f"Telegram notification failed: {response.text}")
        except Exception as e:
            logger.error(f"Telegram exception: {str(e)}")

notifier = TelegramNotifier()
