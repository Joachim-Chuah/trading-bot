"""One-shot test runner — initializes DB, seeds watchlist if empty, runs screener immediately."""
from main import init_db, run_live, _print_result
from db.database import SessionLocal
from db.models import Watchlist

SEED_TICKERS = ["AAPL", "NVDA", "MSFT"]


def _seed_watchlist(db) -> None:
    existing = {r.ticker for r in db.query(Watchlist).all()}
    for ticker in SEED_TICKERS:
        if ticker not in existing:
            db.add(Watchlist(ticker=ticker, active=True))
    db.commit()


if __name__ == "__main__":
    init_db()

    db = SessionLocal()
    try:
        _seed_watchlist(db)
        active = [r.ticker for r in db.query(Watchlist).filter(Watchlist.active == True).all()]
        print(f"Watchlist: {active}")
    finally:
        db.close()

    run_live()
