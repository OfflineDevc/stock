import yfinance as yf
import json

try:
    ticker = yf.Ticker("NVDA")
    info = ticker.info
    
    print(f"Trailing EPS: {info.get('trailingEps')}")
    print(f"Forward EPS: {info.get('forwardEps')}")
    
    # Check for other EPS related keys
    eps_keys = [k for k in info.keys() if 'eps' in k.lower()]
    print(f"EPS Related Keys: {eps_keys}")
    
except Exception as e:
    print(f"Error: {e}")
