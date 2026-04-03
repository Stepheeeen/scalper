import openai
from typing import Dict, List, Optional
from config import config
from utils.logger import logger

class AIAssistant:
    """
    OpenAI-based assistant for trade commentary and journaling.
    Strictly restricted to the explanation/documentation layer.
    """
    def __init__(self, api_key: str):
        self.api_key = api_key
        self.client = openai.OpenAI(api_key=api_key) if api_key else None

    def generate_setup_commentary(self, setup: Dict, market_context: Dict) -> str:
        """Explains why a setup is valid or interesting."""
        if not self.client or not config.ai.enabled:
            return f"Setup: {setup['type']} at {setup['level']}."

        prompt = (
            f"You are a senior price action trader. Explain this setup to a human trader via Telegram.\n"
            f"Setup Type: {setup['type']}\n"
            f"Direction: {setup['side']}\n"
            f"Key Level: {setup['level']}\n"
            f"HTF Bias: {market_context.get('bias')}\n"
            f"Confluence Score: {setup.get('confluence_score', 'N/A')}\n"
            f"Concisely explain the logic and why this level is important. Max 3 sentences."
        )

        try:
            response = self.client.chat.completions.create(
                model=config.ai.model,
                messages=[{"role": "user", "content": prompt}],
                max_tokens=150
            )
            return response.choices[0].message.content.strip()
        except Exception as e:
            logger.error(f"AI Commentary error: {e}")
            return "Unable to generate AI commentary at this time."

    def generate_post_trade_note(self, trade: Dict, outcome: str) -> str:
        """Generates a journal entry for a completed trade."""
        if not self.client or not config.ai.enabled:
            return "Trade completed according to rules."

        prompt = (
            f"Review this trade and write a short journal note.\n"
            f"Strategy: {trade['strategy']}\n"
            f"Outcome: {outcome}\n"
            f"P&L: ${trade.get('profit_dollars', 0):.2f}\n"
            f"RR: {trade.get('rr', 'N/A')}\n"
            f"Reflect on the discipline and market behavior. Be objective. Max 2 sentences."
        )

        try:
            response = self.client.chat.completions.create(
                model=config.ai.model,
                messages=[{"role": "user", "content": prompt}],
                max_tokens=100
            )
            return response.choices[0].message.content.strip()
        except Exception as e:
            logger.error(f"AI Journaling error: {e}")
            return "Manual review required."

    def explain_skipped_setup(self, setup: Dict, reason: str) -> str:
        """Explains why a setup was valid-looking but rejected by rules."""
        if not self.client or not config.ai.enabled:
            return f"Skipped: {reason}"

        prompt = (
            f"Explain to the trader why this setup was skipped despite looking valid.\n"
            f"Setup: {setup['type']}\n"
            f"Rejection Reason: {reason}\n"
            f"Emphasis on discipline and rule-adherence. Max 2 sentences."
        )

        try:
            response = self.client.chat.completions.create(
                model=config.ai.model,
                messages=[{"role": "user", "content": prompt}],
                max_tokens=100
            )
            return response.choices[0].message.content.strip()
        except Exception as e:
            logger.error(f"AI Reflection error: {e}")
            return reason
