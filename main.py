import argparse
from datetime import datetime
from zoneinfo import ZoneInfo

from apscheduler.schedulers.blocking import BlockingScheduler

from db.database import Base, engine, SessionLocal
from db import models  # noqa: F401
from db.models import Watchlist
from models.stock import Pick, ScreenerResult
from screener.screener import run_screener
from screener.universe import UNIVERSE

ET = ZoneInfo("America/New_York")


def _get_tickers() -> list[str]:
    db = SessionLocal()
    try:
        rows = db.query(Watchlist).filter(Watchlist.active == True).all()
        return [r.ticker for r in rows]
    finally:
        db.close()


def _print_result(result: ScreenerResult, title: str = "Daily Screen") -> None:
    now = datetime.now(ET).strftime("%I:%M %p ET")
    print("\n" + "═" * 60)
    print(f"  {title} — {result.run_date}  {now}")
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
            _print_pick(pick)

    count = len(result.picks)
    label = f"{count} pick{'s' if count != 1 else ''}" if count else "0 picks"
    print(f"  {label}. Run saved.")
    print("═" * 60 + "\n")


def _print_pick(pick: Pick) -> None:
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


def run_live() -> None:
    tickers = _get_tickers()
    if not tickers:
        print("[screener] Watchlist is empty. Add tickers with: python3 main.py --add TICKER")
        return
    result = run_screener(tickers)
    _print_result(result, title="Daily Screen")


def run_research() -> None:
    from clients.fmp import get_profile, get_ratios, get_income_statement
    from screener.fundamentals import evaluate_fundamentals

    watchlist = set(_get_tickers())
    result = run_screener(UNIVERSE)
    _print_result(result, title="Weekend Research — Universe Scan")

    # Surface fundamental candidates: passed fundamentals but didn't make it to a pick
    # These are worth adding to your watchlist and waiting for the right entry
    picks_found = {p.ticker for p in result.picks}
    candidates = []
    for ticker in UNIVERSE:
        if ticker in picks_found or ticker in watchlist:
            continue
        try:
            profile = get_profile(ticker)
            ratios = get_ratios(ticker)
            income = get_income_statement(ticker)
            fund = evaluate_fundamentals(profile, ratios, income)
            if fund:
                candidates.append((ticker, fund))
        except Exception:
            pass

    if candidates:
        print("─" * 60)
        print("  Fundamental Candidates — passed fundamentals, not yet entry-ready")
        print("  Consider adding to watchlist for daily monitoring.")
        print("─" * 60)
        for ticker, fund in candidates[:10]:
            pe = f"P/E: {fund.pe_ratio:.1f} | " if fund.pe_ratio else ""
            eps = f"EPS: ${fund.eps:.2f}" if fund.eps else ""
            print(f"  {ticker:<6}  Cap: ${fund.market_cap / 1e9:.0f}B | {pe}{eps}")
        print()


def _add_ticker(ticker: str) -> None:
    db = SessionLocal()
    try:
        existing = db.query(Watchlist).filter(Watchlist.ticker == ticker.upper()).first()
        if existing:
            if not existing.active:
                existing.active = True
                db.commit()
                print(f"Reactivated {ticker.upper()} in watchlist.")
            else:
                print(f"{ticker.upper()} is already in the watchlist.")
        else:
            db.add(Watchlist(ticker=ticker.upper(), active=True))
            db.commit()
            print(f"Added {ticker.upper()} to watchlist.")
    finally:
        db.close()


def _remove_ticker(ticker: str) -> None:
    db = SessionLocal()
    try:
        row = db.query(Watchlist).filter(Watchlist.ticker == ticker.upper()).first()
        if not row:
            print(f"{ticker.upper()} not found in watchlist.")
        else:
            row.active = False
            db.commit()
            print(f"Removed {ticker.upper()} from watchlist.")
    finally:
        db.close()


def _list_watchlist() -> None:
    db = SessionLocal()
    try:
        rows = db.query(Watchlist).filter(Watchlist.active == True).all()
        if not rows:
            print("Watchlist is empty.")
        else:
            print("Watchlist:", ", ".join(r.ticker for r in rows))
    finally:
        db.close()


def init_db() -> None:
    Base.metadata.create_all(bind=engine)


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Trading screener")
    group = parser.add_mutually_exclusive_group()
    group.add_argument("--now", action="store_true", help="Run live screener immediately")
    group.add_argument("--research", action="store_true", help="Run research mode immediately")
    group.add_argument("--add", metavar="TICKER", help="Add a ticker to the watchlist")
    group.add_argument("--remove", metavar="TICKER", help="Remove a ticker from the watchlist")
    group.add_argument("--watchlist", action="store_true", help="Show current watchlist")
    args = parser.parse_args()

    init_db()

    if args.now:
        run_live()
    elif args.research:
        run_research()
    elif args.add:
        _add_ticker(args.add)
    elif args.remove:
        _remove_ticker(args.remove)
    elif args.watchlist:
        _list_watchlist()
    else:
        scheduler = BlockingScheduler(timezone=ET)
        scheduler.add_job(run_live, "cron", day_of_week="mon-fri", hour=10, minute=30)
        scheduler.add_job(run_live, "cron", day_of_week="mon-fri", hour=14, minute=0)
        scheduler.add_job(run_research, "cron", day_of_week="sat", hour=9, minute=0)
        print("Screener running. Mon-Fri 10:30am + 2:00pm ET | Research: Sat 9:00am ET")
        try:
            scheduler.start()
        except (KeyboardInterrupt, SystemExit):
            print("Screener stopped.")
