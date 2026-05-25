from clients.massive import get_snapshot
from clients.fmp import get_etf_holdings

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

SECTOR_UNIVERSE: dict[str, list[str]] = {
    "Technology": ["AAPL", "MSFT", "NVDA", "AVGO", "ORCL", "CRM", "AMD", "QCOM", "TXN", "NOW", "AMAT", "ADI", "MU", "KLAC", "INTC"],
    "Healthcare": ["LLY", "UNH", "JNJ", "ABBV", "MRK", "TMO", "ABT", "DHR", "BMY", "AMGN", "PFE", "ISRG", "MDT", "SYK", "GILD"],
    "Financial Services": ["JPM", "BAC", "WFC", "GS", "MS", "BLK", "SPGI", "CB", "PGR", "CME", "ICE", "AXP", "V", "MA", "COF"],
    "Energy": ["XOM", "CVX", "COP", "EOG", "SLB", "MPC", "PSX", "VLO", "OXY", "HAL", "DVN", "BKR", "HES", "MRO", "FANG"],
    "Industrials": ["GE", "RTX", "CAT", "HON", "UNP", "LMT", "DE", "EMR", "ETN", "ITW", "GD", "WM", "PH", "NOC", "FDX"],
    "Consumer Cyclical": ["AMZN", "TSLA", "HD", "MCD", "NKE", "LOW", "SBUX", "TJX", "BKNG", "CMG", "DHI", "ORLY", "AZO", "MAR", "F"],
    "Consumer Defensive": ["WMT", "PG", "COST", "KO", "PEP", "PM", "MO", "CL", "MDLZ", "GIS", "SYY", "K", "HSY", "CAG", "STZ"],
    "Basic Materials": ["LIN", "APD", "SHW", "ECL", "FCX", "NEM", "NUE", "VMC", "MLM", "ALB", "CF", "MOS", "PPG", "EMN", "CTVA"],
    "Real Estate": ["PLD", "AMT", "EQIX", "CCI", "PSA", "O", "WELL", "SPG", "DLR", "AVB", "EQR", "VICI", "EXR", "ARE", "WY"],
    "Utilities": ["NEE", "DUK", "SO", "D", "SRE", "AEP", "EXC", "XEL", "PCG", "ED", "ETR", "FE", "WEC", "AWK", "DTE"],
    "Communication Services": ["GOOGL", "META", "NFLX", "DIS", "CMCSA", "T", "VZ", "TMUS", "CHTR", "EA", "WBD", "FOXA", "OMC", "IPG", "TTWO"],
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
    if top_n is None:
        sectors = list(SECTOR_UNIVERSE.keys())
    else:
        ranked = score_sectors()
        sectors = [s for s, _ in ranked[:top_n]]

    tickers: list[str] = []
    for sector in sectors:
        etf = SECTOR_ETFS[sector]
        try:
            live = get_etf_holdings(etf)
        except Exception:
            live = []
        holdings = live if live else SECTOR_UNIVERSE[sector]
        if not live:
            print(f"[sector] using static universe for {sector}")
        tickers.extend(holdings)
    return list(dict.fromkeys(tickers))
