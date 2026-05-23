from typing import Any


def get_spy_baseline(
    snapshot: dict,
    rsi: list[dict],
    macd: list[dict],
    daily_bars: list[dict],
) -> dict[str, Any]:
    price = snapshot.get("day", {}).get("c", 0.0)
    prev_close = snapshot.get("prevDay", {}).get("c", 0.0)
    change_pct = round((price - prev_close) / prev_close * 100, 2) if prev_close else 0.0

    latest_rsi = rsi[0]["value"] if rsi else None

    macd_signal = None
    if macd:
        h = macd[0].get("histogram", 0)
        macd_signal = "bullish" if h > 0 else ("bearish" if h < 0 else "neutral")

    ma50 = _moving_average(daily_bars, 50)
    ma200 = _moving_average(daily_bars, 200)

    return {
        "price": price,
        "change_pct": change_pct,
        "rsi": latest_rsi,
        "macd_signal": macd_signal,
        "ma50": round(ma50, 2) if ma50 else None,
        "ma200": round(ma200, 2) if ma200 else None,
    }


def _moving_average(bars: list[dict], window: int) -> float | None:
    closes = [b["c"] for b in bars]
    if len(closes) < window:
        return None
    return sum(closes[-window:]) / window
