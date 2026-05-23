UNIVERSE: list[str] = [
    # Mega-cap tech
    "AAPL", "MSFT", "NVDA", "GOOGL", "META", "AMZN", "TSLA", "AVGO", "ORCL", "AMD",
    "INTC", "QCOM", "TXN", "MU", "AMAT", "KLAC", "LRCX", "ADI", "MRVL", "NOW",
    "CRM", "ADBE", "INTU", "SNPS", "CDNS",
    # Financials
    "JPM", "BAC", "WFC", "GS", "MS", "BLK", "SCHW", "AXP", "V", "MA",
    "COF", "USB", "PNC", "TFC", "MET", "PRU", "AFL", "ALL", "CB", "MMC",
    # Healthcare
    "UNH", "JNJ", "LLY", "ABBV", "MRK", "PFE", "TMO", "ABT", "DHR", "BMY",
    "AMGN", "GILD", "VRTX", "REGN", "ISRG", "SYK", "BSX", "MDT", "ZBH", "BAX",
    # Consumer
    "AMZN", "COST", "WMT", "TGT", "HD", "LOW", "NKE", "SBUX", "MCD", "YUM",
    "PG", "KO", "PEP", "PM", "MO", "CL", "EL", "MNST",
    # Industrials & Energy
    "CAT", "DE", "HON", "GE", "RTX", "LMT", "NOC", "BA", "UPS", "FDX",
    "XOM", "CVX", "COP", "SLB", "EOG", "PSX", "VLO", "MPC",
    # Communication & Media
    "NFLX", "DIS", "CMCSA", "T", "VZ", "TMUS",
]

# Deduplicate while preserving order (AMZN appears in both tech and consumer)
UNIVERSE = list(dict.fromkeys(UNIVERSE))
