import pandas as pd

url = 'https://en.wikipedia.org/wiki/Nasdaq-100'
try:
    tables = pd.read_html(url, storage_options={'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36'})
    
    with open('debug_output.txt', 'w', encoding='utf-8') as f:
        f.write(f"Number of tables found: {len(tables)}\n")
        
        for i, table in enumerate(tables):
            cols = [str(c) for c in table.columns.tolist()]
            if 'Ticker' in cols or 'Symbol' in cols:
                f.write(f"Table {i} has target columns: {cols}\n")
                f.write(str(table.head()) + "\n")
            elif i < 5: # Log first 5 tables headers just in case
                f.write(f"Table {i} columns: {cols}\n")
                
except Exception as e:
    with open('debug_output.txt', 'w') as f:
        f.write(f"Error: {e}")
