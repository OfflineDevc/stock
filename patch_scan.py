
import os

path = r'c:\Stock\crypto.py'

new_code = r'''
# --- CRYPTO METRIC HELPERS ---
def calculate_rsi(series, period=14):
    delta = series.diff()
    gain = (delta.where(delta > 0, 0)).rolling(window=period).mean()
    loss = (-delta.where(delta < 0, 0)).rolling(window=period).mean()
    rs = gain / loss
    return 100 - (100 / (1 + rs))

def calculate_mvrv_z_proxy(series, window=200):
    ma = series.rolling(window=window).mean()
    std = series.rolling(window=window).std()
    z_score = (series - ma) / std
    return z_score

# --- Stage 1: Fast Scan (Batch) ---
def scan_market_basic(tickers, progress_bar, status_text, debug_container=None):
    data_list = []
    status_text.text("Stage 1: Fetching Market Data (Batch Mode)...")
    
    if not tickers: return []
    
    import pandas as pd
    
    # Batch Download for Speed
    try:
        data = yf.download(tickers, period="2y", group_by='ticker', threads=True)
    except Exception as e:
        status_text.error(f"Download Failed: {e}")
        return []

    status_text.text("Stage 1: Calculating On-Chain Metrics...")
    
    total = len(tickers)
    
    # Handle Single Ticker vs Multi Ticker Structure
    if len(tickers) == 1:
        ticker = tickers[0]
        valid_tickers = [ticker]
    else:
        valid_tickers = tickers
        
    for i, ticker in enumerate(valid_tickers):
        if i % 5 == 0: progress_bar.progress((i + 1) / total)
        
        try:
            # Extract Series
            if len(tickers) == 1:
                hist = data
            else:
                hist = data[ticker]
            
            if hist is None or hist.empty or 'Close' not in hist.columns: continue
            
            # Drop NaN
            hist = hist.dropna(subset=['Close'])
            if len(hist) < 200: continue # Need history for Z-Score
            
            # --- CALCULATE METRICS ---
            closes = hist['Close']
            
            # 1. Valuation: MVRV Z-Score Proxy
            z_score_series = calculate_mvrv_z_proxy(closes)
            current_z = z_score_series.iloc[-1] if not pd.isna(z_score_series.iloc[-1]) else 0
            
            # 2. Momentum: RSI
            rsi_series = calculate_rsi(closes)
            current_rsi = rsi_series.iloc[-1] if not pd.isna(rsi_series.iloc[-1]) else 50
            
            # 3. Volatility (30D)
            returns = closes.pct_change()
            vol_30d = returns.rolling(30).std().iloc[-1] * (365 ** 0.5) * 100
            if pd.isna(vol_30d): vol_30d = 0
            
            # 4. Cycle State
            cycle_state = "😐 Neutral"
            if current_z < 0: cycle_state = "🟢 Accumulation (Undervalued)"
            elif current_z > 3: cycle_state = "🔴 Euphoria (Overvalued)"
            elif current_z > 1.5: cycle_state = "🟠 Greed"
            
            # 5. Price Change
            price = closes.iloc[-1]
            chg_7d = (price - closes.iloc[-8]) / closes.iloc[-8] * 100 if len(closes) > 7 else 0
            chg_30d = (price - closes.iloc[-31]) / closes.iloc[-31] * 100 if len(closes) > 31 else 0
            
            data_list.append({
                'Symbol': ticker,
                'Price': price,
                'MVRV_Z': current_z,
                'RSI': current_rsi,
                'Vol_30D': vol_30d,
                'Cycle_State': cycle_state,
                '7D': chg_7d,
                '30D': chg_30d,
                'YF_Obj': None 
            })
            
        except Exception as e:
            if debug_container: debug_container.write(f"Error {ticker}: {e}")
            continue
            
    return data_list

'''

with open(path, 'r', encoding='utf-8') as f:
    content = f.read()

# Locate Block
start_marker = "# --- Stage 1: Fast Scan (Basic Metrics) ---"
next_func_marker = "# ---------------------------------------------------------\n# 3. Classifications & Scoring"

# Wait, looking at file view (Step 32), line 1173 starts with "# ---------------------------------------------------------".
# Line 1176 is "def classify_lynch(row):".
# Line 770 is "# --- Stage 1: Fast Scan (Basic Metrics) ---".
# So I should split by these markers.

parts = content.split(start_marker)
if len(parts) > 1:
    pre_block = parts[0]
    rest = parts[1]
    
    # Now find the end of the block in 'rest'
    # Use "def classify_lynch" as anchor or just the header before it.
    end_anchor = "def classify_lynch(row):"
    
    # Problem: classify_lynch is far down. In between there might be "analyze_history_deep" in stock.py?
    # Actually, stock.py has "scan_market_basic" then "analyze_history_deep" then "classify_lynch"?
    # The view in Step 32 started at 1150 and showed classify_lynch at 1176.
    # Where is analyze_history_deep? It is probably AFTER scan_market_basic.
    
    # Let's inspect what is AFTER scan_market_basic using the view we have.
    # We saw up to 900.
    # scan_market_basic ends loop, returns data_list.
    # Then there is likely "analyze_history_deep".
    
    # Safe bet: Replace "def scan_market_basic" function until "def " of the next function.
    import re
    
    # Find start of function
    match_start = re.search(r'def scan_market_basic\(.*?\):', rest)
    if match_start:
        # We invoke the replacement logic
        # But wait, 'rest' starts right after the marker. So 'rest' begins with "def scan_market_basic..." or close to it.
        pass

    # Easier strategy: Replace specifically the text known to exist.
    # No, I will use regex to replace the function body.
    
    pattern = r"def scan_market_basic\(.*?\):.*?return data_list"
    # DOTALL
    import re
    # We need to capture up to return data_list but non-greedy? No, greedy until the LAST return data_list in that function?
    # It takes indentation into account.
    
    # Simpler: Split by "def scan_market_basic" and the next known function "def analyze_history_deep" (if it existed) or "def classify_lynch".
    # I'll check for "analyze_history_deep".
    
    next_func = "def analyze_history_deep"
    if next_func not in rest:
        next_func = "def classify_lynch" # Fallback
        
    if next_func in rest:
         body, tail = rest.split(next_func, 1)
         
         final_content = pre_block + new_code + "\n\n" + next_func + tail
         
         with open(path, 'w', encoding='utf-8') as f:
             f.write(final_content)
         print("SUCCESS")
    else:
         print("FAILED: Could not find next function marker")

else:
    print("FAILED: Could not find start marker")
