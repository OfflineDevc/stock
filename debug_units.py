import yfinance as yf
import pandas as pd

pd.set_option('display.max_rows', None)
pd.set_option('display.float_format', '{:,.2f}'.format)

def analyze_units(ticker):
    print(f"--- {ticker} Unit Check ---")
    stock = yf.Ticker(ticker)
    
    # 1. Shares
    shares = stock.info.get('sharesOutstanding')
    print(f"Shares Outstanding: {shares:,.0f}")
    
    # 2. Market Cap (Check Magnitude)
    price = stock.history(period='1d')['Close'].iloc[-1]
    mcap = shares * price
    print(f"Price: {price:.2f}")
    print(f"Calc Market Cap: {mcap:,.0f}")
    
    # 3. Cash Flow
    # yfinance usually returns full numbers, but let's verify
    cf = stock.cashflow
    if not cf.empty:
        ocf = cf.loc['Total Cash From Operating Activities'].iloc[0]
        capex = cf.loc['Capital Expenditures'].iloc[0]
        
        print(f"OCF (Latest): {ocf:,.0f}")
        print(f"CapEx (Latest): {capex:,.0f}")
        
        fcf = ocf + capex
        print(f"Calculated FCF (Total): {fcf:,.0f}")
        
        fcf_per_share = fcf / shares
        print(f"FCF / Share: {fcf_per_share:.4f}")
        
        # Check against the bad value seen by user ($1.26 for AAPL?)
        # If FCF/Share is ~6-7, then code is fine but maybe user saw something else.
        # If FCF/Share is ~1.26, then `shares` might be diluted or `ocf` is weird.

    else:
        print("No Cashflow Data")

analyze_units("AAPL")
