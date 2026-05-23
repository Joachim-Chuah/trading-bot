import pytest
from screener.fundamentals import evaluate_fundamentals


def make_profile(market_cap: float = 5_000_000_000, sector: str = "Technology") -> dict:
    return {"marketCap": market_cap, "sector": sector}


def make_ratios(pe: float = 25.0, debt_equity: float = 1.0) -> dict:
    return {"priceToEarningsRatio": pe, "debtToEquityRatio": debt_equity}


def make_income(eps: float = 5.0, revenue: float = 1_000_000_000) -> dict:
    return {"eps": eps, "revenue": revenue, "revenueGrowth": 0.08}


def test_passes_all_gates():
    result = evaluate_fundamentals(make_profile(), make_ratios(), make_income())
    assert result is not None
    assert result.market_cap == 5_000_000_000
    assert result.sector == "Technology"
    assert result.pe_ratio == 25.0
    assert result.eps == 5.0


def test_discards_below_min_market_cap():
    assert evaluate_fundamentals(make_profile(market_cap=500_000_000), make_ratios(), make_income()) is None


def test_discards_negative_pe():
    assert evaluate_fundamentals(make_profile(), make_ratios(pe=-5.0), make_income()) is None


def test_discards_zero_pe():
    assert evaluate_fundamentals(make_profile(), make_ratios(pe=0.0), make_income()) is None


def test_discards_extreme_pe():
    assert evaluate_fundamentals(make_profile(), make_ratios(pe=101.0), make_income()) is None


def test_passes_pe_at_boundary():
    result = evaluate_fundamentals(make_profile(), make_ratios(pe=100.0), make_income())
    assert result is not None


def test_discards_high_debt_equity():
    assert evaluate_fundamentals(make_profile(), make_ratios(debt_equity=3.1), make_income()) is None


def test_passes_debt_equity_at_boundary():
    result = evaluate_fundamentals(make_profile(), make_ratios(debt_equity=3.0), make_income())
    assert result is not None


def test_discards_negative_eps():
    assert evaluate_fundamentals(make_profile(), make_ratios(), make_income(eps=-1.0)) is None


def test_discards_zero_eps():
    assert evaluate_fundamentals(make_profile(), make_ratios(), make_income(eps=0.0)) is None


def test_passes_with_missing_optional_fields():
    result = evaluate_fundamentals(
        {"marketCap": 5_000_000_000},
        {},
        {},
    )
    assert result is not None
    assert result.pe_ratio is None
    assert result.debt_to_equity is None
    assert result.eps is None


def test_revenue_growth_from_income():
    result = evaluate_fundamentals(make_profile(), make_ratios(), make_income())
    assert result.revenue_growth == 0.08
