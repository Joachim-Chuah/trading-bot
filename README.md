# Trading Screener

A terminal-based stock screener built around a LEAP options strategy. Surfaces intentional, high-conviction trade ideas daily — not noise.

---

## Strategy Overview

LEAPS (Long-term Equity Anticipation Securities) are used as a capital-efficient stock replacement strategy. The screener filters for stocks that meet strict fundamental and technical criteria before evaluating their options chain for viable LEAP entries.

**LEAP Entry Criteria**
1. **Oversold conditions across multiple timeframes** — RSI, MACD, and/or stochastic oversold on at least 2 timeframes (daily + weekly)
2. **Price at or near key support** — prior highs, 50/200 MA, or demand zone
3. **Low IV environment** — IV rank/percentile must be low to favor buying options
4. **Adequate options liquidity** — sufficient open interest and tight bid-ask spreads
5. **Strong fundamental catalyst** — earnings, product cycle, sector tailwind, etc.
6. **Strike within 10% OTM — no exceptions** — ATM to slight OTM gives real delta exposure. Beyond 10% OTM, premium is predominantly extrinsic value bleeding away via theta.

> **The cheap LEAP trap:** A $0.50 contract 30% OTM looks attractive but has almost no delta and is almost entirely time value. Stay ATM to ≤10% OTM — you pay more upfront but you're buying exposure, not hope.

---

## Screener Pipeline

Every run follows this exact order. A stock must pass each gate before moving to the next.

```
Step 0 — Macro Kill Switch
         VIX + Put/Call ratio checked first.
         Hostile macro → skip to SPY fallback immediately.
         │
         ▼ macro is neutral or favorable
Step 1 — Fundamentals Gate (FMP)
         Market cap, P/E, revenue growth, debt-to-equity, EPS.
         Weak fundamentals → discard.
         │
         ▼ fundamentals pass
Step 2 — Technical Analysis (Massive Stocks)
         Oversold across 2+ timeframes, price at key support.
         Not aligned → discard.
         │
         ▼ technicals pass
Step 3 — Options Evaluation (Massive Options)
         Low IV, adequate liquidity, strike ≤10% OTM.
         Conditions not met → discard.
         │
         ▼ options pass
Step 4 — Sentiment Comparison
         Massive news sentiment (stock-level) vs VIX + Put/Call (macro).
         Feeds conviction rating — does not gate picks.
         │
         ▼
Step 5 — Output
         Pick with conviction rating, news context, fundamentals snapshot.
         No qualifying stocks → SPY technical summary.
```

---

## Tech Stack

| Layer | Technology |
|---|---|
| Screener core | Python |
| API | FastAPI |
| Database | PostgreSQL (Neon) |
| ORM / Migrations | SQLAlchemy + Alembic |
| UI (future) | React + TypeScript |
| Tests | pytest |

---

## Architecture

```
Daily screener (Python)
        │
        ▼ writes
   PostgreSQL (Neon)
        │
        ▼ reads
     FastAPI  ◄──── External web app / other services
        │
        ▼ (future)
   React + TypeScript UI
```

The screener is the only writer — picks, run history, and API cache go to PostgreSQL. FastAPI is the read layer — everything external goes through it.

---

## Project Structure

```
trading-bot/
├── screener/
│   ├── macro.py             # Kill switch — VIX + Put/Call
│   ├── fundamentals.py      # FMP fundamentals gate
│   ├── technicals.py        # RSI, MACD, support detection
│   ├── options.py           # LEAP evaluation
│   ├── sentiment.py         # News sentiment + macro comparison
│   ├── spy_baseline.py      # SPY fallback technicals
│   └── screener.py          # Pipeline orchestrator
├── api/
│   ├── main.py              # FastAPI app
│   └── routes/              # Route handlers
├── clients/
│   ├── massive.py           # Massive API client
│   ├── fmp.py               # FMP client
│   ├── cboe.py              # CBOE put/call client
│   └── yfinance_client.py   # Historical backfill
├── db/
│   ├── models.py            # SQLAlchemy models
│   └── migrations/          # Alembic migrations
├── models/
│   └── stock.py             # Pydantic data models
├── tests/
├── main.py                  # Screener entry point
├── requirements.txt
├── .env.example
├── CLAUDE.md
└── README.md
```

---

## Setup

```bash
git clone https://github.com/Joachim-Chuah/trading-bot.git
cd trading-bot

python3 -m venv venv
source venv/bin/activate
pip install -r requirements.txt

# Copy env and fill in API keys + DATABASE_URL
cp .env.example .env
```

---

## Commands

```bash
python3 main.py                  # start scheduler (Mon-Fri 10:30am + 2:00pm, Sat 9:00am)
python3 main.py --now            # run live screener immediately
python3 main.py --research       # run weekend research scan immediately

python3 main.py --add AAPL       # add ticker to watchlist
python3 main.py --remove AAPL    # remove ticker from watchlist
python3 main.py --watchlist      # show current watchlist

pytest --cov=. --cov-report=term-missing  # run tests
```
