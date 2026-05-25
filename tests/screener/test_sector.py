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


@patch("screener.sector.get_etf_holdings")
@patch("screener.sector.score_sectors")
def test_get_sector_universe_uses_live_holdings(mock_score, mock_holdings):
    mock_score.return_value = [("Technology", 2.0), ("Energy", 1.5)]
    mock_holdings.return_value = ["AAPL", "MSFT", "NVDA"]
    tickers = get_sector_universe(top_n=2)
    assert tickers == ["AAPL", "MSFT", "NVDA"]  # deduped across both sectors


@patch("screener.sector.get_etf_holdings")
@patch("screener.sector.score_sectors")
def test_get_sector_universe_falls_back_on_empty(mock_score, mock_holdings):
    mock_score.return_value = [("Technology", 2.0)]
    mock_holdings.return_value = []
    tickers = get_sector_universe(top_n=1)
    assert all(t in tickers for t in SECTOR_UNIVERSE["Technology"])


@patch("screener.sector.get_etf_holdings")
@patch("screener.sector.score_sectors")
def test_get_sector_universe_falls_back_on_exception(mock_score, mock_holdings):
    mock_score.return_value = [("Technology", 2.0)]
    mock_holdings.side_effect = Exception("API error")
    tickers = get_sector_universe(top_n=1)
    assert all(t in tickers for t in SECTOR_UNIVERSE["Technology"])


@patch("screener.sector.get_etf_holdings")
def test_get_sector_universe_all_sectors(mock_holdings):
    mock_holdings.return_value = ["AAPL", "MSFT"]
    tickers = get_sector_universe(top_n=None)
    assert mock_holdings.call_count == len(SECTOR_ETFS)


@patch("screener.sector.get_etf_holdings")
def test_get_sector_universe_no_duplicates(mock_holdings):
    mock_holdings.return_value = ["AAPL"]  # same ticker across all sectors
    tickers = get_sector_universe(top_n=None)
    assert tickers.count("AAPL") == 1


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
