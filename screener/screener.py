from datetime import date, timedelta
from typing import Literal

from clients.massive import (
    get_daily_bars, get_rsi, get_macd, get_snapshot, get_news, get_options_chain,
)
from clients.fmp import get_profile, get_ratios, get_income_statement
from clients.yfinance_client import get_vix
from clients.cboe import get_put_call_ratio
from screener.macro import get_macro_snapshot
from screener.fundamentals import evaluate_fundamentals
from screener.technicals import evaluate_technicals
from screener.options import evaluate_options
from screener.sentiment import evaluate_sentiment, _load_finbert
from screener.spy_baseline import get_spy_baseline
from models.stock import MacroSnapshot, Pick, ScreenerResult, SentimentData
from db.database import SessionLocal
from db.models import ScreenerRun
from db.models import Pick as DbPick

_HISTORY_DAYS = 270


def _date_range() -> tuple[date, date]:
    today = date.today()
    return today - timedelta(days=_HISTORY_DAYS), today


def _calculate_conviction(sentiment: SentimentData, macro: MacroSnapshot) -> int:
    score = 3
    if sentiment.sentiment_signal == "bullish":
        score += 1
    elif sentiment.sentiment_signal in ("bearish", "mixed"):
        score -= 1
    if macro.signal == "favorable":
        score += 1
    return max(1, min(5, score))


def _evaluate_ticker(
    ticker: str,
    macro: MacroSnapshot,
    finbert,
    from_date: date,
    to_date: date,
) -> Pick | None:
    try:
        profile = get_profile(ticker)
        ratios = get_ratios(ticker)
        income = get_income_statement(ticker)
        fundamentals = evaluate_fundamentals(profile, ratios, income)
        if fundamentals is None:
            return None

        daily_bars = get_daily_bars(ticker, from_date, to_date)
        daily_rsi = get_rsi(ticker, timespan="day")
        weekly_rsi = get_rsi(ticker, timespan="week")
        macd = get_macd(ticker)
        snapshot = get_snapshot(ticker)
        technicals = evaluate_technicals(daily_bars, daily_rsi, weekly_rsi, macd, snapshot)
        if technicals is None:
            return None

        chain = get_options_chain(ticker)
        options_data = evaluate_options(chain, technicals.price)
        if options_data is None:
            return None

        news = get_news(ticker)
        sentiment = evaluate_sentiment(news, macro, finbert)
        conviction = _calculate_conviction(sentiment, macro)

        return Pick(
            ticker=ticker,
            conviction=conviction,
            sentiment=sentiment,
            news_headlines=[a.get("title", "") for a in news if a.get("title")],
            fundamentals=fundamentals,
            options_data=options_data,
            technicals=technicals,
        )
    except Exception as e:
        print(f"[screener] skipping {ticker}: {e}")
        return None


def _save_result(result: ScreenerResult) -> None:
    db = SessionLocal()
    try:
        run = ScreenerRun(
            run_date=result.run_date,
            spy_price=result.macro.spy_price,
            spy_rsi=result.macro.spy_rsi,
            spy_trend=result.macro.spy_trend,
            vix=result.macro.vix,
            put_call_ratio=result.macro.put_call_ratio,
            macro_signal=result.macro.signal,
            picks_count=len(result.picks),
        )
        db.add(run)
        db.flush()

        for pick in result.picks:
            db.add(DbPick(
                run_id=run.id,
                ticker=pick.ticker,
                conviction=pick.conviction,
                news_sentiment=pick.sentiment.sentiment_signal,
                news_headlines=pick.news_headlines,
                fundamentals=pick.fundamentals.model_dump(),
                options_data=pick.options_data.model_dump(),
                technicals=pick.technicals.model_dump(),
            ))
        db.commit()
    finally:
        db.close()


def run_screener(tickers: list[str]) -> ScreenerResult:
    from_date, to_date = _date_range()

    vix_df = get_vix()
    put_call = get_put_call_ratio()
    spy_snapshot = get_snapshot("SPY")
    spy_rsi = get_rsi("SPY", timespan="day")
    spy_daily_bars = get_daily_bars("SPY", from_date, to_date)
    macro = get_macro_snapshot(vix_df, put_call, spy_snapshot, spy_rsi, spy_daily_bars)

    if macro.signal == "hostile":
        result = ScreenerResult(
            run_date=date.today(),
            macro=macro,
            picks=[],
            spy_fallback=True,
        )
        _save_result(result)
        return result

    finbert = _load_finbert()
    picks = []
    for ticker in tickers:
        pick = _evaluate_ticker(ticker, macro, finbert, from_date, to_date)
        if pick:
            picks.append(pick)

    result = ScreenerResult(
        run_date=date.today(),
        macro=macro,
        picks=picks,
        spy_fallback=len(picks) == 0,
    )
    _save_result(result)
    return result
