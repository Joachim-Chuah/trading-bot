import pytest
from datetime import date, timedelta
from screener.options import evaluate_options, _is_viable_leap


def future_date(days: int) -> str:
    return (date.today() + timedelta(days=days)).strftime("%Y-%m-%d")


def make_contract(
    strike: float = 195.0,
    current_price: float = 200.0,
    days_out: int = 425,
    iv: float = 20.0,
    open_interest: int = 500,
    bid: float = 5.0,
    ask: float = 5.50,
    contract_type: str = "call",
) -> dict:
    return {
        "details": {
            "strike_price": strike,
            "expiration_date": future_date(days_out),
            "contract_type": contract_type,
            "ticker": f"AAPL{future_date(days_out).replace('-', '')}C{int(strike * 1000):08d}",
        },
        "greeks": {"implied_volatility": iv},
        "open_interest": open_interest,
        "day": {"bid": bid, "ask": ask},
    }


# --- _is_viable_leap ---

def test_viable_call_passes():
    assert _is_viable_leap(make_contract(), 200.0) is True


def test_rejects_put():
    assert _is_viable_leap(make_contract(contract_type="put"), 200.0) is False


def test_rejects_expiry_under_365_days():
    assert _is_viable_leap(make_contract(days_out=364), 200.0) is False


def test_passes_expiry_at_365_days():
    assert _is_viable_leap(make_contract(days_out=365), 200.0) is True


def test_rejects_strike_more_than_10_pct_otm():
    # 200 * 0.90 = 180, strike 179 is >10% OTM
    assert _is_viable_leap(make_contract(strike=179.0), 200.0) is False


def test_passes_strike_at_10_pct_otm_boundary():
    assert _is_viable_leap(make_contract(strike=180.0), 200.0) is True


def test_rejects_strike_more_than_5_pct_itm():
    # 200 * 1.05 = 210, strike 211 is >5% ITM
    assert _is_viable_leap(make_contract(strike=211.0), 200.0) is False


def test_rejects_high_iv():
    assert _is_viable_leap(make_contract(iv=31.0), 200.0) is False


def test_passes_iv_at_boundary():
    assert _is_viable_leap(make_contract(iv=30.0), 200.0) is True


def test_rejects_low_open_interest():
    assert _is_viable_leap(make_contract(open_interest=99), 200.0) is False


def test_passes_open_interest_at_boundary():
    assert _is_viable_leap(make_contract(open_interest=100), 200.0) is True


def test_rejects_wide_bid_ask_spread():
    # mid = 7.75, spread = 4.0, relative = 4/7.75 = 0.516 > 0.15
    assert _is_viable_leap(make_contract(bid=5.75, ask=9.75), 200.0) is False


# --- evaluate_options ---

def test_returns_best_contract():
    chain = [make_contract(strike=195.0), make_contract(strike=198.0)]
    result = evaluate_options(chain, 200.0)
    assert result is not None
    assert result.strike == 198.0  # closest to current price


def test_returns_none_empty_chain():
    assert evaluate_options([], 200.0) is None


def test_returns_none_no_viable_contracts():
    chain = [make_contract(iv=50.0), make_contract(open_interest=5)]
    assert evaluate_options(chain, 200.0) is None


def test_returns_none_all_too_otm():
    chain = [make_contract(strike=150.0), make_contract(strike=160.0)]
    assert evaluate_options(chain, 200.0) is None


def test_otm_hard_limit_enforced():
    # 10% OTM of 200 = 180; strike 179 must be rejected
    chain = [make_contract(strike=179.0)]
    assert evaluate_options(chain, 200.0) is None
