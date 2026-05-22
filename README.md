# Trading Screener

A terminal-based stock screener built around a LEAP options strategy, with a fallback to Cash-Secured Puts (CSPs). Designed to surface intentional, high-conviction trade ideas daily — not noise.

---

## Strategy Overview

### Primary: LEAP Options
LEAPS (Long-term Equity Anticipation Securities) are used as a capital-efficient stock replacement strategy. The screener filters for stocks that meet strict fundamental and technical criteria before evaluating their options chain for viable LEAP entries.

**LEAP Entry Criteria**
1. **Oversold conditions across multiple timeframes** — RSI, MACD, and/or stochastic showing oversold on at least 2 timeframes (e.g., daily + weekly)
2. **Price at or near key support** — stock sitting at a meaningful technical level (prior highs, 50/200 MA, demand zone)
3. **Low IV environment** — cheaper contracts; IV rank/percentile must be low to favor buying options
4. **Adequate options liquidity** — sufficient open interest and tight bid-ask spreads to enter and exit cleanly
5. **Strong fundamental catalyst** — a clear reason the stock should recover/grow (earnings, product cycle, sector tailwind, etc.)
6. **Strike within 10% OTM — no exceptions** — do not chase cheap far-OTM contracts. Beyond 10% OTM, premium is predominantly extrinsic value that bleeds away via theta every day. ATM or slight OTM (≤10%) gives real delta exposure; deeper OTM is a lottery ticket dressed as a trade.

> **The cheap LEAP trap:** A $0.50 contract 30% OTM looks attractive but has almost no delta and is almost entirely time value. You need a massive move just to break even. Stay ATM to ≤10% OTM — you pay more upfront but you're actually buying exposure, not hope.

*Greek specifics (delta, DTE, etc.) to be defined in a future iteration.*

### Fallback: Cash-Secured Puts (CSPs)
When LEAP conditions are not met (e.g., IV too high, stock is range-bound), the screener pivots to evaluating CSP opportunities on the same watchlist.

**CSP Pivot Conditions** *(to be finalized)*
- [ ] IV rank / IV percentile threshold
- [ ] Stock trading sideways or in a defined range
- [ ] Premium yield meets minimum threshold

---

## Constraints & Capital Rules

- **Capital:** $1,000–$1,500 deployed at a time — position sizing must respect this hard limit
- **Hold period:** Minimum 2–4 weeks per position — this is not a day trading tool
- **SPY fallback:** If no stocks meet criteria on a given day, the screener defaults to evaluating SPY technically and outputs that instead of forcing picks
- **No picks for the sake of picks** — zero output is a valid and correct result

---

## Features

- **Daily stock picks** — intentional, criteria-driven output. Quality over quantity.
- **Conviction rating** — each pick includes a conviction score based on fundamentals, technicals, news, and sentiment
- **News feed** — surfaces recent relevant news per stock; picks must be contextualized against current events
- **Fundamental data** — market cap, P/E, revenue growth, debt-to-equity, EPS, sector, and more
- **Options chain analysis** — evaluates LEAP and CSP viability per stock
- **SPY baseline + technicals** — all picks evaluated relative to SPY; SPY technicals shown on fallback days
- **Twitter/X cross-reference** — screens for social sentiment and chatter as a secondary signal *(implementation TBD — sentiment analysis, specific accounts, or mention volume)*
- **Terminal UI** — clean, readable output in the terminal; React + TypeScript UI planned for a future phase

---

## Tech Stack

| Layer | Technology |
|---|---|
| Screener core | Python |
| API | FastAPI |
| Database | PostgreSQL |
| ORM / Migrations | SQLAlchemy + Alembic |
| Local dev | Docker Compose |
| UI (future) | React + TypeScript |
| Data — price/technicals | Polygon.io (Stocks Starter) |
| Data — options/IV | Polygon.io (Options Starter) |
| Data — fundamentals | Financial Modeling Prep (Starter) |
| Data — historical backfill | yfinance |
| Sentiment | TBD (X API v2) |

## Architecture

```
Daily screener (Python)
        │
        ▼ writes
   PostgreSQL
        │
        ▼ reads
     FastAPI  ◄──── External web app / other services
        │
        ▼ (future)
   React + TypeScript UI
```

The screener is the **data producer** — it writes picks, run history, and API cache directly to PostgreSQL. FastAPI is the **data layer** — everything that reads data (web app, future UI) goes through it. Nothing outside the screener touches the DB directly.

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
├── api/
│   ├── main.py              # FastAPI app entry point
│   └── routes/              # API route handlers
├── db/
│   ├── models.py            # SQLAlchemy models
│   └── migrations/          # Alembic migrations
├── models/
│   └── stock.py             # Pydantic data models
├── tests/
│   └── ...                  # Unit tests (one per module)
├── docker-compose.yml
├── Dockerfile
├── main.py                  # Screener entry point
├── requirements.txt
├── .env.example
├── CLAUDE.md
└── README.md
```

---

## Setup

```bash
# Clone the repo
git clone https://github.com/Joachim-Chuah/trading-bot.git
cd trading-bot

# Copy env file and fill in your API keys
cp .env.example .env

# Start Postgres + FastAPI
docker compose up -d

# Create and activate virtual environment
python -m venv venv
source venv/bin/activate

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
# ─────────────────────────────────────────────────────────────────────────
# Daily Screen — 2026-05-21
# SPY: +0.42% | RSI: 58 | Trend: Bullish | Baseline: Neutral
# Capital available: $1,500 | Hold target: 2–4 weeks
# ─────────────────────────────────────────────────────────────────────────
# [LEAP]  AAPL  | Cap: $3.1T | P/E: 28 | Delta: 0.82 | DTE: 18mo
#               | News: Earnings beat, new product cycle
#               | Conviction: ★★★★☆  (High)
#
# [CSP]   META  | Cap: $1.4T | IV Rank: 34 | Strike: $480 | Yield: 1.2%/mo
#               | News: Ad revenue guidance raised
#               | Conviction: ★★★☆☆  (Medium)
# ─────────────────────────────────────────────────────────────────────────
#
# --- SPY Fallback day example ---
# No picks met criteria today.
# SPY Technical Summary: RSI 62 | 50MA > 200MA | MACD: Bullish cross
# Suggestion: Hold cash or add to existing SPY position.
# ─────────────────────────────────────────────────────────────────────────
```

---

## Open Questions

- Twitter cross-ref: sentiment scoring, specific accounts, or mention volume?
- Daily picks: is there a target count, or purely criteria-driven?
