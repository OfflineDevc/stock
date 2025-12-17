import pandas as pd

try:
    print("--- S&P 500 ---")
    url_sp = 'https://en.wikipedia.org/wiki/List_of_S%26P_500_companies'
    tables_sp = pd.read_html(url_sp)
    print(tables_sp[0].columns.tolist())
    print(tables_sp[0].head(1))

    print("\n--- NASDAQ 100 ---")
    url_nd = 'https://en.wikipedia.org/wiki/Nasdaq-100'
    tables_nd = pd.read_html(url_nd, match='Ticker')
    print(tables_nd[0].columns.tolist())
    print(tables_nd[0].head(1))

except Exception as e:
    print(e)
