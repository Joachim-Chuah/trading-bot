from __future__ import annotations

import math
from dataclasses import dataclass, field
from datetime import date, timedelta

import numpy as np
import pandas as pd

from clients.yfinance_client import get_price_history

_RISK_FREE_RATE = 0.05
_WARMUP_DAYS = 200
_MIN_IV = 0.10
_RSI_DAILY_THRESHOLD = 45.0
_RSI_WEEKLY_THRESHOLD = 50.0
_SUPPORT_PROXIMITY = 0.03


@dataclass
class BacktestTrade:
    ticker: str
    entry_date: date
    exit_date: date
    entry_stock_price: float
    exit_stock_price: float
    strike: float
    expiration: date
    entry_option_price: float
    exit_option_price: float
    pnl_pct: float
    exit_reason: str  # "target" | "max_hold"


@dataclass
class BacktestResult:
    ticker: str
    trades: list[BacktestTrade] = field(default_factory=list)

    @property
    def hit_rate(self) -> float:
        if not self.trades:
            return 0.0
        return sum(1 for t in self.trades if t.pnl_pct > 0) / len(self.trades)

    @property
    def avg_return_pct(self) -> float:
        if not self.trades:
            return 0.0
        return sum(t.pnl_pct for t in self.trades) / len(self.trades)

    @property
    def avg_hold_days(self) -> float:
        if not self.trades:
            return 0.0
        return sum((t.exit_date - t.entry_date).days for t in self.trades) / len(self.trades)

    @property
    def total_trades(self) -> int:
        return len(self.trades)


def _norm_cdf(x: float) -> float:
    return (1.0 + math.erf(x / math.sqrt(2.0))) / 2.0


def _black_scholes_call(S: float, K: float, T: float, r: float, sigma: float) -> float:
    """Price a European call. T is time in years."""
    if T <= 0:
        return max(0.0, S - K)
    sigma = max(sigma, _MIN_IV)
    d1 = (math.log(S / K) + (r + 0.5 * sigma ** 2) * T) / (sigma * math.sqrt(T))
    d2 = d1 - sigma * math.sqrt(T)
    return S * _norm_cdf(d1) - K * math.exp(-r * T) * _norm_cdf(d2)


def _rsi(prices: pd.Series, period: int = 14) -> pd.Series:
    delta = prices.diff()
    gain = delta.clip(lower=0).rolling(period).mean()
    loss = (-delta.clip(upper=0)).rolling(period).mean()
    # When loss == 0, all periods were gains → RSI = 100
    rsi = pd.Series(
        np.where(loss == 0, 100.0, 100 - 100 / (1 + gain / loss)),
        index=prices.index,
    )
    return rsi


def _historical_vol(prices: pd.Series, window: int = 30) -> pd.Series:
    """Annualized realized volatility from daily log returns."""
    log_ret = np.log(prices / prices.shift(1))
    return log_ret.rolling(window).std() * math.sqrt(252)


def _entry_signals(prices: pd.Series) -> pd.Series:
    """Boolean Series — True on days all technical gates pass."""
    rsi_daily = _rsi(prices, 14)

    # Strip timezone for resample compatibility
    prices_local = prices.copy()
    if prices_local.index.tz is not None:
        prices_local.index = prices_local.index.tz_localize(None)

    weekly = prices_local.resample("W").last().dropna()
    rsi_weekly = _rsi(weekly, 14).reindex(prices_local.index, method="ffill")

    ma50 = prices.rolling(50).mean()
    ma200 = prices.rolling(200).mean()
    at_support = (
        ((prices - ma50).abs() / ma50 <= _SUPPORT_PROXIMITY) |
        ((prices - ma200).abs() / ma200 <= _SUPPORT_PROXIMITY)
    )

    return (rsi_daily < _RSI_DAILY_THRESHOLD) & (rsi_weekly < _RSI_WEEKLY_THRESHOLD) & at_support


def run_backtest(
    ticker: str,
    profit_target_pct: float = 0.50,
    max_hold_days: int = 90,
    leap_dte: int = 730,
    otm_pct: float = 0.05,
    vol_premium: float = 1.20,
) -> BacktestResult:
    result = BacktestResult(ticker=ticker)

    df = get_price_history(ticker)
    if df is None or len(df) < _WARMUP_DAYS + 1:
        return result

    prices = df["Close"].astype(float)

    # Strip timezone so date arithmetic works cleanly
    if prices.index.tz is not None:
        prices.index = prices.index.tz_localize(None)

    signals = _entry_signals(prices)
    iv_series = (_historical_vol(prices) * vol_premium).clip(lower=_MIN_IV)
    dates = prices.index

    in_trade_until: date | None = None

    for i in range(_WARMUP_DAYS, len(dates)):
        entry_dt = dates[i].date()

        if in_trade_until and entry_dt <= in_trade_until:
            continue

        if not signals.iloc[i]:
            continue

        S_entry = float(prices.iloc[i])
        K = round(S_entry * (1 + otm_pct), 2)
        iv = float(iv_series.iloc[i]) if not math.isnan(iv_series.iloc[i]) else _MIN_IV
        T_entry = leap_dte / 365.0
        option_entry = _black_scholes_call(S_entry, K, T_entry, _RISK_FREE_RATE, iv)

        if option_entry <= 0:
            continue

        target_price = option_entry * (1 + profit_target_pct)
        expiration = entry_dt + timedelta(days=leap_dte)

        exit_idx = min(i + max_hold_days, len(dates) - 1)
        exit_reason = "max_hold"

        for j in range(i + 1, min(i + max_hold_days + 1, len(dates))):
            S_j = float(prices.iloc[j])
            T_j = (expiration - dates[j].date()).days / 365.0
            iv_j_raw = float(iv_series.iloc[j])
            iv_j = iv_j_raw if not math.isnan(iv_j_raw) else iv
            option_j = _black_scholes_call(S_j, K, T_j, _RISK_FREE_RATE, iv_j)
            if option_j >= target_price:
                exit_idx = j
                exit_reason = "target"
                break

        exit_dt = dates[exit_idx].date()
        S_exit = float(prices.iloc[exit_idx])
        T_exit = max((expiration - exit_dt).days / 365.0, 0.0)
        iv_exit_raw = float(iv_series.iloc[exit_idx])
        iv_exit = iv_exit_raw if not math.isnan(iv_exit_raw) else iv
        option_exit = _black_scholes_call(S_exit, K, T_exit, _RISK_FREE_RATE, iv_exit)

        pnl_pct = (option_exit - option_entry) / option_entry

        result.trades.append(BacktestTrade(
            ticker=ticker,
            entry_date=entry_dt,
            exit_date=exit_dt,
            entry_stock_price=round(S_entry, 2),
            exit_stock_price=round(S_exit, 2),
            strike=K,
            expiration=expiration,
            entry_option_price=round(option_entry, 2),
            exit_option_price=round(option_exit, 2),
            pnl_pct=round(pnl_pct, 4),
            exit_reason=exit_reason,
        ))
        in_trade_until = exit_dt

    return result
