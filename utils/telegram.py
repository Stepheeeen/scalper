import requests
from typing import List, Dict, Optional
from datetime import datetime
from utils.logger import logger

class TelegramNotifier:
    """
    Sends alerts and signal notifications to a Telegram bot.
    """
    def __init__(self, token: str, chat_id: str):
        self.token = token
        self.chat_id = chat_id
        self.base_url = f"https://api.telegram.org/bot{token}/sendMessage"

    def send_message(self, text: str, parse_mode: str = "Markdown"):
        """
        Sends a message to the configured Telegram chat.
        """
        if not self.token or not self.chat_id:
            logger.warning("Telegram token or chat ID missing. Skipping notification.")
            return False

        payload = {
            "chat_id": self.chat_id,
            "text": text,
            "parse_mode": parse_mode
        }

        try:
            response = requests.post(self.base_url, json=payload, timeout=10)
            if response.status_code == 200:
                logger.debug("Telegram message sent successfully.")
                return True
            else:
                logger.error(f"Failed to send Telegram message: {response.text}")
                return False
        except requests.exceptions.ConnectionError:
            logger.error("Network Error: Could not reach Telegram API (api.telegram.org). Please check your internet connection or firewall.")
            return False
        except Exception as e:
            logger.error(f"Error sending Telegram message: {e}")
            return False

    def send_photo(self, photo_path: str, caption: str = ""):
        """
        Sends a photo to the configured Telegram chat.
        """
        if not self.token or not self.chat_id:
            logger.warning("Telegram token or chat ID missing. Skipping notification.")
            return False

        url = f"https://api.telegram.org/bot{self.token}/sendPhoto"
        try:
            with open(photo_path, 'rb') as photo:
                files = {'photo': photo}
                payload = {'chat_id': self.chat_id, 'caption': caption, 'parse_mode': 'Markdown'}
                response = requests.post(url, data=payload, files=files, timeout=30)
                if response.status_code == 200:
                    logger.debug("Telegram photo sent successfully.")
                    return True
                else:
                    logger.error(f"Failed to send Telegram photo: {response.text}")
                    return False
        except Exception as e:
            logger.error(f"Error sending Telegram photo: {e}")
            return False

    def send_signal(self, symbol: str, side: str, entry: float, sl: float, reason: str):
        """
        Sends a formatted trade signal alert.
        """
        icon = "🟢" if side.upper() == "BUY" else "🔴"
        message = (
            f"{icon} *{side.upper()} SIGNAL: {symbol}*\n\n"
            f"📍 *Entry:* `{entry:.2f}`\n"
            f"🛡️ *Stop Loss:* `{sl:.2f}`\n"
            f"💡 *Reason:* {reason}\n"
            f"⏳ *Time:* {datetime.now().strftime('%H:%M:%S')}"
        )
        return self.send_message(message)

    def send_alert(self, level: str, message: str):
        """
        Sends a formatted system alert (INFO, WARNING, ERROR).
        """
        icons = {
            "INFO": "🔵",
            "WARNING": "🟡",
            "ERROR": "🔴",
            "SUCCESS": "🟢"
        }
        icon = icons.get(level.upper(), "⚪")
        formatted_message = f"{icon} *{level.upper()} ALERT*\n{message}"
        return self.send_message(formatted_message)

    def get_updates(self, offset: Optional[int] = None) -> List[Dict]:
        """
        Polls for new messages from the user.
        """
        if not self.token: return []
        
        url = f"https://api.telegram.org/bot{self.token}/getUpdates"
        params = {"timeout": 10, "offset": offset}
        try:
            response = requests.get(url, params=params, timeout=15)
            if response.status_code == 200:
                data = response.json()
                if data["ok"]:
                    return data["result"]
            return []
        except Exception:
            return []
