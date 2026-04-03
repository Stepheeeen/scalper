import pandas as pd
from typing import Dict, List, Optional
from config import config
from .structure import Trend

class ConfirmationEngine:
    """
    Evaluates setups based on confluence scoring and RR verification.
    """
    def __init__(self, config):
        self.config = config

    def calculate_confluence_score(self, setup: Dict, market_context: Dict) -> int:
        """
        Confluence Scoring (0-100):
        HTF Alignment: +30
        Quality Level: +20
        Session Timing: +20
        Liquidity Sweep: +15
        Rejection Quality: +15
        """
        score = 0
        
        # 1. HTF Alignment
        if setup.get('bias_alignment') == market_context.get('bias'):
            score += 30
        elif setup.get('bias_alignment') == "NEUTRAL":
            score += 10
            
        # 2. Quality Level (Is it a major level?)
        if setup.get('level_name') in ['pdh', 'pdl', 'daily_open']:
            score += 20
        elif setup.get('level_name') in ['session_high', 'session_low']:
            score += 15
            
        # 3. Session Timing
        if market_context.get('is_market_open'):
            score += 20
            
        # 4. Liquidity Sweep
        if setup.get('type') == 'BREAKOUT_TRAP':
            score += 15
            
        # 5. Rejection Quality (Simplified for now)
        if setup.get('type') == 'PIN_BAR_REVERSAL' or 'TREND_PULLBACK':
            score += 15
            
        return score

    def verify_rr(self, side: str, entry: float, sl: float, target_level: float) -> Optional[Dict]:
        """
        Ensures a minimum 1:2 and maximum 1:5 risk-to-reward ratio.
        """
        risk = abs(entry - sl)
        if risk == 0: return None
        
        reward = abs(entry - target_level)
        rr = reward / risk
        
        if self.config.risk.min_rr_ratio <= rr <= self.config.risk.max_rr_ratio:
            return {
                "rr": round(rr, 2),
                "is_valid": True,
                "reward_to_1": f"1:{round(rr, 1)}"
            }
        
        return None

    def validate_setup(self, setup: Dict, market_context: Dict) -> Optional[Dict]:
        """
        Full validation: Score check + RR check.
        """
        score = self.calculate_confluence_score(setup, market_context)
        
        if score < self.config.strategy.min_confluence_score:
            return None # Skip low quality setups
            
        # Calculate RR based on next structural target (Simplified for now)
        # In a real bot, we'd fetch the closest opposing fractal
        entry = setup.get('entry_price', 0) # In reality, entry is often break of candle
        sl = setup.get('stop_loss', 0)
        
        # Determine target based on side and HTF bias
        target_level = market_context.get('pdh') if setup['side'] == "BUY" else market_context.get('pdl')
        
        if not target_level: return None
        
        rr_data = self.verify_rr(setup['side'], entry, sl, target_level)
        
        if rr_data:
            setup['confluence_score'] = score
            setup.update(rr_data)
            return setup
            
        return None
