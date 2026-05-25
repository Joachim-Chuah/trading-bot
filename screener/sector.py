from clients.massive import get_snapshot
from clients.fmp import get_stock_screener

SECTOR_ETFS: dict[str, str] = {
    "Technology": "XLK",
    "Healthcare": "XLV",
    "Financial Services": "XLF",
    "Energy": "XLE",
    "Industrials": "XLI",
    "Consumer Cyclical": "XLY",
    "Consumer Defensive": "XLP",
    "Basic Materials": "XLB",
    "Real Estate": "XLRE",
    "Utilities": "XLU",
    "Communication Services": "XLC",
}


def score_sectors() -> list[tuple[str, float]]:
    """Score each sector ETF by day return + volume vs average, sorted descending."""
    scored = []
    for sector, etf in SECTOR_ETFS.items():
        try:
            snap = get_snapshot(etf)
        except Exception:
            continue
        day = snap.get("day", {})
        avg_vol = snap.get("min", {}).get("av", 0)
        day_return = snap.get("todaysChangePerc", 0.0)
        vol_ratio = day.get("v", 0) / avg_vol if avg_vol else 1.0
        score = day_return + (vol_ratio - 1.0) * 5.0
        scored.append((sector, score))
    return sorted(scored, key=lambda x: x[1], reverse=True)


def get_sector_universe(top_n: int | None = None) -> list[str]:
    """
    Return stock tickers from top_n sectors by momentum score.
    If top_n is None, returns stocks from all 11 sectors (for backtesting).
    """
    if top_n is None:
        sectors = list(SECTOR_ETFS.keys())
    else:
        ranked = score_sectors()
        sectors = [s for s, _ in ranked[:top_n]]

    tickers: list[str] = []
    for sector in sectors:
        try:
            stocks = get_stock_screener(sector)
            for s in stocks:
                tickers.append(s["symbol"])
        except Exception as e:
            print(f"[sector] failed to fetch {sector}: {e}")
            continue
    return list(dict.fromkeys(tickers))
