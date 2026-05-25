import pytest
from unittest.mock import patch
from screener.sector import score_sectors, get_sector_universe, SECTOR_ETFS, SECTOR_UNIVERSE


def make_snap(change_pct: float, day_vol: int = 1_000_000, avg_vol: int = 1_000_000) -> dict:
    return {
        "todaysChangePerc": change_pct,
        "day": {"v": day_vol},
        "min": {"av": avg_vol},
    }


@patch("screener.sector.get_snapshot")
def test_score_sectors_sorted_descending(mock_snap):
    etfs = list(SECTOR_ETFS.values())

    def side_effect(ticker):
        return make_snap(float(len(etfs) - etfs.index(ticker)))

    mock_snap.side_effect = side_effect
    ranked = score_sectors()
    scores = [s for _, s in ranked]
    assert scores == sorted(scores, reverse=True)
    assert len(ranked) == len(SECTOR_ETFS)


@patch("screener.sector.get_snapshot")
def test_score_sectors_skips_failed_etf(mock_snap):
    def side_effect(ticker):
        if ticker == "XLK":
            raise Exception("API error")
        return make_snap(1.0)

    mock_snap.side_effect = side_effect
    ranked = score_sectors()
    sector_names = [s for s, _ in ranked]
    assert "Technology" not in sector_names
    assert len(ranked) == len(SECTOR_ETFS) - 1


@patch("screener.sector.score_sectors")
def test_get_sector_universe_top_n(mock_score):
    mock_score.return_value = [
        ("Technology", 2.0), ("Energy", 1.5), ("Healthcare", 1.0), ("Financial Services", 0.5),
    ]
    tickers = get_sector_universe(top_n=2)
    assert all(t in tickers for t in SECTOR_UNIVERSE["Technology"])
    assert all(t in tickers for t in SECTOR_UNIVERSE["Energy"])
    assert not any(t in tickers for t in SECTOR_UNIVERSE["Healthcare"])


def test_get_sector_universe_all_sectors():
    tickers = get_sector_universe(top_n=None)
    assert len(tickers) == sum(len(v) for v in SECTOR_UNIVERSE.values())


def test_get_sector_universe_no_duplicates():
    tickers = get_sector_universe(top_n=None)
    assert len(tickers) == len(set(tickers))


@patch("screener.sector.get_snapshot")
def test_score_sectors_volume_boosts_score(mock_snap):
    # Sector with elevated volume should score higher than same return with flat volume
    def side_effect(ticker):
        if ticker == "XLK":
            return make_snap(1.0, day_vol=2_000_000, avg_vol=1_000_000)  # vol_ratio=2
        return make_snap(1.0, day_vol=1_000_000, avg_vol=1_000_000)  # vol_ratio=1

    mock_snap.side_effect = side_effect
    ranked = score_sectors()
    top_sector = ranked[0][0]
    assert top_sector == "Technology"
