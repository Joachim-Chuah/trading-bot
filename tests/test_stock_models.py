import pytest
from datetime import date
from pydantic import ValidationError
from models.stock import (
    FundamentalsData,
    TechnicalsData,
    OptionsData,
    MacroSnapshot,
    Pick,
    ScreenerResult,
)


def make_fundamentals() -> FundamentalsData:
    return FundamentalsData(market_cap=3_100_000_000_000, pe_ratio=28.5, sector="Technology")


def make_technicals() -> TechnicalsData:
    return TechnicalsData(rsi_daily=32.0, rsi_weekly=38.0, macd_signal="bullish", at_support=True, price=194.5)


def make_options() -> OptionsData:
    return OptionsData(
        iv_rank=18.0,
        open_interest=5000,
        bid_ask_spread=0.05,
        strike=195.0,
        expiration=date(2027, 1, 15),
        contract_symbol="AAPL270115C00195000",
    )


def make_macro() -> MacroSnapshot:
    return MacroSnapshot(vix=22.4, put_call_ratio=0.94, signal="neutral", spy_price=520.0, spy_rsi=58.0, spy_trend="bullish")


def make_pick(ticker: str = "AAPL", conviction: int = 4) -> Pick:
    return Pick(
        ticker=ticker,
        conviction=conviction,
        news_sentiment="bullish",
        news_headlines=["Earnings beat expectations", "New product cycle announced"],
        fundamentals=make_fundamentals(),
        options_data=make_options(),
        technicals=make_technicals(),
    )


def test_fundamentals_data_valid():
    f = make_fundamentals()
    assert f.market_cap == 3_100_000_000_000
    assert f.sector == "Technology"


def test_fundamentals_data_optional_fields_default_none():
    f = FundamentalsData(market_cap=1_000_000_000)
    assert f.pe_ratio is None
    assert f.revenue_growth is None
    assert f.debt_to_equity is None
    assert f.eps is None
    assert f.sector is None


def test_technicals_data_valid():
    t = make_technicals()
    assert t.rsi_daily == 32.0
    assert t.at_support is True
    assert t.macd_signal == "bullish"


def test_technicals_data_invalid_macd_signal():
    with pytest.raises(ValidationError):
        TechnicalsData(rsi_daily=32.0, rsi_weekly=38.0, macd_signal="strong_buy", at_support=True, price=194.5)


def test_options_data_valid():
    o = make_options()
    assert o.iv_rank == 18.0
    assert o.strike == 195.0
    assert o.expiration == date(2027, 1, 15)


def test_macro_snapshot_valid():
    m = make_macro()
    assert m.signal == "neutral"
    assert m.spy_trend == "bullish"


def test_macro_snapshot_invalid_signal():
    with pytest.raises(ValidationError):
        MacroSnapshot(vix=22.4, put_call_ratio=0.94, signal="unknown", spy_price=520.0, spy_rsi=58.0, spy_trend="bullish")


def test_pick_valid():
    p = make_pick()
    assert p.ticker == "AAPL"
    assert p.conviction == 4
    assert p.news_sentiment == "bullish"
    assert len(p.news_headlines) == 2


def test_pick_conviction_boundary_low():
    p = make_pick(conviction=1)
    assert p.conviction == 1


def test_pick_conviction_boundary_high():
    p = make_pick(conviction=5)
    assert p.conviction == 5


def test_pick_conviction_below_minimum():
    with pytest.raises(ValidationError):
        make_pick(conviction=0)


def test_pick_conviction_above_maximum():
    with pytest.raises(ValidationError):
        make_pick(conviction=6)


def test_pick_invalid_news_sentiment():
    with pytest.raises(ValidationError):
        Pick(
            ticker="AAPL",
            conviction=4,
            news_sentiment="very_bullish",
            news_headlines=[],
            fundamentals=make_fundamentals(),
            options_data=make_options(),
            technicals=make_technicals(),
        )


def test_screener_result_with_picks():
    result = ScreenerResult(
        run_date=date.today(),
        macro=make_macro(),
        picks=[make_pick("AAPL"), make_pick("NVDA", conviction=3)],
        spy_fallback=False,
    )
    assert len(result.picks) == 2
    assert result.spy_fallback is False


def test_screener_result_zero_picks_valid():
    result = ScreenerResult(run_date=date.today(), macro=make_macro(), picks=[], spy_fallback=False)
    assert result.picks == []


def test_screener_result_spy_fallback():
    macro = MacroSnapshot(vix=38.1, put_call_ratio=1.3, signal="hostile", spy_price=510.0, spy_rsi=62.0, spy_trend="neutral")
    result = ScreenerResult(run_date=date.today(), macro=macro, picks=[], spy_fallback=True)
    assert result.spy_fallback is True
    assert result.macro.signal == "hostile"
    assert result.picks == []
