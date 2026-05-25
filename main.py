import argparse
from datetime import date, datetime
from zoneinfo import ZoneInfo

from apscheduler.schedulers.blocking import BlockingScheduler

from db.database import Base, engine, SessionLocal
from db import models  # noqa: F401
from db.models import Watchlist
from models.stock import FundamentalsData, Pick, ScreenerResult
from screener.screener import run_screener
from screener.backtest import run_backtest, BacktestResult
from screener.visualize import save_backtest_chart

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
        print("[screener] Watchlist is empty. Add tickers with: python3 main.py --watch TICKER")
        return
    result = run_screener(tickers)
    _print_result(result, title="Daily Screen")
    from clients.claude_client import generate_report
    from clients.email_client import send_report
    structured = _build_screener_data(result)
    report = generate_report(structured, report_type="live")
    send_report(
        subject=f"Daily Screen — {datetime.now(ET).strftime('%b %d %I:%M %p ET')}",
        body=report,
        filename=f"screen_{date.today()}.txt",
        raw_data=structured,
    )


def run_research() -> None:
    from clients.fmp import get_profile, get_ratios, get_income_statement
    from screener.sector import score_sectors, get_sector_universe
    from screener.fundamentals import evaluate_fundamentals

    ranked = score_sectors()
    top_sectors = [s for s, _ in ranked[:3]]
    print("\n  Sector Scores (selecting top 3):")
    for sector, score in ranked:
        mark = " ←" if sector in top_sectors else ""
        print(f"    {sector:<25} {score:+.2f}{mark}")

    universe = get_sector_universe(top_n=3)
    result = run_screener(universe)
    _print_result(result, title="Weekend Research — Sector Scan")

    picks_found = {p.ticker for p in result.picks}
    watchlist = set(_get_tickers())
    candidates = []
    for ticker in universe:
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

    from clients.claude_client import generate_report
    from clients.email_client import send_report
    structured = _build_screener_data(result, ranked=ranked, candidates=candidates)
    report = generate_report(structured, report_type="research")
    send_report(
        subject=f"Weekend Research — {date.today()}",
        body=report,
        filename=f"research_{date.today()}.txt",
        raw_data=structured,
    )


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


def run_backtest_cmd(tickers: list[str]) -> list[BacktestResult]:
    if tickers == ["SECTORS"]:
        from screener.sector import get_sector_universe
        print("Fetching sector universe...")
        tickers = get_sector_universe(top_n=None)
        print(f"Found {len(tickers)} stocks across all sectors.")
    elif not tickers:
        tickers = _get_tickers()

    if not tickers:
        print("No tickers specified and watchlist is empty.")
        return []

    large_run = len(tickers) > 20

    print("\n" + "═" * 60)
    print(f"  Backtest — {date.today()}  ({len(tickers)} ticker{'s' if len(tickers) != 1 else ''})")
    print("═" * 60)

    if large_run:
        from concurrent.futures import ThreadPoolExecutor, as_completed
        from tqdm import tqdm
        results: list[BacktestResult] = []
        with ThreadPoolExecutor(max_workers=8) as executor:
            futures = {executor.submit(run_backtest, t): t for t in tickers}
            with tqdm(total=len(tickers), desc="Backtesting", unit="ticker") as pbar:
                for future in as_completed(futures):
                    results.append(future.result())
                    pbar.update(1)
        _print_backtest_summary(results)
    else:
        results = []
        for ticker in tickers:
            result = run_backtest(ticker)
            results.append(result)
            _print_backtest_result(result)
        if len(results) > 1:
            _print_backtest_aggregate(results)

    return results


def _print_backtest_result(result: BacktestResult) -> None:
    n = result.total_trades
    if n == 0:
        print(f"  {result.ticker:<6}  No trades generated.")
        return
    wins = sum(1 for t in result.trades if t.pnl_pct > 0)
    print(f"\n  {result.ticker}  —  {n} trade{'s' if n != 1 else ''}")
    print(f"  Hit rate:   {result.hit_rate * 100:.1f}%  ({wins}/{n})")
    print(f"  Avg return: {result.avg_return_pct * 100:+.1f}%")
    print(f"  Avg hold:   {result.avg_hold_days:.0f} days")
    best = max(result.trades, key=lambda t: t.pnl_pct)
    worst = min(result.trades, key=lambda t: t.pnl_pct)
    print(f"  Best:       {best.pnl_pct * 100:+.1f}%  ({best.entry_date} → {best.exit_date})")
    print(f"  Worst:      {worst.pnl_pct * 100:+.1f}%  ({worst.entry_date} → {worst.exit_date})")


def _print_backtest_aggregate(results: list[BacktestResult]) -> None:
    all_trades = [t for r in results for t in r.trades]
    if not all_trades:
        return
    hit_rate = sum(1 for t in all_trades if t.pnl_pct > 0) / len(all_trades)
    avg_return = sum(t.pnl_pct for t in all_trades) / len(all_trades)
    print("\n" + "─" * 60)
    print(f"  AGGREGATE  ({len(results)} tickers, {len(all_trades)} trades)")
    print(f"  Hit rate:   {hit_rate * 100:.1f}%")
    print(f"  Avg return: {avg_return * 100:+.1f}%")
    print("═" * 60 + "\n")


def _print_backtest_summary(results: list[BacktestResult]) -> None:
    """Aggregate view for large runs (NYSE-scale)."""
    active = [r for r in results if r.trades]
    all_trades = [t for r in active for t in r.trades]

    if not all_trades:
        print("  No trades generated across any ticker.")
        print("═" * 60 + "\n")
        return

    hit_rate = sum(1 for t in all_trades if t.pnl_pct > 0) / len(all_trades)
    avg_return = sum(t.pnl_pct for t in all_trades) / len(all_trades)

    print(f"  Tickers with trades: {len(active)}/{len(results)}")
    print(f"  Total trades:        {len(all_trades)}")
    print(f"  Hit rate:            {hit_rate * 100:.1f}%")
    print(f"  Avg LEAP return:     {avg_return * 100:+.1f}%")
    print("─" * 60)

    ranked = sorted(active, key=lambda r: r.avg_return_pct, reverse=True)
    print("  Top 10 performers:")
    for r in ranked[:10]:
        wins = sum(1 for t in r.trades if t.pnl_pct > 0)
        print(f"    {r.ticker:<6}  {r.avg_return_pct * 100:+.1f}%  "
              f"({r.total_trades} trades, {wins}/{r.total_trades} wins)")
    print("  Bottom 10 performers:")
    for r in ranked[-10:]:
        wins = sum(1 for t in r.trades if t.pnl_pct > 0)
        print(f"    {r.ticker:<6}  {r.avg_return_pct * 100:+.1f}%  "
              f"({r.total_trades} trades, {wins}/{r.total_trades} wins)")
    print("═" * 60 + "\n")


def _build_screener_data(
    result: ScreenerResult,
    ranked: list[tuple[str, float]] | None = None,
    candidates: list[tuple[str, FundamentalsData]] | None = None,
) -> str:
    lines = [
        f"DATE: {result.run_date}",
        "MACRO:",
        f"  VIX: {result.macro.vix:.1f}",
        f"  SPY: ${result.macro.spy_price:.2f} | RSI: {result.macro.spy_rsi:.1f} | Trend: {result.macro.spy_trend}",
    ]
    if result.macro.put_call_ratio:
        lines.append(f"  Put/Call: {result.macro.put_call_ratio:.2f}")
    lines.append(f"  Signal: {result.macro.signal}")

    if ranked:
        lines += ["", "SECTOR SCORES:"]
        for sector, score in ranked:
            lines.append(f"  {sector:<25} {score:+.2f}")

    lines += ["", f"PICKS: {len(result.picks)}"]
    for pick in result.picks:
        t, o, s, f = pick.technicals, pick.options_data, pick.sentiment, pick.fundamentals
        lines += ["---", f"TICKER: {pick.ticker}", f"CONVICTION: {pick.conviction}/5",
                  f"SECTOR: {f.sector or 'N/A'}", f"MARKET_CAP: ${f.market_cap / 1e9:.1f}B"]
        if f.pe_ratio:
            lines.append(f"PE_RATIO: {f.pe_ratio:.1f}")
        if f.debt_to_equity:
            lines.append(f"DEBT_EQUITY: {f.debt_to_equity:.2f}")
        if f.eps:
            lines.append(f"EPS: {f.eps:.2f}")
        lines += [
            f"RSI_DAILY: {t.rsi_daily:.1f}", f"RSI_WEEKLY: {t.rsi_weekly:.1f}",
            f"MACD: {t.macd_signal}", f"AT_SUPPORT: {t.at_support}", f"PRICE: ${t.price:.2f}",
            f"IV_RANK: {o.iv_rank:.1f}", f"STRIKE: ${o.strike:.0f}", f"EXPIRATION: {o.expiration}",
            f"OPEN_INTEREST: {o.open_interest}",
            f"SENTIMENT: {s.sentiment_signal} (Massive: {s.massive_sentiment} | FinBERT: {s.finbert_sentiment} {s.finbert_confidence:.2f})",
            "HEADLINES:",
        ]
        for h in pick.news_headlines[:3]:
            lines.append(f"  - {h}")

    if candidates:
        lines += ["", "FUNDAMENTAL CANDIDATES:"]
        for ticker, fund in candidates[:10]:
            pe = f" PE={fund.pe_ratio:.1f}" if fund.pe_ratio else ""
            eps = f" EPS={fund.eps:.2f}" if fund.eps else ""
            lines.append(f"  {ticker:<6} Cap=${fund.market_cap / 1e9:.0f}B{pe}{eps}")

    return "\n".join(lines)


def _build_backtest_data(results: list[BacktestResult]) -> str:
    active = [r for r in results if r.trades]
    all_trades = [t for r in active for t in r.trades]
    lines = [
        f"DATE: {date.today()}",
        f"TICKERS_TESTED: {len(results)}",
        f"TICKERS_WITH_TRADES: {len(active)}",
        f"TOTAL_TRADES: {len(all_trades)}",
    ]
    if all_trades:
        hit_rate = sum(1 for t in all_trades if t.pnl_pct > 0) / len(all_trades)
        avg_return = sum(t.pnl_pct for t in all_trades) / len(all_trades)
        lines += [f"HIT_RATE: {hit_rate * 100:.1f}%", f"AVG_RETURN: {avg_return * 100:+.1f}%",
                  "", "TOP_PERFORMERS:"]
        ranked = sorted(active, key=lambda r: r.avg_return_pct, reverse=True)
        for r in ranked[:10]:
            wins = sum(1 for t in r.trades if t.pnl_pct > 0)
            lines.append(f"  {r.ticker:<6} avg={r.avg_return_pct * 100:+.1f}% wins={wins}/{r.total_trades}")
        lines.append("BOTTOM_PERFORMERS:")
        for r in ranked[-10:]:
            wins = sum(1 for t in r.trades if t.pnl_pct > 0)
            lines.append(f"  {r.ticker:<6} avg={r.avg_return_pct * 100:+.1f}% wins={wins}/{r.total_trades}")
    return "\n".join(lines)


def init_db() -> None:
    Base.metadata.create_all(bind=engine)


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Trading screener")
    group = parser.add_mutually_exclusive_group()
    group.add_argument("--now", action="store_true", help="Run live screener immediately")
    group.add_argument("--research", action="store_true", help="Run weekend research immediately")
    group.add_argument("--backtest", nargs="*", metavar="TICKER", help="Run backtest (defaults to watchlist)")
    group.add_argument("--watch", nargs="?", const="", metavar="TICKER",
                       help="Manage watchlist: --watch (list), --watch AAPL (add), --watch -AAPL (remove)")
    args = parser.parse_args()

    init_db()

    if args.now:
        run_live()
    elif args.research:
        run_research()
    elif args.backtest is not None:
        results = run_backtest_cmd(args.backtest)
        if results:
            from clients.claude_client import generate_report
            from clients.email_client import send_report
            structured = _build_backtest_data(results)
            report = generate_report(structured, report_type="backtest")
            chart_path = save_backtest_chart(results)
            print(f"  Chart saved: {chart_path}")
            send_report(
                subject=f"Backtest Report — {date.today()}",
                body=report,
                filename=f"backtest_{date.today()}.txt",
                raw_data=structured,
                chart_path=chart_path,
            )
    elif args.watch is not None:
        if not args.watch:
            _list_watchlist()
        elif args.watch.startswith("-"):
            _remove_ticker(args.watch[1:])
        else:
            _add_ticker(args.watch)
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
