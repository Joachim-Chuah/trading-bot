import pytest
import pandas as pd
from datetime import date
from unittest.mock import patch, MagicMock, call
from models.stock import (
    FundamentalsData, TechnicalsData, OptionsData, SentimentData, MacroSnapshot, Pick, ScreenerResult,
)
from screener.screener import run_screener, _calculate_conviction, _evaluate_ticker, _save_result


def make_macro(signal: str = "favorable") -> MacroSnapshot:
    return MacroSnapshot(
        vix=16.0, put_call_ratio=0.85, signal=signal,
        spy_price=520.0, spy_rsi=58.0, spy_trend="bullish",
    )


def make_fundamentals() -> FundamentalsData:
    return FundamentalsData(market_cap=3_000_000_000_000, pe_ratio=28.0, sector="Technology", eps=6.5)


def make_technicals() -> TechnicalsData:
    return TechnicalsData(rsi_daily=32.0, rsi_weekly=38.0, macd_signal="bullish", at_support=True, price=194.5)


def make_options() -> OptionsData:
    return OptionsData(
        iv_rank=18.0, open_interest=500, bid_ask_spread=0.05,
        strike=195.0, expiration=date(2027, 1, 15), contract_symbol="AAPL270115C00195000",
    )


def make_sentiment(signal: str = "bullish") -> SentimentData:
    return SentimentData(
        massive_sentiment="bullish", finbert_sentiment="bullish",
        finbert_confidence=0.91, sentiment_signal=signal,
    )


def mock_vix() -> pd.DataFrame:
    return pd.DataFrame({"Close": [16.0]})


# --- _calculate_conviction ---

def test_conviction_bullish_favorable():
    assert _calculate_conviction(make_sentiment("bullish"), make_macro("favorable")) == 5


def test_conviction_bullish_neutral():
    assert _calculate_conviction(make_sentiment("bullish"), make_macro("neutral")) == 4


def test_conviction_neutral_favorable():
    assert _calculate_conviction(make_sentiment("neutral"), make_macro("favorable")) == 4


def test_conviction_neutral_neutral():
    assert _calculate_conviction(make_sentiment("neutral"), make_macro("neutral")) == 3


def test_conviction_mixed_neutral():
    assert _calculate_conviction(make_sentiment("mixed"), make_macro("neutral")) == 2


def test_conviction_bearish_favorable():
    assert _calculate_conviction(make_sentiment("bearish"), make_macro("favorable")) == 3


def test_conviction_clamped_min():
    assert _calculate_conviction(make_sentiment("bearish"), make_macro("neutral")) >= 1


def test_conviction_clamped_max():
    assert _calculate_conviction(make_sentiment("bullish"), make_macro("favorable")) <= 5


# --- run_screener kill switch ---

@patch("screener.screener._save_result")
@patch("screener.screener.get_macro_snapshot", return_value=None)
@patch("screener.screener.get_daily_bars", return_value=[])
@patch("screener.screener.get_rsi", return_value=[{"value": 55.0}])
@patch("screener.screener.get_snapshot", return_value={"day": {"c": 520.0}})
@patch("screener.screener.get_put_call_ratio", return_value=1.3)
@patch("screener.screener.get_vix", return_value=mock_vix())
def test_kill_switch_aborts_pipeline(
    mock_vix_, mock_pc, mock_snap, mock_rsi, mock_bars, mock_macro, mock_save
):
    hostile_macro = make_macro("hostile")
    mock_macro.return_value = hostile_macro

    result = run_screener(["AAPL"])

    assert result.spy_fallback is True
    assert result.picks == []
    assert result.macro.signal == "hostile"
    mock_save.assert_called_once()


# --- run_screener full pipeline ---

@patch("screener.screener._save_result")
@patch("screener.screener._load_finbert")
@patch("screener.screener.evaluate_sentiment")
@patch("screener.screener.get_news", return_value=[{"title": "Apple beats earnings", "insights": [{"sentiment": "positive"}]}])
@patch("screener.screener.evaluate_options")
@patch("screener.screener.get_options_chain", return_value=[])
@patch("screener.screener.evaluate_technicals")
@patch("screener.screener.get_macd", return_value=[{"histogram": 0.3}])
@patch("screener.screener.get_rsi", return_value=[{"value": 32.0}])
@patch("screener.screener.get_daily_bars", return_value=[])
@patch("screener.screener.get_snapshot", return_value={"day": {"c": 194.5}})
@patch("screener.screener.evaluate_fundamentals")
@patch("screener.screener.get_income_statement", return_value={})
@patch("screener.screener.get_ratios", return_value={})
@patch("screener.screener.get_profile", return_value={})
@patch("screener.screener.get_macro_snapshot")
@patch("screener.screener.get_put_call_ratio", return_value=0.85)
@patch("screener.screener.get_vix", return_value=mock_vix())
def test_full_pipeline_produces_pick(
    mock_vix_, mock_pc, mock_macro, mock_profile, mock_ratios, mock_income,
    mock_eval_fund, mock_snap, mock_bars, mock_rsi, mock_macd, mock_eval_tech,
    mock_chain, mock_eval_opts, mock_news, mock_eval_sent, mock_finbert, mock_save
):
    mock_macro.return_value = make_macro("favorable")
    mock_eval_fund.return_value = make_fundamentals()
    mock_eval_tech.return_value = make_technicals()
    mock_eval_opts.return_value = make_options()
    mock_eval_sent.return_value = make_sentiment("bullish")
    mock_finbert.return_value = MagicMock()

    result = run_screener(["AAPL"])

    assert len(result.picks) == 1
    assert result.picks[0].ticker == "AAPL"
    assert result.picks[0].conviction == 5
    assert result.spy_fallback is False
    mock_save.assert_called_once()


@patch("screener.screener._save_result")
@patch("screener.screener._load_finbert", return_value=MagicMock())
@patch("screener.screener.evaluate_fundamentals", return_value=None)
@patch("screener.screener.get_income_statement", return_value={})
@patch("screener.screener.get_ratios", return_value={})
@patch("screener.screener.get_profile", return_value={})
@patch("screener.screener.get_macro_snapshot")
@patch("screener.screener.get_daily_bars", return_value=[])
@patch("screener.screener.get_rsi", return_value=[{"value": 55.0}])
@patch("screener.screener.get_snapshot", return_value={"day": {"c": 520.0}})
@patch("screener.screener.get_put_call_ratio", return_value=0.85)
@patch("screener.screener.get_vix", return_value=mock_vix())
def test_fundamentals_gate_discards_ticker(
    mock_vix_, mock_pc, mock_snap, mock_rsi, mock_bars, mock_macro,
    mock_profile, mock_ratios, mock_income, mock_fund, mock_finbert, mock_save
):
    mock_macro.return_value = make_macro("favorable")

    result = run_screener(["AAPL"])

    assert result.picks == []
    assert result.spy_fallback is True


@patch("screener.screener._save_result")
@patch("screener.screener._load_finbert", return_value=MagicMock())
@patch("screener.screener.evaluate_fundamentals", return_value=make_fundamentals())
@patch("screener.screener.evaluate_technicals", return_value=None)
@patch("screener.screener.get_macd", return_value=[])
@patch("screener.screener.get_rsi", return_value=[{"value": 32.0}])
@patch("screener.screener.get_daily_bars", return_value=[])
@patch("screener.screener.get_snapshot", return_value={"day": {"c": 194.5}})
@patch("screener.screener.get_income_statement", return_value={})
@patch("screener.screener.get_ratios", return_value={})
@patch("screener.screener.get_profile", return_value={})
@patch("screener.screener.get_macro_snapshot")
@patch("screener.screener.get_put_call_ratio", return_value=0.85)
@patch("screener.screener.get_vix", return_value=mock_vix())
def test_technicals_gate_discards_ticker(
    mock_vix_, mock_pc, mock_macro, mock_profile, mock_ratios, mock_income,
    mock_snap, mock_bars, mock_rsi, mock_macd, mock_eval_tech, mock_fund,
    mock_finbert, mock_save
):
    mock_macro.return_value = make_macro("favorable")

    result = run_screener(["AAPL"])
    assert result.picks == []


@patch("screener.screener._save_result")
@patch("screener.screener._load_finbert", return_value=MagicMock())
@patch("screener.screener.evaluate_sentiment", return_value=make_sentiment())
@patch("screener.screener.get_news", return_value=[])
@patch("screener.screener.evaluate_options", return_value=None)
@patch("screener.screener.get_options_chain", return_value=[])
@patch("screener.screener.evaluate_technicals", return_value=make_technicals())
@patch("screener.screener.evaluate_fundamentals", return_value=make_fundamentals())
@patch("screener.screener.get_macd", return_value=[])
@patch("screener.screener.get_rsi", return_value=[{"value": 32.0}])
@patch("screener.screener.get_daily_bars", return_value=[])
@patch("screener.screener.get_snapshot", return_value={"day": {"c": 194.5}})
@patch("screener.screener.get_income_statement", return_value={})
@patch("screener.screener.get_ratios", return_value={})
@patch("screener.screener.get_profile", return_value={})
@patch("screener.screener.get_macro_snapshot")
@patch("screener.screener.get_put_call_ratio", return_value=0.85)
@patch("screener.screener.get_vix", return_value=mock_vix())
def test_options_gate_discards_ticker(
    mock_vix_, mock_pc, mock_macro, mock_profile, mock_ratios, mock_income,
    mock_snap, mock_bars, mock_rsi, mock_macd, mock_fund, mock_tech,
    mock_chain, mock_opts, mock_news, mock_sent, mock_finbert, mock_save
):
    mock_macro.return_value = make_macro("favorable")
    result = run_screener(["AAPL"])
    assert result.picks == []


@patch("screener.screener._save_result")
@patch("screener.screener._load_finbert", return_value=MagicMock())
@patch("screener.screener.evaluate_sentiment", return_value=make_sentiment())
@patch("screener.screener.get_news", return_value=[])
@patch("screener.screener.evaluate_options", return_value=make_options())
@patch("screener.screener.get_options_chain", return_value=[])
@patch("screener.screener.evaluate_technicals", return_value=make_technicals())
@patch("screener.screener.evaluate_fundamentals", return_value=make_fundamentals())
@patch("screener.screener.get_macd", return_value=[])
@patch("screener.screener.get_rsi", return_value=[{"value": 32.0}])
@patch("screener.screener.get_daily_bars", return_value=[])
@patch("screener.screener.get_snapshot", return_value={"day": {"c": 194.5}})
@patch("screener.screener.get_income_statement", return_value={})
@patch("screener.screener.get_ratios", return_value={})
@patch("screener.screener.get_profile", return_value={})
@patch("screener.screener.get_macro_snapshot")
@patch("screener.screener.get_put_call_ratio", return_value=0.85)
@patch("screener.screener.get_vix", return_value=mock_vix())
def test_ticker_error_skipped_gracefully(
    mock_vix_, mock_pc, mock_macro, mock_profile, mock_ratios, mock_income,
    mock_snap, mock_bars, mock_rsi, mock_macd, mock_fund, mock_tech,
    mock_chain, mock_opts, mock_news, mock_sent, mock_finbert, mock_save
):
    mock_macro.return_value = make_macro("favorable")
    mock_fund.side_effect = Exception("API timeout")

    result = run_screener(["AAPL", "NVDA"])
    assert result.picks == []


# --- _save_result ---

@patch("screener.screener.SessionLocal")
def test_save_result_persists_run_and_picks(mock_session_cls):
    mock_db = MagicMock()
    mock_session_cls.return_value = mock_db
    mock_db.flush.side_effect = lambda: setattr(mock_db.add.call_args_list[0][0][0], "id", 1)

    result = ScreenerResult(
        run_date=date(2026, 1, 15),
        macro=make_macro("favorable"),
        picks=[
            Pick(
                ticker="AAPL",
                conviction=5,
                sentiment=make_sentiment("bullish"),
                news_headlines=["Apple beats earnings"],
                fundamentals=make_fundamentals(),
                options_data=make_options(),
                technicals=make_technicals(),
            )
        ],
        spy_fallback=False,
    )

    _save_result(result)

    assert mock_db.add.call_count == 2
    mock_db.commit.assert_called_once()
    mock_db.close.assert_called_once()


@patch("screener.screener.SessionLocal")
def test_save_result_no_picks(mock_session_cls):
    mock_db = MagicMock()
    mock_session_cls.return_value = mock_db

    result = ScreenerResult(
        run_date=date(2026, 1, 15),
        macro=make_macro("hostile"),
        picks=[],
        spy_fallback=True,
    )

    _save_result(result)

    assert mock_db.add.call_count == 1
    mock_db.commit.assert_called_once()
    mock_db.close.assert_called_once()
