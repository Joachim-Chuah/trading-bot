from datetime import date

from screener.backtest import BacktestResult


def save_backtest_chart(results: list[BacktestResult]) -> str:
    import matplotlib
    matplotlib.use("Agg")  # non-interactive backend — no display required
    import matplotlib.pyplot as plt

    active = [r for r in results if r.trades]
    all_trades = sorted(
        [t for r in active for t in r.trades],
        key=lambda t: t.exit_date,
    )

    fig, axes = plt.subplots(2, 1, figsize=(12, 8))
    fig.suptitle(f"Backtest Report — {date.today()}", fontsize=14, fontweight="bold")

    ax1 = axes[0]
    if all_trades:
        dates = [t.exit_date for t in all_trades]
        cumulative: list[float] = []
        running = 0.0
        for t in all_trades:
            running += t.pnl_pct * 100
            cumulative.append(running)
        ax1.plot(dates, cumulative, color="steelblue", linewidth=1.5)
        ax1.axhline(y=0, color="gray", linestyle="--", linewidth=0.8)
        ax1.fill_between(dates, cumulative, 0, where=[c >= 0 for c in cumulative], alpha=0.15, color="green")
        ax1.fill_between(dates, cumulative, 0, where=[c < 0 for c in cumulative], alpha=0.15, color="red")
    ax1.set_title("Aggregate Equity Curve (Cumulative P&L %)")
    ax1.set_ylabel("Cumulative Return (%)")
    ax1.grid(True, alpha=0.3)

    ax2 = axes[1]
    ranked = sorted(active, key=lambda r: r.avg_return_pct, reverse=True)
    display = ranked[:10] + ranked[-10:] if len(ranked) > 20 else ranked
    tickers_display = [r.ticker for r in display]
    returns = [r.avg_return_pct * 100 for r in display]
    colors = ["#2e7d32" if v >= 0 else "#c62828" for v in returns]
    ax2.barh(tickers_display, returns, color=colors)
    ax2.axvline(x=0, color="gray", linewidth=0.8)
    label = "Top/Bottom 10" if len(ranked) > 20 else "All Tickers"
    ax2.set_title(f"Avg Return per Ticker (%) — {label}")
    ax2.set_xlabel("Avg Return (%)")
    ax2.grid(True, axis="x", alpha=0.3)

    plt.tight_layout()
    path = f"backtest_{date.today()}.png"
    plt.savefig(path, dpi=150, bbox_inches="tight")
    plt.close()
    return path
