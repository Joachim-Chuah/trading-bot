from datetime import date
from typing import Literal
from pydantic import BaseModel, Field


class FundamentalsData(BaseModel):
    market_cap: float
    pe_ratio: float | None = None
    revenue_growth: float | None = None
    debt_to_equity: float | None = None
    eps: float | None = None
    sector: str | None = None


class TechnicalsData(BaseModel):
    rsi_daily: float
    rsi_weekly: float
    macd_signal: Literal["bullish", "neutral", "bearish"]
    at_support: bool
    price: float


class OptionsData(BaseModel):
    iv_rank: float
    open_interest: int
    bid_ask_spread: float
    strike: float
    expiration: date
    contract_symbol: str


class MacroSnapshot(BaseModel):
    vix: float
    put_call_ratio: float
    signal: Literal["favorable", "neutral", "hostile"]
    spy_price: float
    spy_rsi: float
    spy_trend: Literal["bullish", "neutral", "bearish"]


class Pick(BaseModel):
    ticker: str
    conviction: int = Field(ge=1, le=5)
    news_sentiment: Literal["bullish", "neutral", "bearish"]
    news_headlines: list[str]
    fundamentals: FundamentalsData
    options_data: OptionsData
    technicals: TechnicalsData


class ScreenerResult(BaseModel):
    run_date: date
    macro: MacroSnapshot
    picks: list[Pick]
    spy_fallback: bool
