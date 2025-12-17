import pandas as pd
import requests
from io import StringIO

headers = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36"
}

def get_wiki_cols(url, match_str=None):
    try:
        r = requests.get(url, headers=headers)
        r.raise_for_status()
        dfs = pd.read_html(StringIO(r.text), match=match_str)
        df = dfs[0]
        print(f"\n--- URL: {url} ---")
        print("Columns:", df.columns.tolist())
        print("First Row:", df.iloc[0].to_dict())
        return df
    except Exception as e:
        print(f"Error fetching {url}: {e}")

# S&P 500
get_wiki_cols('https://en.wikipedia.org/wiki/List_of_S%26P_500_companies')

# NASDAQ 100
get_wiki_cols('https://en.wikipedia.org/wiki/Nasdaq-100', match='Ticker')
