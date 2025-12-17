import yfinance as yf
import traceback

tickers = ["PTT.BK"]
for t in tickers:
    print(f"--- Checking {t} ---")
    try:
        stock = yf.Ticker(t)
        
        # Check fast_info
        print("Checking fast_info...")
        try:
            fi = stock.fast_info
            print(f"FastInfo LastPrice: {fi.get('last_price', 'N/A')}")
        except:
            print("FastInfo failed")

        # Check full info
        print("Checking full info...")
        info = stock.info
        print(f"Info Keys: {list(info.keys())[:5]}...")
        print(f"currentPrice: {info.get('currentPrice')}")
        print(f"regularMarketPrice: {info.get('regularMarketPrice')}")
        print(f"trailingPE: {info.get('trailingPE')}")
        
    except Exception:
        traceback.print_exc()
