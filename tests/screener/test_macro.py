import pytest
import pandas as pd
from screener.macro import get_macro_snapshot, _classify_signal, _classify_spy_trend


def make_vix_df(close: float) -> pd.DataFrame:
    return pd.DataFrame({"Close": [close]})


def make_daily_bars(n: int, close: float) -> list[dict]:
    return [{"c": close, "o": close, "h": close + 1, "l": close - 1, "v": 1000000} for _ in range(n)]


def make_bullish_bars() -> list[dict]:
    # older 150 bars at 490, newer 50 bars at 520 → ma50=520, ma200≈497
    return make_daily_bars(150, 490.0) + make_daily_bars(50, 520.0)


def make_bearish_bars() -> list[dict]:
    # older 150 bars at 530, newer 50 bars at 490 → ma50=490, ma200≈520
    return make_daily_bars(150, 530.0) + make_daily_bars(50, 490.0)


def make_spy_snapshot(price: float) -> dict:
    return {"day": {"c": price}}


def make_spy_rsi(value: float) -> list[dict]:
    return [{"value": value}]


# --- _classify_signal ---

def test_signal_hostile_high_vix():
    assert _classify_signal(31.0, None) == "hostile"


def test_signal_hostile_vix_boundary():
    assert _classify_signal(30.1, None) == "hostile"


def test_signal_hostile_elevated_vix_high_putcall():
    assert _classify_signal(25.0, 1.3) == "hostile"


def test_signal_neutral_elevated_vix_normal_putcall():
    assert _classify_signal(25.0, 0.9) == "neutral"


def test_signal_neutral_elevated_vix_no_putcall():
    assert _classify_signal(25.0, None) == "neutral"


def test_signal_neutral_low_vix_high_putcall():
    assert _classify_signal(18.0, 1.3) == "neutral"


def test_signal_favorable_low_vix_no_putcall():
    assert _classify_signal(18.0, None) == "favorable"


def test_signal_favorable_low_vix_normal_putcall():
    assert _classify_signal(15.0, 0.85) == "favorable"


def test_signal_favorable_vix_boundary():
    assert _classify_signal(20.0, None) == "favorable"


# --- _classify_spy_trend ---

def test_spy_trend_bullish():
    assert _classify_spy_trend(make_bullish_bars(), 530.0) == "bullish"


def test_spy_trend_bearish():
    assert _classify_spy_trend(make_bearish_bars(), 480.0) == "bearish"


def test_spy_trend_neutral_mixed():
    assert _classify_spy_trend(make_bullish_bars(), 515.0) == "neutral"


def test_spy_trend_insufficient_bars():
    bars = make_daily_bars(30, 520.0)
    assert _classify_spy_trend(bars, 520.0) == "neutral"


# --- get_macro_snapshot ---

def test_get_macro_snapshot_favorable():
    snapshot = get_macro_snapshot(
        vix_df=make_vix_df(16.0),
        put_call=0.85,
        spy_snapshot=make_spy_snapshot(520.0),
        spy_rsi=make_spy_rsi(58.0),
        spy_daily_bars=make_bullish_bars(),
    )
    assert snapshot.vix == 16.0
    assert snapshot.signal == "favorable"
    assert snapshot.put_call_ratio == 0.85
    assert snapshot.spy_price == 520.0
    assert snapshot.spy_rsi == 58.0


def test_get_macro_snapshot_hostile():
    snapshot = get_macro_snapshot(
        vix_df=make_vix_df(38.0),
        put_call=1.3,
        spy_snapshot=make_spy_snapshot(480.0),
        spy_rsi=make_spy_rsi(32.0),
        spy_daily_bars=make_bearish_bars(),
    )
    assert snapshot.signal == "hostile"


def test_get_macro_snapshot_no_putcall():
    snapshot = get_macro_snapshot(
        vix_df=make_vix_df(22.0),
        put_call=None,
        spy_snapshot=make_spy_snapshot(520.0),
        spy_rsi=make_spy_rsi(55.0),
        spy_daily_bars=make_bullish_bars(),
    )
    assert snapshot.put_call_ratio is None
    assert snapshot.signal == "neutral"


def test_get_macro_snapshot_empty_rsi_defaults_to_50():
    snapshot = get_macro_snapshot(
        vix_df=make_vix_df(16.0),
        put_call=None,
        spy_snapshot=make_spy_snapshot(520.0),
        spy_rsi=[],
        spy_daily_bars=make_bullish_bars(),
    )
    assert snapshot.spy_rsi == 50.0
