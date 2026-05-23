from models.stock import FundamentalsData

_MIN_MARKET_CAP = 1_000_000_000
_MAX_PE = 100.0
_MAX_DEBT_EQUITY = 3.0


def evaluate_fundamentals(
    profile: dict,
    ratios: dict,
    income: dict,
) -> FundamentalsData | None:
    market_cap = profile.get("marketCap") or 0
    if market_cap < _MIN_MARKET_CAP:
        return None

    pe = ratios.get("priceToEarningsRatio")
    if pe is not None and (pe <= 0 or pe > _MAX_PE):
        return None

    debt_equity = ratios.get("debtToEquityRatio")
    if debt_equity is not None and debt_equity > _MAX_DEBT_EQUITY:
        return None

    eps = income.get("eps")
    if eps is not None and eps <= 0:
        return None

    revenue = income.get("revenue")
    revenue_growth = _revenue_growth(income)

    return FundamentalsData(
        market_cap=market_cap,
        pe_ratio=pe,
        revenue_growth=revenue_growth,
        debt_to_equity=debt_equity,
        eps=eps,
        sector=profile.get("sector"),
    )


def _revenue_growth(income: dict) -> float | None:
    revenue = income.get("revenue")
    prev_revenue = income.get("revenueGrowth")
    if prev_revenue is not None:
        return float(prev_revenue)
    return None
