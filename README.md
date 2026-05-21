# Trading Screener

A terminal-based stock screener built around a LEAP options strategy, with a fallback to Cash-Secured Puts (CSPs). Designed to surface intentional, high-conviction trade ideas daily — not noise.

---

## Strategy Overview

### Primary: LEAP Options
LEAPS (Long-term Equity Anticipation Securities) are used as a capital-efficient stock replacement strategy. The screener filters for stocks that meet strict fundamental and technical criteria before evaluating their options chain for viable LEAP entries.

**LEAP Entry Criteria** *(to be finalized — see open questions)*
- [ ] Minimum delta threshold (e.g., ≥ 0.70)
- [ ] DTE range (e.g., 12–24 months out)
- [ ] Moneyness (deep ITM)
- [ ] Minimum market cap
- [ ] Fundamental filters (P/E, revenue growth, debt-to-equity, etc.)
- [ ] Options liquidity (open interest, bid-ask spread)

### Fallback: Cash-Secured Puts (CSPs)
When LEAP conditions are not met (e.g., IV too high, stock is range-bound), the screener pivots to evaluating CSP opportunities on the same watchlist.

**CSP Pivot Conditions** *(to be finalized)*
- [ ] IV rank / IV percentile threshold
- [ ] Stock trading sideways or in a defined range
- [ ] Premium yield meets minimum threshold

---

## Features

- **Daily stock picks** — intentional, criteria-driven output. Quality over quantity.
- **Fundamental data** — market cap, P/E, revenue growth, debt-to-equity, EPS, sector, and more
- **Options chain analysis** — evaluates LEAP and CSP viability per stock
- **SPY baseline** — all picks are evaluated relative to SPY for relative strength and context *(baseline metrics TBD)*
- **Twitter/X cross-reference** — screens for social sentiment and chatter as a secondary signal *(implementation TBD — sentiment analysis, specific accounts, or mention volume)*
- **Terminal UI** — clean, readable output in the terminal; React + TypeScript UI planned for a future phase

---

## Tech Stack

| Layer | Technology |
|---|---|
| Core / Backend | Python |
| UI (future) | React + TypeScript |
| Data sources | TBD (yfinance, Polygon.io, etc.) |
| Twitter/X | TBD (X API v2) |

---

## Project Structure

```
trading-bot/
├── screener/
│   ├── fundamentals.py      # Pulls and evaluates fundamental data
│   ├── options.py           # LEAP and CSP evaluation logic
│   ├── sentiment.py         # Twitter/X cross-reference
│   ├── spy_baseline.py      # SPY comparison logic
│   └── screener.py          # Main screener pipeline
├── models/
│   └── stock.py             # Stock data model
├── tests/
│   └── ...                  # Unit tests (one per module)
├── main.py                  # Entry point
├── requirements.txt
├── CLAUDE.md
└── README.md
```

---

## Setup

```bash
# Clone the repo
git clone https://github.com/Joachim-Chuah/trading-bot.git
cd trading-bot

# Create and activate virtual environment
python -m venv venv
source venv/bin/activate  # Windows: venv\Scripts\activate

# Install dependencies
pip install -r requirements.txt

# Run the screener
python main.py
```

---

## Usage

```bash
# Run daily screen
python main.py

# Example output (terminal)
# ─────────────────────────────────────────────────────
# Daily Screen — 2026-05-21
# SPY: +0.42% | Baseline: Neutral
# ─────────────────────────────────────────────────────
# [LEAP]  AAPL  | Cap: $3.1T | P/E: 28 | Delta: 0.82 | DTE: 18mo | Sentiment: ↑
# [CSP]   META  | Cap: $1.4T | IV Rank: 34 | Strike: $480 | Yield: 1.2%/mo
# ─────────────────────────────────────────────────────
```

---

## Open Questions

- What are the exact LEAP entry criteria (delta, DTE, fundamental thresholds)?
- Twitter cross-ref: sentiment scoring, specific accounts, or mention volume?
- SPY baseline: what metrics are we comparing (relative strength, beta, sector)?
- CSP pivot: what specific conditions trigger the fallback?
- Daily picks: is there a target count, or purely criteria-driven?
