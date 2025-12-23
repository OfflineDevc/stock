import yfinance as yf
import pandas as pd

def debug_stock(ticker):
    print(f"--- Debugging {ticker} ---")
    stock = yf.Ticker(ticker)
    
    # 1. Shares
    shares = stock.info.get('sharesOutstanding')
    print(f"Shares Outstanding: {shares:,.0f}" if shares else "Shares: None")
    
    # 2. Cashflow
    cf = stock.cashflow
    print("\n[Raw Cashflow Index]:", cf.index.tolist())
    
    # Check key rows
    keys = ['Free Cash Flow', 'Total Cash From Operating Activities', 'Capital Expenditures']
    for k in keys:
        if k in cf.index:
            row = cf.loc[k]
            print(f"\n{k}:")
            print(row.head(4).apply(lambda x: f"{x:,.0f}"))
        else:
            print(f"\n{k}: MISSING")

    # 3. Calculation Check
    # Let's see if FCF matches OCF + CapEx
    if 'Total Cash From Operating Activities' in cf.index and 'Capital Expenditures' in cf.index:
        ocf = cf.loc['Total Cash From Operating Activities']
        capex = cf.loc['Capital Expenditures']
        # Note: Capex is negative in yfinance usually
        calc_fcf = ocf + capex
        print("\nCalculated FCF (OCF + CapEx):")
        print(calc_fcf.head(4).apply(lambda x: f"{x:,.0f}"))
    
    if shares:
        if 'Free Cash Flow' in cf.index:
            latest_fcf = cf.loc['Free Cash Flow'].dropna().iloc[0]
            print(f"\n[Latest FCF/Share]: {latest_fcf / shares:.2f}")
            
            avg_3y = cf.loc['Free Cash Flow'].dropna().head(3).mean()
            print(f"[3Y Avg FCF/Share]: {avg_3y / shares:.2f}")

debug_stock("AAPL")
print("\n" + "="*30 + "\n")
debug_stock("PTT.BK") # Check a Thai stock too
