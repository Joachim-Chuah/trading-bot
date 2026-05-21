# CLAUDE.md — Trading Screener

Guidelines for Claude when working in this repository.

---

## Project Context

This is a Python-based stock screener built around a LEAP options strategy with a CSP fallback. It is a screener, not a trading bot — it surfaces ideas, it does not execute trades. The UI is terminal-first; a React + TypeScript frontend may be added later.

---

## Tech Stack

- **Backend / Core:** Python
- **UI (future):** React + TypeScript
- **Tests:** pytest

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
- Aim for **≥ 80% code coverage** across the project; critical strategy logic (LEAP criteria, CSP pivot conditions) must be at **100%**
- Test edge cases: empty data, API failures, boundary values on thresholds
- Do not mock internal logic — only mock at external boundaries (API calls, file I/O)
- Run tests before marking any task complete:
  ```bash
  pytest --cov=. --cov-report=term-missing
  ```

---

## Architecture Principles

- **No trading execution** — this is read-only. Never add code that places orders.
- **Screener pipeline is modular** — each step (fundamentals → options → sentiment → output) is independent and testable in isolation
- **SPY is always the baseline** — any stock output must include its performance relative to SPY
- **Intentional output** — if no stocks pass criteria on a given day, the output should say so clearly. Do not loosen criteria to produce picks.

---

## What NOT to Do

- Do not add features beyond the current task scope
- Do not add error handling for scenarios that cannot happen
- Do not add backwards-compatibility shims for removed code — delete it cleanly
- Do not introduce abstractions until there are at least three concrete use cases for them
- Do not commit secrets, API keys, or `.env` files
- Do not skip tests to ship faster

---

## PR / Commit Hygiene

- Commit messages should explain **why**, not just what
- Each PR should have a clear test plan
- Do not merge without passing tests and adequate coverage
