from models.stock import TechnicalsData
from typing import Literal

_RSI_DAILY_THRESHOLD = 40.0
_RSI_WEEKLY_THRESHOLD = 45.0
_SUPPORT_PROXIMITY = 0.03


def _moving_average(bars: list[dict], window: int) -> float | None:
    closes = [b["c"] for b in bars]
    if len(closes) < window:
        return None
    return sum(closes[-window:]) / window


def _at_support(price: float, daily_bars: list[dict]) -> bool:
    ma50 = _moving_average(daily_bars, 50)
    ma200 = _moving_average(daily_bars, 200)
    for ma in [ma50, ma200]:
        if ma is not None and abs(price - ma) / ma <= _SUPPORT_PROXIMITY:
            return True
    return False


def _macd_signal(macd_values: list[dict]) -> Literal["bullish", "neutral", "bearish"]:
    if not macd_values:
        return "neutral"
    latest = macd_values[0]
    histogram = latest.get("histogram", 0)
    if histogram > 0:
        return "bullish"
    if histogram < 0:
        return "bearish"
    return "neutral"


def evaluate_technicals(
    daily_bars: list[dict],
    daily_rsi: list[dict],
    weekly_rsi: list[dict],
    macd: list[dict],
    snapshot: dict,
) -> TechnicalsData | None:
    if not daily_rsi or not weekly_rsi:
        return None

    rsi_daily = daily_rsi[0]["value"]
    rsi_weekly = weekly_rsi[0]["value"]

    if rsi_daily >= _RSI_DAILY_THRESHOLD or rsi_weekly >= _RSI_WEEKLY_THRESHOLD:
        return None

    price = snapshot.get("day", {}).get("c", 0.0)
    at_support = _at_support(price, daily_bars)
    if not at_support:
        return None

    return TechnicalsData(
        rsi_daily=rsi_daily,
        rsi_weekly=rsi_weekly,
        macd_signal=_macd_signal(macd),
        at_support=at_support,
        price=price,
    )
