from sqlalchemy import Column, Integer, String, Float, Date, DateTime, Boolean, JSON, ForeignKey
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func
from db.database import Base


class ScreenerRun(Base):
    __tablename__ = "screener_runs"

    id = Column(Integer, primary_key=True)
    run_date = Column(Date, nullable=False)
    spy_price = Column(Float)
    spy_rsi = Column(Float)
    spy_trend = Column(String)
    vix = Column(Float)
    put_call_ratio = Column(Float)
    macro_signal = Column(String)  # "favorable", "neutral", "hostile"
    picks_count = Column(Integer, default=0)
    created_at = Column(DateTime, server_default=func.now())

    picks = relationship("Pick", back_populates="run")


class Pick(Base):
    __tablename__ = "picks"

    id = Column(Integer, primary_key=True)
    run_id = Column(Integer, ForeignKey("screener_runs.id"), nullable=False)
    ticker = Column(String, nullable=False)
    conviction = Column(Integer)  # 1-5
    news_sentiment = Column(String)  # "bullish", "neutral", "bearish"
    news_headlines = Column(JSON)
    fundamentals = Column(JSON)
    options_data = Column(JSON)
    technicals = Column(JSON)
    created_at = Column(DateTime, server_default=func.now())

    run = relationship("ScreenerRun", back_populates="picks")


class Watchlist(Base):
    __tablename__ = "watchlist"

    id = Column(Integer, primary_key=True)
    ticker = Column(String, nullable=False, unique=True)
    active = Column(Boolean, default=True)
    notes = Column(String)
    added_at = Column(DateTime, server_default=func.now())


class ApiCache(Base):
    __tablename__ = "api_cache"

    id = Column(Integer, primary_key=True)
    cache_key = Column(String, nullable=False, unique=True)
    data = Column(JSON, nullable=False)
    expires_at = Column(DateTime, nullable=False)
    created_at = Column(DateTime, server_default=func.now())
