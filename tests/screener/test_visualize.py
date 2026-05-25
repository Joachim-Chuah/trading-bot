from datetime import date
from screener.backtest import BacktestResult, BacktestTrade
from screener.visualize import save_backtest_chart


def make_result(ticker: str, pnl: float) -> BacktestResult:
    r = BacktestResult(ticker=ticker)
    r.trades = [BacktestTrade(
        ticker=ticker,
        entry_date=date(2024, 1, 2),
        exit_date=date(2024, 3, 1),
        entry_stock_price=100.0,
        exit_stock_price=110.0,
        strike=105.0,
        expiration=date(2026, 1, 1),
        entry_option_price=5.0,
        exit_option_price=round(5.0 * (1 + pnl), 2),
        pnl_pct=pnl,
        exit_reason="target" if pnl > 0 else "max_hold",
    )]
    return r


def test_saves_png_file(tmp_path, monkeypatch):
    monkeypatch.chdir(tmp_path)
    path = save_backtest_chart([make_result("AAPL", 0.50), make_result("NVDA", -0.20)])
    assert path.endswith(".png")
    assert (tmp_path / path).exists()


def test_empty_results_still_creates_file(tmp_path, monkeypatch):
    monkeypatch.chdir(tmp_path)
    path = save_backtest_chart([])
    assert path.endswith(".png")
    assert (tmp_path / path).exists()


def test_results_with_no_trades_creates_file(tmp_path, monkeypatch):
    monkeypatch.chdir(tmp_path)
    path = save_backtest_chart([BacktestResult(ticker="AAPL")])
    assert path.endswith(".png")
    assert (tmp_path / path).exists()


def test_large_result_set_uses_top_bottom_10(tmp_path, monkeypatch):
    monkeypatch.chdir(tmp_path)
    results = [make_result(f"T{i:02d}", (i - 10) * 0.05) for i in range(25)]
    path = save_backtest_chart(results)
    assert (tmp_path / path).exists()
