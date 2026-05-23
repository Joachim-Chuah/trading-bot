import pytest
from screener.spy_baseline import get_spy_baseline, _moving_average


def make_bars(n: int, close: float) -> list[dict]:
    return [{"c": close, "o": close, "h": close + 1, "l": close - 1, "v": 500000} for _ in range(n)]


def make_snapshot(price: float, prev_close: float = 515.0) -> dict:
    return {"day": {"c": price}, "prevDay": {"c": prev_close}}


def make_rsi(value: float) -> list[dict]:
    return [{"value": value}]


def make_macd(histogram: float) -> list[dict]:
    return [{"histogram": histogram}]


# --- _moving_average ---

def test_moving_average_50():
    bars = make_bars(50, 520.0)
    assert _moving_average(bars, 50) == 520.0


def test_moving_average_insufficient_bars():
    assert _moving_average(make_bars(10, 520.0), 50) is None


# --- get_spy_baseline ---

def test_spy_baseline_full():
    result = get_spy_baseline(
        snapshot=make_snapshot(520.0, prev_close=515.0),
        rsi=make_rsi(58.0),
        macd=make_macd(0.4),
        daily_bars=make_bars(200, 510.0),
    )
    assert result["price"] == 520.0
    assert result["change_pct"] == round((520 - 515) / 515 * 100, 2)
    assert result["rsi"] == 58.0
    assert result["macd_signal"] == "bullish"
    assert result["ma50"] is not None
    assert result["ma200"] is not None


def test_spy_baseline_bearish_macd():
    result = get_spy_baseline(
        snapshot=make_snapshot(520.0),
        rsi=make_rsi(45.0),
        macd=make_macd(-0.3),
        daily_bars=make_bars(200, 510.0),
    )
    assert result["macd_signal"] == "bearish"


def test_spy_baseline_neutral_macd():
    result = get_spy_baseline(
        snapshot=make_snapshot(520.0),
        rsi=make_rsi(50.0),
        macd=make_macd(0.0),
        daily_bars=make_bars(200, 510.0),
    )
    assert result["macd_signal"] == "neutral"


def test_spy_baseline_empty_rsi():
    result = get_spy_baseline(
        snapshot=make_snapshot(520.0),
        rsi=[],
        macd=make_macd(0.3),
        daily_bars=make_bars(200, 510.0),
    )
    assert result["rsi"] is None


def test_spy_baseline_empty_macd():
    result = get_spy_baseline(
        snapshot=make_snapshot(520.0),
        rsi=make_rsi(55.0),
        macd=[],
        daily_bars=make_bars(200, 510.0),
    )
    assert result["macd_signal"] is None


def test_spy_baseline_insufficient_bars_for_ma():
    result = get_spy_baseline(
        snapshot=make_snapshot(520.0),
        rsi=make_rsi(55.0),
        macd=make_macd(0.3),
        daily_bars=make_bars(30, 510.0),
    )
    assert result["ma50"] is None
    assert result["ma200"] is None


def test_spy_baseline_zero_prev_close():
    result = get_spy_baseline(
        snapshot={"day": {"c": 520.0}, "prevDay": {"c": 0.0}},
        rsi=make_rsi(55.0),
        macd=make_macd(0.3),
        daily_bars=make_bars(200, 510.0),
    )
    assert result["change_pct"] == 0.0
