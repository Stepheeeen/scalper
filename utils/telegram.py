import requests
from typing import List, Dict, Optional
from datetime import datetime
from utils.logger import logger

class TelegramNotifier:
    """
    Sends structured alerts and signals for the Naked Price Action bot.
    Supports lifecycle events: Open, Setup, Entry, Management, Exit, Summaries.
    """
    def __init__(self, token: str, chat_id: str):
        self.token = token
        self.chat_id = chat_id
        self.base_url = f"https://api.telegram.org/bot{token}/sendMessage"

    def _send(self, text: str, parse_mode: str = "HTML"):
        if not self.token or not self.chat_id:
            logger.warning("Telegram credentials missing. Skipping.")
            return False
            
        payload = {"chat_id": self.chat_id, "text": text, "parse_mode": parse_mode}
        try:
            response = requests.post(self.base_url, json=payload, timeout=10)
            return response.status_code == 200
        except Exception as e:
            logger.error(f"Telegram error: {e}")
            return False

    def send_daily_open(self, data: Dict):
        """1. DAILY MARKET OPEN SUMMARY"""
        msg = (
            f"<b>☀️ DAILY MARKET OPEN | {data['date']}</b>\n"
            f"━━━━━━━━━━━━━━━━━━━━\n"
            f"🏛 <b>Instrument:</b> {data['symbol']}\n"
            f"🧭 <b>HTF Bias:</b> {data['bias']}\n"
            f"📍 <b>Levels:</b> PDH: {data['pdh']} | PDL: {data['pdl']}\n"
            f"⏰ <b>Session Windows:</b> {data['sessions']}\n"
            f"📝 <b>Primary Scenarios:</b> {data['scenarios']}\n"
        )
        return self._send(msg)

    def send_setup_alert(self, setup: Dict):
        """2. SETUP CONFIRMATION ALERT"""
        msg = (
            f"<b>🔍 SETUP DETECTED | {setup['type']}</b>\n"
            f"━━━━━━━━━━━━━━━━━━━━\n"
            f"🏷 <b>Timeframe:</b> {setup['timeframe']}\n"
            f"↕️ <b>Direction:</b> {setup['side']}\n"
            f"🎯 <b>Key Level:</b> {setup['level']}\n"
            f"📊 <b>Confluence Score:</b> {setup['confluence_score']}/100\n"
            f"💡 <b>Reason:</b> {setup['reason']}\n"
            f"⏳ <i>Waiting for trigger...</i>"
        )
        return self._send(msg)

    def send_entry_alert(self, trade: Dict):
        """3. ENTRY ALERT"""
        msg = (
            f"<b>🚀 TRADE EXECUTED | {trade['strategy']}</b>\n"
            f"━━━━━━━━━━━━━━━━━━━━\n"
            f"📈 <b>{trade['side']}</b> @ {trade['entry']}\n"
            f"🛡 <b>SL:</b> {trade['sl']} | 🎯 <b>TP:</b> {trade['tp']}\n"
            f"⚖️ <b>RR:</b> {trade['rr']} | 💰 <b>Risk:</b> {trade['risk_percent']}%\n"
            f"📋 <b>Rationale:</b> {trade['rationale']}\n"
        )
        return self._send(msg)

    def send_management_alert(self, ticket: int, event: str, price: float):
        """4. TRADE MANAGEMENT ALERT"""
        msg = (
            f"<b>⚙️ TRADE MANAGEMENT | #{ticket}</b>\n"
            f"━━━━━━━━━━━━━━━━━━━━\n"
            f"📢 <b>Event:</b> {event}\n"
            f"📍 <b>Current Price:</b> {price}\n"
        )
        return self._send(msg)

    def send_exit_alert(self, trade: Dict):
        """5. EXIT ALERT"""
        pnl_icon = "💰" if trade['profit_dollars'] > 0 else "📉"
        msg = (
            f"{pnl_icon} <b>TRADE CLOSED | {trade['symbol']}</b>\n"
            f"━━━━━━━━━━━━━━━━━━━━\n"
            f"🏁 <b>Reason:</b> {trade['exit_reason']}\n"
            f"💵 <b>P&L:</b> ${trade['profit_dollars']:.2f} ({trade['profit_percent']:.2f}%)\n"
            f"📊 <b>RR Result:</b> {trade['rr_result']}R\n"
            f"⏱ <b>Duration:</b> {trade['duration']}\n"
            f"🤖 <b>AI Note:</b> {trade['ai_note']}\n"
        )
        return self._send(msg)

    def send_performance_summary(self, stats: Dict, is_weekly: bool = False):
        """6/7. DAILY/WEEKLY PERFORMANCE SUMMARY"""
        title = "📅 DAILY PERFORMANCE" if not is_weekly else "🗓 WEEKLY PERFORMANCE"
        msg = (
            f"<b>{title} | {stats['date']}</b>\n"
            f"━━━━━━━━━━━━━━━━━━━━\n"
            f"✅ <b>Wins:</b> {stats['wins']} | ❌ <b>Losses:</b> {stats['losses']}\n"
            f"🎯 <b>Win Rate:</b> {stats['win_rate']:.1f}%\n"
            f"📈 <b>Net P&L:</b> {stats['net_pnl_percent']:.2f}%\n"
            f"🔢 <b>Total R:</b> {stats['total_r']:.1f}R\n"
            f"🚫 <b>Skipped Setups:</b> {stats['skipped_count']}\n"
            f"🏆 <b>Best:</b> {stats['best_trade']}\n"
        )
        return self._send(msg)

    def send_alert(self, level: str, message: str):
        icons = {"INFO": "🔵", "WARNING": "🟡", "ERROR": "🔴", "SUCCESS": "🟢"}
        msg = f"{icons.get(level, '⚪')} <b>{level} ALERT</b>\n{message}"
        return self._send(msg)
