from datetime import datetime
from zoneinfo import ZoneInfo

from apscheduler.schedulers.blocking import BlockingScheduler

from db.database import Base, engine, SessionLocal
from db import models  # noqa: F401
from db.models import Watchlist
from models.stock import ScreenerResult
from screener.screener import run_screener

ET = ZoneInfo("America/New_York")


def _get_tickers() -> list[str]:
    db = SessionLocal()
    try:
        rows = db.query(Watchlist).filter(Watchlist.active == True).all()
        return [r.ticker for r in rows]
    finally:
        db.close()


def _print_result(result: ScreenerResult) -> None:
    now = datetime.now(ET).strftime("%I:%M %p ET")
    print("\n" + "═" * 60)
    print(f"  Daily Screen — {result.run_date}  {now}")
    print("═" * 60)

    macro = result.macro
    pc = f" | Put/Call {macro.put_call_ratio:.2f}" if macro.put_call_ratio else ""
    print(f"  Macro: VIX {macro.vix:.1f}{pc} | {macro.signal.upper()}")
    print(f"  SPY: ${macro.spy_price:.2f} | RSI: {macro.spy_rsi:.1f} | {macro.spy_trend.capitalize()}")
    print("─" * 60)

    if result.spy_fallback and not result.picks:
        print("  Kill switch triggered — no picks evaluated." if macro.signal == "hostile"
              else "  No stocks passed all criteria today.")
        print("─" * 60)
    else:
        for pick in result.picks:
            stars = "★" * pick.conviction + "☆" * (5 - pick.conviction)
            print(f"\n  [LEAP]  {pick.ticker}  {stars}  ({pick.conviction}/5)")
            f = pick.fundamentals
            pe = f"P/E: {f.pe_ratio:.1f} | " if f.pe_ratio else ""
            de = f"D/E: {f.debt_to_equity:.2f} | " if f.debt_to_equity else ""
            eps = f"EPS: ${f.eps:.2f}" if f.eps else ""
            print(f"  Cap: ${f.market_cap / 1e9:.0f}B | Sector: {f.sector or 'N/A'}")
            print(f"  {pe}{de}{eps}")
            o = pick.options_data
            print(f"  IV Rank: {o.iv_rank:.1f} | Strike: ${o.strike:.0f} | Exp: {o.expiration}")
            s = pick.sentiment
            print(f"  Sentiment: {s.sentiment_signal.upper()} "
                  f"(Massive: {s.massive_sentiment} | FinBERT: {s.finbert_sentiment} "
                  f"conf: {s.finbert_confidence:.2f})")
            print("  Headlines:")
            for h in pick.news_headlines[:3]:
                print(f"    • {h}")
            print()

    count = len(result.picks)
    label = f"{count} pick{'s' if count != 1 else ''} today" if count else "0 picks today"
    print(f"  {label}. Run saved.")
    print("═" * 60 + "\n")


def run_live() -> None:
    tickers = _get_tickers()
    if not tickers:
        print("[screener] No active tickers in watchlist. Add tickers via the API to get started.")
        return
    result = run_screener(tickers)
    _print_result(result)


def run_research() -> None:
    from clients.yfinance_client import get_vix
    from clients.cboe import get_put_call_ratio
    from clients.massive import get_snapshot, get_rsi, get_daily_bars, get_news
    from screener.macro import get_macro_snapshot
    from screener.sentiment import evaluate_sentiment, _load_finbert
    from datetime import date, timedelta

    print("\n" + "═" * 60)
    print(f"  Weekend Research — {date.today()}")
    print("═" * 60)

    from_date = date.today() - timedelta(days=270)
    to_date = date.today()
    vix_df = get_vix()
    put_call = get_put_call_ratio()
    spy_snapshot = get_snapshot("SPY")
    spy_rsi = get_rsi("SPY", timespan="day")
    spy_bars = get_daily_bars("SPY", from_date, to_date)
    macro = get_macro_snapshot(vix_df, put_call, spy_snapshot, spy_rsi, spy_bars)

    pc = f" | Put/Call {macro.put_call_ratio:.2f}" if macro.put_call_ratio else ""
    print(f"  Macro: VIX {macro.vix:.1f}{pc} | {macro.signal.upper()}")
    print(f"  SPY: ${macro.spy_price:.2f} | RSI: {macro.spy_rsi:.1f} | {macro.spy_trend.capitalize()}")
    print("─" * 60)

    tickers = _get_tickers()
    if not tickers:
        print("  No active tickers in watchlist.")
        print("═" * 60 + "\n")
        return

    finbert = _load_finbert()
    for ticker in tickers:
        try:
            news = get_news(ticker, limit=5)
            if not news:
                continue
            sentiment = evaluate_sentiment(news, macro, finbert)
            print(f"\n  {ticker} — {sentiment.sentiment_signal.upper()} "
                  f"(Massive: {sentiment.massive_sentiment} | FinBERT: {sentiment.finbert_sentiment})")
            for n in news[:3]:
                print(f"    • {n.get('title', '')}")
        except Exception as e:
            print(f"  [{ticker}] error: {e}")

    print("\n" + "═" * 60 + "\n")


def init_db() -> None:
    Base.metadata.create_all(bind=engine)


if __name__ == "__main__":
    init_db()

    scheduler = BlockingScheduler(timezone=ET)
    scheduler.add_job(run_live, "cron", day_of_week="mon-fri", hour=10, minute=30)
    scheduler.add_job(run_live, "cron", day_of_week="mon-fri", hour=14, minute=0)
    scheduler.add_job(run_research, "cron", day_of_week="sat", hour=9, minute=0)

    print("Screener running. Next live runs: Mon-Fri 10:30am + 2:00pm ET | Research: Sat 9:00am ET")
    try:
        scheduler.start()
    except (KeyboardInterrupt, SystemExit):
        print("Screener stopped.")
