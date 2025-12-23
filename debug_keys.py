import yfinance as yf
import pandas as pd

def check_keys(ticker):
    print(f"--- Keys for {ticker} ---")
    stock = yf.Ticker(ticker)
    cf = stock.cashflow
    print("Cashflow Keys:")
    for k in cf.index:
        print(f" - {k}")

check_keys("AAPL")
