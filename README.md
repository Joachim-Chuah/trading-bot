# Trading Screener

A terminal-based stock screener built around a LEAP options strategy. Designed to surface intentional, high-conviction trade ideas daily — not noise.

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
6. **Strike within 10% OTM — no exceptions** — ATM or slight OTM (≤10%) gives real delta exposure. Beyond 10% OTM, premium is predominantly extrinsic value bleeding away via theta every day.

> **The cheap LEAP trap:** A $0.50 contract 30% OTM looks attractive but has almost no delta and is almost entirely time value. You need a massive move just to break even. Stay ATM to ≤10% OTM — you pay more upfront but you're actually buying exposure, not hope.

**Greek risk is managed implicitly by the criteria:**
- Theta (time decay) → controlled by the ≤10% OTM rule. Staying near the money means premium is mostly intrinsic, not extrinsic bleeding away daily.
- Vega (IV risk) → controlled by the low IV environment criterion. Buying when IV is low means IV crush works in your favour, not against you.

---

## Constraints & Capital Rules

- **Capital:** $1,000–$1,500 deployed at a time — position sizing must respect this hard limit
- **Hold period:** Minimum 2–4 weeks per position — this is not a day trading tool
- **SPY fallback:** If no stocks meet criteria on a given day, the screener outputs SPY technicals instead of forcing picks
- **Purely criteria-driven** — no hard cap on picks. The criteria decide the count. Zero is valid. That's the point of a screener.

---

## Screener Pipeline

Every run follows this exact order. A stock must pass each gate before moving to the next.

```
Step 0 — Macro Kill Switch
         VIX + Put/Call ratio checked first.
         Hostile macro environment → skip to SPY fallback output immediately.
         │
         ▼ macro is neutral or favorable
Step 1 — Fundamentals Gate (FMP)
         Market cap, P/E, revenue growth, debt-to-equity, EPS.
         Weak fundamentals → discard ticker.
         │
         ▼ fundamentals pass
Step 2 — Technical Analysis (Massive Stocks)
         Oversold across 2+ timeframes, price at key support.
         Technicals not aligned → discard ticker.
         │
         ▼ technicals pass
Step 3 — Options Evaluation (Massive Options)
         Low IV environment, adequate liquidity, strike ≤10% OTM.
         Options conditions not met → discard ticker.
         │
         ▼ options pass
Step 4 — Sentiment Comparison
         Massive news sentiment (stock-level) vs VIX + Put/Call (macro).
         Sentiment feeds conviction rating — does not gate/block a pick.
         │
         ▼
Step 5 — Output
         Pick with conviction rating, news context, fundamentals snapshot.
         No qualifying stocks → SPY technical summary output.
```

---

## Sentiment

Sentiment is kept intentionally simple — two signals compared against each other.

**Signal 1: Massive News Sentiment (stock-level)**
- Pre-scored sentiment on news articles returned by the Massive news endpoint
- Tells you: *is the narrative around this specific stock positive or negative right now?*
- Source: Massive Stocks Starter (included, no extra cost)

**Signal 2: VIX + Put/Call Ratio (macro-level)**
- VIX (`^VIX` via yfinance): market fear gauge. Above 30 = fear, below 15 = complacency
- Put/Call ratio (CBOE, free): above 1.2 = extreme fear (contrarian bullish), below 0.7 = extreme greed (contrarian bearish). Smoothed with 5-day MA
- Tells you: *is the broader market fearful or greedy?*
- Source: yfinance + CBOE (both free)

**How they compare:**

| News Sentiment | VIX + Put/Call | Conviction Impact |
|---|---|---|
| Bullish | Fearful (contrarian bullish) | Highest — positive narrative in a scared market |
| Bullish | Greedy | Lower — crowd already knows, late |
| Bearish | Fearful | Skip — bad stock in bad market |
| Bearish | Greedy | Skip |

The ideal LEAP setup: stock-level news turning positive while the macro is still fearful. Fear has peaked, catalyst is emerging.

---

## Features

- **Daily stock picks** — intentional, criteria-driven. Quality over quantity.
- **Conviction rating** — every pick rated based on fundamentals, technicals, options conditions, and sentiment comparison
- **News context** — mandatory for every pick; surfaces the Massive news sentiment score and recent headlines
- **Fundamental data** — market cap, P/E, revenue growth, debt-to-equity, EPS, sector
- **Options chain analysis** — evaluates LEAP viability; enforces ≤10% OTM hard limit
- **Macro kill switch** — VIX and Put/Call checked before any stock evaluation; hostile macro = immediate SPY fallback
- **SPY baseline + technicals** — all picks include SPY relative performance; SPY technicals shown on fallback days
- **Terminal UI** — clean output in the terminal; React + TypeScript UI planned for a future phase

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
| Data — price/technicals | Massive (Stocks Starter, $29/mo) |
| Data — options/IV | Massive (Options Starter, $29/mo) |
| Data — fundamentals | Financial Modeling Prep (Starter, $19/mo) |
| Data — historical backfill | yfinance (free) |
| Sentiment — stock level | Massive news endpoint (included) |
| Sentiment — macro | yfinance `^VIX` + CBOE Put/Call (free) |

**Total data cost: $77/mo**

---

## Data Sources & API Calls

### Massive Stocks Starter ($29/mo)
| Endpoint | Used for |
|---|---|
| `GET /v2/aggs/ticker/{ticker}/range/1/day` | Daily OHLCV → 50MA, 200MA, support levels |
| `GET /v2/aggs/ticker/{ticker}/range/1/week` | Weekly OHLCV → multi-timeframe RSI/MACD |
| `GET /v1/indicators/rsi/{ticker}` | RSI oversold detection |
| `GET /v1/indicators/macd/{ticker}` | MACD oversold detection |
| `GET /v2/snapshot/locale/us/markets/stocks/tickers/{ticker}` | Current price vs support check |
| `GET /v2/reference/news?ticker={ticker}` | Pre-scored news sentiment + headlines |

### Massive Options Starter ($29/mo)
| Endpoint | Used for |
|---|---|
| `GET /v3/snapshot/options/{ticker}` | Full chain — IV, greeks, OI, bid-ask |
| `GET /v3/snapshot/options/{ticker}/{contract}` | Specific LEAP or CSP contract evaluation |
| `GET /v3/reference/options/contracts` | Available strikes and expirations |

### Financial Modeling Prep Starter ($19/mo)
| Endpoint | Used for |
|---|---|
| `GET /v3/profile/{ticker}` | Market cap, sector, beta, description |
| `GET /v3/ratios/{ticker}` | P/E, debt-to-equity, ROE, price-to-book |
| `GET /v3/income-statement/{ticker}` | Revenue growth, EPS, net income trend |
| `GET /v3/key-metrics/{ticker}` | Supplemental metrics, EV, dividend yield |

### yfinance (free)
| Call | Used for |
|---|---|
| `Ticker("^VIX").history()` | VIX macro sentiment signal |
| `Ticker(t).history(period="10y")` | Historical price backfill beyond Massive's 5yr window |

### CBOE (free)
| Source | Used for |
|---|---|
| Daily put/call ratio | Macro sentiment signal, smoothed with 5-day MA |

---

## Backtesting Approach

| Data | Source | Range |
|---|---|---|
| Price / technicals | Massive Stocks | Last 5 years (within paid tier) |
| Price / technicals | yfinance | Beyond 5 years (free backfill) |
| Options / IV | Massive Options | Last 2 years only |
| Fundamentals | FMP | Last 5 years (annual) |

Massive is used first within its coverage range (more reliable). yfinance fills the gap for price history beyond 5 years. Historical options backtesting is limited to 2 years — the Massive Options Starter constraint. Options-specific backtesting (IV regime, contract pricing) stays within that window; price and fundamental criteria can be backtested further.

---

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

The screener is the **data producer** — writes picks, run history, and API cache to PostgreSQL. FastAPI is the **data layer** — everything that reads (web app, future UI) goes through it. Nothing outside the screener writes to the DB directly.

---

## Project Structure

```
trading-bot/
├── screener/
│   ├── fundamentals.py      # FMP fundamentals gate
│   ├── options.py           # LEAP evaluation
│   ├── technicals.py        # RSI, MACD, support level detection
│   ├── sentiment.py         # Massive news sentiment + VIX/Put/Call
│   ├── macro.py             # Kill switch — VIX + Put/Call check
│   ├── spy_baseline.py      # SPY comparison + fallback technicals
│   └── screener.py          # Main pipeline orchestrator
├── api/
│   ├── main.py              # FastAPI app entry point
│   └── routes/              # API route handlers
├── db/
│   ├── models.py            # SQLAlchemy models
│   └── migrations/          # Alembic migrations
├── models/
│   └── stock.py             # Pydantic data models
├── tests/
│   └── ...                  # Unit tests mirroring screener/ structure
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

# Copy env file and fill in API keys
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

# Example output
# ─────────────────────────────────────────────────────────────────────────
# Daily Screen — 2026-05-21
# Macro: VIX 22.4 (Neutral) | Put/Call 0.94 (Neutral) → Proceed
# SPY: +0.42% | RSI: 58 | Trend: Bullish
# Capital: $1,500 | Hold target: 2–4 weeks
# ─────────────────────────────────────────────────────────────────────────
# [LEAP]  AAPL  | Cap: $3.1T | P/E: 28 | IV Rank: 18 | Strike ≤10% OTM
#               | News sentiment: Bullish | Macro: Neutral → Conviction: ★★★★☆
#               | Headlines: Earnings beat, new product cycle announced
#
# ─────────────────────────────────────────────────────────────────────────
#
# --- SPY Fallback example ---
# Macro: VIX 38.1 (Fear) | Put/Call 1.3 (Extreme Fear) → Kill switch triggered
# No individual picks evaluated.
# SPY Technicals: RSI 62 | 50MA > 200MA | MACD: Bullish cross
# ─────────────────────────────────────────────────────────────────────────
```

---

