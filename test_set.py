import yfinance as yf

tickers = ["PTT.BK", "AOT.BK", "DELTA.BK"]
for t in tickers:
    print(f"--- {t} ---")
    try:
        stock = yf.Ticker(t)
        info = stock.info
        print(f"Price: {info.get('currentPrice')}")
        print(f"PE: {info.get('trailingPE')}")
        print(f"PEG: {info.get('pegRatio')}")
        print(f"Growth: {info.get('earningsQuarterlyGrowth')}")
        print(f"ROE: {info.get('returnOnEquity')}")
        print(f"Keys found: {len(info.keys())}")
    except Exception as e:
        print(f"Error: {e}")
