import pytest
from screener.technicals import evaluate_technicals, _macd_signal, _at_support


def make_bars(n: int, close: float) -> list[dict]:
    return [{"c": close, "o": close, "h": close + 1, "l": close - 1, "v": 500000} for _ in range(n)]


def make_support_bars() -> list[dict]:
    # 200 bars; current price will be set close to the MA (~500)
    return make_bars(200, 500.0)


def make_rsi(value: float) -> list[dict]:
    return [{"value": value}]


def make_macd(histogram: float) -> list[dict]:
    return [{"value": -1.0, "signal": -0.5, "histogram": histogram}]


def make_snapshot(price: float) -> dict:
    return {"day": {"c": price}}


# --- _macd_signal ---

def test_macd_bullish():
    assert _macd_signal(make_macd(0.5)) == "bullish"


def test_macd_bearish():
    assert _macd_signal(make_macd(-0.5)) == "bearish"


def test_macd_neutral_zero():
    assert _macd_signal(make_macd(0.0)) == "neutral"


def test_macd_empty():
    assert _macd_signal([]) == "neutral"


# --- _at_support ---

def test_at_support_near_ma():
    bars = make_support_bars()
    assert _at_support(502.0, bars) is True


def test_not_at_support_far_from_ma():
    bars = make_support_bars()
    assert _at_support(600.0, bars) is False


def test_at_support_insufficient_bars():
    assert _at_support(500.0, make_bars(10, 500.0)) is False


# --- evaluate_technicals ---

def test_passes_all_gates():
    result = evaluate_technicals(
        daily_bars=make_support_bars(),
        daily_rsi=make_rsi(32.0),
        weekly_rsi=make_rsi(38.0),
        macd=make_macd(0.3),
        snapshot=make_snapshot(502.0),
    )
    assert result is not None
    assert result.rsi_daily == 32.0
    assert result.rsi_weekly == 38.0
    assert result.macd_signal == "bullish"
    assert result.at_support is True


def test_discards_daily_rsi_too_high():
    result = evaluate_technicals(
        daily_bars=make_support_bars(),
        daily_rsi=make_rsi(40.0),
        weekly_rsi=make_rsi(38.0),
        macd=make_macd(0.3),
        snapshot=make_snapshot(502.0),
    )
    assert result is None


def test_discards_weekly_rsi_too_high():
    result = evaluate_technicals(
        daily_bars=make_support_bars(),
        daily_rsi=make_rsi(32.0),
        weekly_rsi=make_rsi(45.0),
        macd=make_macd(0.3),
        snapshot=make_snapshot(502.0),
    )
    assert result is None


def test_discards_not_at_support():
    result = evaluate_technicals(
        daily_bars=make_support_bars(),
        daily_rsi=make_rsi(32.0),
        weekly_rsi=make_rsi(38.0),
        macd=make_macd(0.3),
        snapshot=make_snapshot(600.0),
    )
    assert result is None


def test_discards_missing_rsi():
    result = evaluate_technicals(
        daily_bars=make_support_bars(),
        daily_rsi=[],
        weekly_rsi=make_rsi(38.0),
        macd=make_macd(0.3),
        snapshot=make_snapshot(502.0),
    )
    assert result is None


def test_discards_missing_weekly_rsi():
    result = evaluate_technicals(
        daily_bars=make_support_bars(),
        daily_rsi=make_rsi(32.0),
        weekly_rsi=[],
        macd=make_macd(0.3),
        snapshot=make_snapshot(502.0),
    )
    assert result is None
