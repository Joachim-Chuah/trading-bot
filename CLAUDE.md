# CLAUDE.md — Trading Screener

Guidelines for Claude when working in this repository.

---

## Project Context

This is a Python-based stock screener built around a LEAP options strategy. It is a screener, not a trading bot — it surfaces ideas, it does not execute trades. The UI is terminal-first; a React + TypeScript frontend may be added later.

---

## Tech Stack

- **Screener core:** Python
- **API:** FastAPI
- **Database:** PostgreSQL (Neon)
- **ORM / Migrations:** SQLAlchemy + Alembic
- **Scheduler:** APScheduler
- **UI (future):** React + TypeScript
- **Tests:** pytest
- **Sentiment:** FinBERT via `transformers` + `torch` (`ProsusAI/finbert`)

---

## Architecture Boundaries

- The **screener** is the only writer to the database — it runs daily and produces picks
- **FastAPI** is the only reader exposed externally — web apps and the future UI go through it
- Nothing outside the screener writes to the DB directly
- Keep screener logic and API logic completely separate — different modules, no shared business logic

---

## Data Source Hierarchy

- **Massive (Stocks + Options Starter)** — primary source for all live screening data
- **FMP (Starter)** — fundamentals only; do not use for price or options data. Base URL: `https://financialmodelingprep.com/stable` (v3 endpoints are legacy and blocked for new accounts)
- **yfinance `^VIX`** — primary macro fear/risk-off signal; free, no API key needed
- **CBOE put/call ratio** — secondary macro signal; scraped from CBOE daily stats page; optional — graceful fallback to VIX-only if unavailable
- **yfinance (price)** — historical price backfill beyond Massive's 5-year window; backtesting only, never live screening

Never use yfinance for live stock price or options data. yfinance for price is backtesting only.

---

## Sentiment Rules

Sentiment is evaluated in four layers. Each layer feeds into the final conviction score — sentiment does not gate or block a pick on its own.

### Layer 1 — Stock News Sentiment
- Pull news articles and headlines from Massive
- Score each headline with FinBERT (`ProsusAI/finbert`) — produces `bullish / neutral / bearish` + confidence score
- Compare against Massive's pre-scored sentiment on the same articles
- If both agree → increase signal weight and confidence
- If they diverge → classify as `mixed`; reduce conviction weight; do not force a bullish or bearish label
- Factor in article recency (`published_utc`), source quality (publisher), and relevance (FinBERT confidence as proxy)

### Layer 2 — Market Confirmation
- Price move after article: Massive snapshot price vs. article publish time — does the stock move in the implied direction? Skip for articles without sufficient post-publish time.
- Volume vs. average volume: elevated volume confirms the move is meaningful
- Sector ETF move: same Massive stocks endpoint on the relevant sector ETF (XLK, XLE, etc.)
- Broader index move: SPY — already pulled for baseline

### Layer 3 — Macro Risk
- VIX via yfinance `^VIX` — primary market fear/risk-off indicator; always required
- CBOE put/call ratio — secondary confirmation; captures options positioning rather than implied volatility alone
- Attempt CBOE scrape on each run; if unavailable, proceed with VIX only — `put_call_ratio` is nullable
- The macro kill switch (Step 0) runs on this layer before any stock is evaluated

### Layer 4 — Final Conviction
- `sentiment_signal`: resolved label — `bullish / neutral / bearish / mixed`
- `confidence`: how clean and consistent the data is (Massive + FinBERT agreement, recency)
- `conviction`: how much the market/macro confirms the stock-level signal
  - Stock bullish + macro risk-on/neutral → conviction increases
  - Stock bullish + macro risk-off → sentiment stays bullish, conviction reduced
  - Stock bearish + any macro → low conviction; pick likely already weak from earlier pipeline steps

---

## Screener Pipeline Order

Steps must execute in this order. Never reorder or skip steps:

```
0. Macro kill switch   → VIX + Put/Call (hostile = abort to SPY output)
1. Fundamentals gate   → FMP (weak = discard)
2. Technical analysis  → Massive Stocks (not aligned = discard)
3. Options evaluation  → Massive Options (conditions not met = discard)
4. Sentiment scoring   → 4-layer: stock news (Massive + FinBERT) → market confirmation → macro risk → final conviction
5. Output              → pick with conviction, news, fundamentals snapshot
```

---

## 1. Think Before Coding

**Don't assume. Don't hide confusion. Surface tradeoffs.**

Before implementing:
- State assumptions explicitly. If uncertain, ask.
- If multiple interpretations exist, present them — don't pick silently.
- If a simpler approach exists, say so. Push back when warranted.
- If something is unclear, stop. Name what's confusing. Ask.

---

## 2. Simplicity First

**Minimum code that solves the problem. Nothing speculative.**

- No features beyond what was asked.
- No abstractions for single-use code.
- No "flexibility" or "configurability" that wasn't requested.
- No error handling for impossible scenarios.
- If you write 200 lines and it could be 50, rewrite it.

Ask: "Would a senior engineer say this is overcomplicated?" If yes, simplify.

---

## 3. Surgical Changes

**Touch only what you must. Clean up only your own mess.**

When editing existing code:
- Don't "improve" adjacent code, comments, or formatting.
- Don't refactor things that aren't broken.
- Match existing style, even if you'd do it differently.
- If you notice unrelated dead code, mention it — don't delete it.

When your changes create orphans:
- Remove imports/variables/functions that YOUR changes made unused.
- Don't remove pre-existing dead code unless asked.

Every changed line should trace directly to the user's request.

---

## 4. Goal-Driven Execution

**Define success criteria. Loop until verified.**

Transform tasks into verifiable goals:
- "Add validation" → "Write tests for invalid inputs, then make them pass"
- "Fix the bug" → "Write a test that reproduces it, then make it pass"
- "Refactor X" → "Ensure tests pass before and after"

For multi-step tasks, state a brief plan:
```
1. [Step] → verify: [check]
2. [Step] → verify: [check]
3. [Step] → verify: [check]
```

---

## Code Standards

### General
- Keep functions small and single-purpose
- Prefer explicit over implicit — no magic
- No dead code; remove unused imports, variables, and functions
- Use type hints on all function signatures
- Fail loudly at system boundaries (external APIs, user input); trust internal code

### Python Specifics
- Follow PEP 8
- Use dataclasses or Pydantic models for data structures — no raw dicts passed between modules
- Use `pathlib` over `os.path`
- Environment variables via `python-dotenv`; never hardcode API keys or secrets

### Comments
- Default to no comments
- Only add a comment when the **why** is non-obvious (hidden constraint, workaround, subtle invariant)
- Do not comment what the code does — well-named functions and variables do that

---

## Testing

**Unit tests are required for every new feature.**

- Tests live in `tests/` and mirror the module structure (e.g., `screener/fundamentals.py` → `tests/test_fundamentals.py`)
- Use `pytest`
- Aim for **≥ 80% code coverage** across the project; critical strategy logic (LEAP criteria: oversold detection, support levels, IV check, liquidity check, OTM threshold, fundamental catalyst — and macro kill switch) must be at **100%**
- Test edge cases: empty data, API failures, boundary values on thresholds
- Do not mock internal logic — only mock at external boundaries (API calls, file I/O)
- Run tests before marking any task complete:
  ```bash
  pytest --cov=. --cov-report=term-missing
  ```

---

## Architecture Principles

- **No trading execution** — this is read-only. Never add code that places orders.
- **Screener pipeline is modular** — each step (macro kill switch → fundamentals → technicals → options → sentiment → output) is independent and testable in isolation
- **SPY is always the baseline** — any stock output must include its performance relative to SPY; on no-pick days or kill switch days, output SPY technicals instead
- **Intentional output** — if no stocks pass criteria on a given day, the output must say so clearly and fall back to SPY. Do not loosen criteria to produce picks.
- **Capital-aware** — all position suggestions must respect the $1,000–$1,500 capital constraint and the 2–4 week minimum hold period
- **News is mandatory context** — every pick must surface recent relevant news; a pick without news context is incomplete
- **Conviction is required** — every pick must include a conviction rating. Never output a pick without one.
- **OTM hard limit** — never suggest a LEAP contract more than 10% OTM. Deeper OTM = mostly extrinsic value = theta decay with no real delta exposure.
- **Macro kill switch is non-negotiable** — if macro conditions are hostile (VIX primary, CBOE put/call supplementary), the screener must abort individual stock evaluation entirely and output SPY technicals only.
- **Two run modes** — `live` (full pipeline, runs Mon–Fri at 10:30am and 2:00pm ET via APScheduler) and `research` (weekend research: news, watchlist review, backtesting, weekly prep). Never run live options evaluation in research mode.

---

## What NOT to Do

- Do not add features beyond the current task scope
- Do not add backwards-compatibility shims for removed code — delete it cleanly
- Do not introduce abstractions until there are at least three concrete use cases for them
- Do not commit secrets, API keys, or `.env` files
- Do not skip tests to ship faster
- Do not add sentiment sources beyond the four defined layers (Massive news, FinBERT, VIX, CBOE put/call) without explicit instruction

---

## PR / Commit Hygiene

- Commit messages should explain **why**, not just what
- Each PR should have a clear test plan
- Do not merge without passing tests and adequate coverage
