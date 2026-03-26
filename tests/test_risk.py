import pytest
from risk.manager import RiskManager
from config import Config

def test_calculate_position_size():
    cfg = Config()
    cfg.risk.risk_per_trade_percent = 1.0 # 1% risk
    manager = RiskManager(cfg)
    
    balance = 10000
    stop_loss_pips = 2.0 # $2.00 move in Gold
    
    # risk_amount = 10000 * 0.01 = 100
    # lot_size = 100 / (2.0 * 100) = 0.5
    lot_size = manager.calculate_position_size(balance, stop_loss_pips)
    assert lot_size == 0.5

def test_check_global_limits_max_trades():
    cfg = Config()
    cfg.risk.max_trades_per_day = 3
    manager = RiskManager(cfg)
    
    assert manager.check_global_limits(10000) == True
    manager.update_daily_stats(100)
    manager.update_daily_stats(100)
    manager.update_daily_stats(100)
    assert manager.check_global_limits(10300) == False

def test_check_global_limits_drawdown():
    cfg = Config()
    cfg.risk.max_daily_drawdown_percent = 2.0
    manager = RiskManager(cfg)
    manager.start_balance = 10000
    
    # 1% drawdown
    assert manager.check_global_limits(9900) == True
    # 2.1% drawdown
    assert manager.check_global_limits(9790) == False
