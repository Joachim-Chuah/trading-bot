import yfinance as yf
import pandas as pd


def get_vix(period: str = "5d") -> pd.DataFrame:
    return yf.Ticker("^VIX").history(period=period)


def get_price_history(ticker: str, period: str = "10y") -> pd.DataFrame:
    return yf.Ticker(ticker).history(period=period)
