"""
Test suite for realistic taker fee calculation:
fee = C * rate * p * (1 - p)
"""
import pytest
from btc5m.simulator.fee_model import TakerFeeModel

def test_pm_fee_formula():
    # PM US default rate 0.075 (within [0.0695, 0.095])
    fee_model = TakerFeeModel(venue="polymarket", rate=0.075, c_multiplier=1.0)

    # At p = 0.50: fee = 1.0 * 0.075 * 0.5 * 0.5 = 0.01875
    f_50 = fee_model.fee_per_contract(0.50)
    assert abs(f_50 - 0.01875) < 1e-5

    # At p = 0.80: fee = 0.075 * 0.8 * 0.2 = 0.012
    f_80 = fee_model.fee_per_contract(0.80)
    assert abs(f_80 - 0.0120) < 1e-5

    # Total fee for 100 contracts
    total_fee = fee_model.calculate_total_fee(size=100.0, price=0.50)
    assert abs(total_fee - 1.875) < 1e-4

def test_kalshi_fee_formula():
    # Kalshi rate 0.07
    fee_model = TakerFeeModel(venue="kalshi", rate=0.07, c_multiplier=1.0)

    # At p = 0.50: fee = 1.0 * 0.07 * 0.25 = 0.0175
    f_50 = fee_model.fee_per_contract(0.50)
    assert abs(f_50 - 0.0175) < 1e-5

    # Total fee for 50 contracts at 0.40: 50 * (0.07 * 0.40 * 0.60) = 50 * 0.0168 = 0.84
    total = fee_model.calculate_total_fee(size=50.0, price=0.40)
    assert abs(total - 0.84) < 1e-4

def test_fee_boundaries():
    fee_model = TakerFeeModel(venue="polymarket")
    # At boundaries 0.0 and 1.0, fee converges to 0
    assert fee_model.fee_per_contract(0.0) == 0.0
    assert fee_model.fee_per_contract(1.0) == 0.0
