import pytest
from datetime import date, datetime, timedelta
from db.models import ScreenerRun, Pick, Watchlist, ApiCache


def utcnow() -> datetime:
    return datetime.utcnow().replace(microsecond=0)


def test_create_screener_run(db):
    run = ScreenerRun(
        run_date=date.today(),
        spy_price=520.0,
        spy_rsi=58.0,
        spy_trend="bullish",
        vix=18.5,
        put_call_ratio=0.85,
        macro_signal="favorable",
        picks_count=0,
    )
    db.add(run)
    db.commit()
    db.refresh(run)

    assert run.id is not None
    assert run.run_date == date.today()
    assert run.macro_signal == "favorable"


def test_create_pick_linked_to_run(db):
    run = ScreenerRun(run_date=date.today(), macro_signal="favorable", picks_count=1)
    db.add(run)
    db.commit()

    pick = Pick(
        run_id=run.id,
        ticker="AAPL",
        conviction=4,
        news_sentiment="bullish",
        news_headlines=["Earnings beat expectations", "New product cycle announced"],
        fundamentals={"pe_ratio": 28.5, "market_cap": 3100000000000},
        options_data={"iv_rank": 18, "strike": 195},
        technicals={"rsi_daily": 32, "rsi_weekly": 38},
    )
    db.add(pick)
    db.commit()
    db.refresh(pick)

    assert pick.id is not None
    assert pick.ticker == "AAPL"
    assert pick.conviction == 4
    assert pick.run_id == run.id


def test_screener_run_picks_relationship(db):
    run = ScreenerRun(run_date=date.today(), macro_signal="neutral", picks_count=2)
    db.add(run)
    db.commit()

    for ticker in ["AAPL", "NVDA"]:
        db.add(Pick(run_id=run.id, ticker=ticker, conviction=3, news_sentiment="bullish"))
    db.commit()
    db.refresh(run)

    assert len(run.picks) == 2
    assert {p.ticker for p in run.picks} == {"AAPL", "NVDA"}


def test_screener_run_hostile_macro_zero_picks(db):
    run = ScreenerRun(run_date=date.today(), macro_signal="hostile", picks_count=0)
    db.add(run)
    db.commit()
    db.refresh(run)

    assert run.picks_count == 0
    assert run.picks == []


def test_create_watchlist_entry(db):
    entry = Watchlist(ticker="ZTEST", active=True, notes="Strong AI catalyst")
    db.add(entry)
    db.commit()
    db.refresh(entry)

    assert entry.id is not None
    assert entry.ticker == "ZTEST"
    assert entry.active is True


def test_watchlist_inactive_entry(db):
    entry = Watchlist(ticker="INACTIVE", active=False)
    db.add(entry)
    db.commit()
    db.refresh(entry)

    assert entry.active is False


def test_create_api_cache(db):
    expires = utcnow() + timedelta(hours=1)
    cache = ApiCache(
        cache_key="massive_news_AAPL_2026-05-21",
        data={"articles": ["headline 1", "headline 2"]},
        expires_at=expires,
    )
    db.add(cache)
    db.commit()
    db.refresh(cache)

    assert cache.id is not None
    assert cache.cache_key == "massive_news_AAPL_2026-05-21"
    assert cache.expires_at > utcnow()


def test_api_cache_expired_entry(db):
    expired = utcnow() - timedelta(hours=1)
    cache = ApiCache(
        cache_key="expired_key",
        data={},
        expires_at=expired,
    )
    db.add(cache)
    db.commit()
    db.refresh(cache)

    assert cache.expires_at < utcnow()


def test_pick_conviction_boundary_values(db):
    run = ScreenerRun(run_date=date.today(), macro_signal="favorable", picks_count=2)
    db.add(run)
    db.commit()

    low = Pick(run_id=run.id, ticker="LOW", conviction=1, news_sentiment="neutral")
    high = Pick(run_id=run.id, ticker="HIGH", conviction=5, news_sentiment="bullish")
    db.add_all([low, high])
    db.commit()

    assert low.conviction == 1
    assert high.conviction == 5
