from typing import Literal
import pandas as pd
from models.stock import MacroSnapshot


def _classify_signal(vix: float, put_call: float | None) -> Literal["favorable", "neutral", "hostile"]:
    if vix > 30:
        return "hostile"
    if vix > 20:
        if put_call is not None and put_call > 1.2:
            return "hostile"
        return "neutral"
    # vix <= 20
    if put_call is not None and put_call > 1.2:
        return "neutral"
    return "favorable"


def _classify_spy_trend(daily_bars: list[dict], current_price: float) -> Literal["bullish", "neutral", "bearish"]:
    if len(daily_bars) < 50:
        return "neutral"
    closes = [b["c"] for b in daily_bars]
    ma50 = sum(closes[-50:]) / 50
    ma200 = sum(closes[-200:]) / 200 if len(closes) >= 200 else ma50
    if current_price > ma50 and ma50 > ma200:
        return "bullish"
    if current_price < ma50 and ma50 < ma200:
        return "bearish"
    return "neutral"


def get_macro_snapshot(
    vix_df: pd.DataFrame,
    put_call: float | None,
    spy_snapshot: dict,
    spy_rsi: list[dict],
    spy_daily_bars: list[dict],
) -> MacroSnapshot:
    vix = float(vix_df["Close"].iloc[-1])
    spy_price = spy_snapshot.get("day", {}).get("c", 0.0)
    latest_rsi = spy_rsi[0]["value"] if spy_rsi else 50.0
    spy_trend = _classify_spy_trend(spy_daily_bars, spy_price)
    signal = _classify_signal(vix, put_call)

    return MacroSnapshot(
        vix=vix,
        put_call_ratio=put_call,
        signal=signal,
        spy_price=spy_price,
        spy_rsi=latest_rsi,
        spy_trend=spy_trend,
    )
