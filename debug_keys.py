import yfinance as yf
import pandas as pd

try:
    s = yf.Ticker("AAPL")
    info = s.info
    print("KEYS Related to PEG/Growth:")
    for k, v in info.items():
        if "peg" in k.lower() or "growth" in k.lower() or "est" in k.lower():
            print(f"{k}: {v}")
            
    print("\n---\nTrying to calc PEG:")
    pe = info.get('trailingPE')
    peg = info.get('pegRatio')
    print(f"PE: {pe}, PEG: {peg}")
    
except Exception as e:
    print(e)
