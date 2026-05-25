import math
import pytest
import pandas as pd
import numpy as np
from datetime import date, timedelta
from unittest.mock import patch

from screener.backtest import (
    _norm_cdf, _black_scholes_call, _rsi, _historical_vol,
    _entry_signals, run_backtest, BacktestResult, BacktestTrade,
)


def make_prices(values: list[float], start: str = "2015-01-02") -> pd.Series:
    index = pd.date_range(start=start, periods=len(values), freq="B")
    return pd.Series(values, index=index, name="Close")


def make_price_df(values: list[float], start: str = "2015-01-02") -> pd.DataFrame:
    return pd.DataFrame({"Close": make_prices(values, start)})


def make_oversold_history() -> pd.DataFrame:
    """220-day warmup trending up, 60-day sharp dip, 80-day recovery."""
    rng = np.random.default_rng(42)
    warmup = np.linspace(100, 155, 220) + rng.normal(0, 0.3, 220)
    dip = np.linspace(155, 118, 60) + rng.normal(0, 0.3, 60)
    recovery = np.linspace(118, 160, 80) + rng.normal(0, 0.3, 80)
    values = np.concatenate([warmup, dip, recovery]).tolist()
    return make_price_df(values)


# --- _norm_cdf ---

def test_norm_cdf_at_zero():
    assert abs(_norm_cdf(0.0) - 0.5) < 1e-6


def test_norm_cdf_large_positive():
    assert _norm_cdf(5.0) > 0.999


def test_norm_cdf_large_negative():
    assert _norm_cdf(-5.0) < 0.001


# --- _black_scholes_call ---

def test_bs_atm_call_reasonable_price():
    price = _black_scholes_call(S=100.0, K=100.0, T=2.0, r=0.05, sigma=0.25)
    assert 5.0 < price < 35.0


def test_bs_deep_itm_approaches_intrinsic():
    price = _black_scholes_call(S=200.0, K=100.0, T=2.0, r=0.05, sigma=0.25)
    assert price > 90.0


def test_bs_deep_otm_near_zero():
    price = _black_scholes_call(S=100.0, K=200.0, T=2.0, r=0.05, sigma=0.25)
    assert price < 5.0


def test_bs_expired_itm():
    price = _black_scholes_call(S=105.0, K=100.0, T=0.0, r=0.05, sigma=0.25)
    assert price == 5.0


def test_bs_expired_otm():
    price = _black_scholes_call(S=95.0, K=100.0, T=0.0, r=0.05, sigma=0.25)
    assert price == 0.0


def test_bs_higher_vol_raises_price():
    low = _black_scholes_call(S=100.0, K=105.0, T=2.0, r=0.05, sigma=0.20)
    high = _black_scholes_call(S=100.0, K=105.0, T=2.0, r=0.05, sigma=0.40)
    assert high > low


def test_bs_longer_dte_raises_price():
    short = _black_scholes_call(S=100.0, K=105.0, T=1.0, r=0.05, sigma=0.25)
    long_ = _black_scholes_call(S=100.0, K=105.0, T=2.0, r=0.05, sigma=0.25)
    assert long_ > short


def test_bs_zero_sigma_uses_floor():
    # sigma=0 should use _MIN_IV floor, not crash
    price = _black_scholes_call(S=100.0, K=100.0, T=2.0, r=0.05, sigma=0.0)
    assert price > 0.0


# --- _rsi ---

def test_rsi_all_up_days():
    prices = make_prices([100 + i for i in range(30)])
    rsi = _rsi(prices).dropna()
    assert rsi.iloc[-1] > 90


def test_rsi_all_down_days():
    prices = make_prices([100 - i * 0.8 for i in range(30)])
    rsi = _rsi(prices).dropna()
    assert rsi.iloc[-1] < 10


def test_rsi_values_in_range():
    prices = make_prices(make_oversold_history()["Close"].tolist())
    rsi = _rsi(prices).dropna()
    assert (rsi >= 0).all() and (rsi <= 100).all()


# --- _historical_vol ---

def test_historical_vol_positive():
    prices = make_prices(make_oversold_history()["Close"].tolist())
    vol = _historical_vol(prices).dropna()
    assert (vol > 0).all()


def test_historical_vol_annualized_range():
    prices = make_prices(make_oversold_history()["Close"].tolist())
    vol = _historical_vol(prices).dropna()
    assert 0.0 < vol.iloc[-1] < 3.0


# --- _entry_signals ---

def test_entry_signals_returns_bool_series():
    prices = make_prices(make_oversold_history()["Close"].tolist())
    signals = _entry_signals(prices)
    assert signals.dtype == bool


def test_entry_signals_fires_during_dip():
    prices = make_prices(make_oversold_history()["Close"].tolist())
    signals = _entry_signals(prices)
    # With a 25% dip over 60 days into established support, at least one signal should fire
    assert signals.any()


def test_entry_signals_no_signal_on_uptrend():
    # Steady uptrend — RSI always high, should never fire
    prices = make_prices([100 + i * 0.5 for i in range(300)])
    signals = _entry_signals(prices)
    assert not signals.any()


# --- run_backtest ---

@patch("screener.backtest.get_price_history")
def test_run_backtest_returns_result(mock_hist):
    mock_hist.return_value = make_oversold_history()
    result = run_backtest("AAPL")
    assert isinstance(result, BacktestResult)
    assert result.ticker == "AAPL"


@patch("screener.backtest.get_price_history")
def test_run_backtest_empty_on_insufficient_data(mock_hist):
    mock_hist.return_value = make_price_df([100.0] * 50)
    result = run_backtest("AAPL")
    assert result.trades == []
    assert result.total_trades == 0


@patch("screener.backtest.get_price_history")
def test_run_backtest_no_overlapping_trades(mock_hist):
    mock_hist.return_value = make_oversold_history()
    result = run_backtest("AAPL", max_hold_days=30)
    for i in range(1, len(result.trades)):
        assert result.trades[i].entry_date > result.trades[i - 1].exit_date


@patch("screener.backtest.get_price_history")
def test_run_backtest_trade_fields_valid(mock_hist):
    mock_hist.return_value = make_oversold_history()
    result = run_backtest("AAPL")
    for trade in result.trades:
        assert trade.entry_option_price > 0
        assert trade.exit_option_price >= 0
        assert trade.exit_reason in ("target", "max_hold")
        assert trade.exit_date >= trade.entry_date
        assert trade.strike > 0
        assert trade.expiration > trade.entry_date


@patch("screener.backtest.get_price_history")
def test_run_backtest_target_exit_pnl_positive(mock_hist):
    mock_hist.return_value = make_oversold_history()
    result = run_backtest("AAPL", profit_target_pct=0.50)
    target_exits = [t for t in result.trades if t.exit_reason == "target"]
    for trade in target_exits:
        assert trade.pnl_pct > 0


@patch("screener.backtest.get_price_history")
def test_backtest_result_properties(mock_hist):
    mock_hist.return_value = make_oversold_history()
    result = run_backtest("AAPL")
    if result.trades:
        assert 0.0 <= result.hit_rate <= 1.0
        assert isinstance(result.avg_return_pct, float)
        assert result.avg_hold_days > 0
        assert result.total_trades == len(result.trades)


@patch("screener.backtest.get_price_history")
def test_backtest_empty_result_properties(mock_hist):
    mock_hist.return_value = make_price_df([100.0] * 50)
    result = run_backtest("AAPL")
    assert result.hit_rate == 0.0
    assert result.avg_return_pct == 0.0
    assert result.avg_hold_days == 0.0
    assert result.total_trades == 0


@patch("screener.backtest.get_price_history")
def test_run_backtest_none_history(mock_hist):
    mock_hist.return_value = None
    result = run_backtest("AAPL")
    assert result.trades == []


@patch("screener.backtest.get_price_history")
def test_vol_premium_increases_option_price(mock_hist):
    mock_hist.return_value = make_oversold_history()
    result_base = run_backtest("AAPL", vol_premium=1.0)
    result_premium = run_backtest("AAPL", vol_premium=3.0)
    assert result_base.trades and result_premium.trades
    assert result_premium.trades[0].entry_option_price > result_base.trades[0].entry_option_price
