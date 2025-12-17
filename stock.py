
import requests
import streamlit as st
import yfinance as yf
import pandas as pd
import numpy as np
import time

# Set up a session with a browser User-Agent
session = requests.Session()
session.headers.update({
    'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36'
})

# --- LOCALIZATION & TEXT ASSETS ---
TRANS = {
    'EN': {
        'sidebar_title': "🏛️ Scanner Controls",
        'market_label': "Market Index",
        'strategy_label': "Strategy Preset",
        'mode_header': "3. Mode",
        'strict_label': "Select Strictly Enforced Metrics",
        'perf_label': "Select Performance Metrics",
        'val_header': "📊 Valuation Metrics",
        'prof_header': "📈 Profitability & Growth",
        'risk_header': "🛡️ Risk",
        'execute_btn': "🚀 Execute 2-Stage Screen",
        'main_title': "📈 Stock Scanner by kun p. & yahoo finance",
        'scan_limit': "Scan Limit",
        'results_header': "🏆 Top Picks (Deep Analyzed)",
        'stage1_msg': "📡 Stage 1: Fetching Universe...",
        'stage2_msg': "✅ Stage 1 Complete. Analyzing Top Candidates...",
        'no_data': "❌ No stocks matched your STRICT criteria.",
        'deep_dive_title': "🔍 Single Stock Deep Dive",
        'glossary_title': "📚 Investment Glossary",
        'search_ticker': "Enter Stock Ticker (e.g. AAPL, PTT.BK)",
        'analyze_btn': "Analyze Stock",
        'about_title': "ℹ️ About This Project",
        'about_desc': "This program was created by Mr. Kun Poonkasetvatana. It was developed to solve the pain point that finding data is difficult, analyzing every stock takes too long, and similar tools are unreasonably expensive. Fetches data from Yahoo Finance to screen quickly. Currently developing AI to analyze fundamentals further, obeying 'Invest on what you know' and regular portfolio health checks."
    },
    'TH': {
        'sidebar_title': "🏛️ ตั้งค่าการสแกน",
        'market_label': "เลือกตลาดหุ้น",
        'strategy_label': "เลือกกลยุทธ์การลงทุน",
        'mode_header': "3. โหมดคัดกรอง",
        'strict_label': "เลือกค่าที่ต้องผ่านเกณฑ์ (Strict)",
        'perf_label': "เลือกช่วงเวลาวัดผลตอบแทน",
        'val_header': "📊 ค่าความถูกแพง (Valuation)",
        'prof_header': "📈 การทำกำไรและการเติบโต",
        'risk_header': "🛡️ ความเสี่ยง (หนี้สิน)",
        'execute_btn': "🚀 เริ่มสแกนหุ้น (2 ขั้นตอน)",
        'main_title': "📈 โปรแกรมสแกนหุ้น โดย kun p. & yahoo finance",
        'scan_limit': "จำกัดจำนวนสแกน", 
        'results_header': "🏆 หุ้นเด่น (วิเคราะห์เจาะลึก)",
        'stage1_msg': "📡 ขั้นแรก: ดึงข้อมูลหุ้น...",
        'stage2_msg': "✅ ขั้นแรกเสร็จสิ้น กำลังวิเคราะห์เจาะลึก...",
        'no_data': "❌ ไม่พบหุ้นที่ผ่านเกณฑ์ Strict ของคุณ",
        'deep_dive_title': "🔍 วิเคราะห์หุ้นรายตัว",
        'glossary_title': "📚 คลังความรู้การลงทุน",
        'search_ticker': "พิมพ์ชื่อหุ้น (เช่น AAPL, PTT.BK)",
        'analyze_btn': "วิเคราะห์หุ้นนี้",
        'about_title': "ℹ️ เกี่ยวกับโปรเจกต์นี้",
        'about_desc': "โปรแกรมนี้ ถูกจัดทำโดย นาย กัญจน์ พูนเกษตรวัฒนา โปรเจคนี้ถูกพัฒนาเพื่อการใช้งานส่วนตัวจากการเจอ pain point ที่ว่าการหาข้อมูลมันยุ่งยากมากๆ และ การที่จะนั่งวิเคราะห์หุ้นทุกๆตัวใช้เวลานานเกินไป และ เว็ปที่ทำคล้ายๆแบบนี้ก็เสียเงินแพงเกินใช่เหตุ จึงดึงข้อมูลมาจาก yahoo finance เพื่อคัดหุ้นจากข้อมูลพื้นฐานอย่างรวดเร็ว สิ่งที่กำลังพัฒนาอยู่ตอนนี้คือเรื่องของ ปัญญาประดิษฐ์ที่นำมาวิเคราะห์เรื่องปัจจัยพื้นฐานอีกที และ ทำให้เราเข้าใจสิ่งที่เราจะลงทุนก่อน โดยอิงจาก Invest on what you know และจะมีการตรวจเช็คสภาพรถเสมอ ในหุ้นในพอร์ตฟอลิโอ"
    }
}

def get_text(key):
    lang = st.session_state.get('lang', 'EN')
    return TRANS[lang].get(key, key)

# ---------------------------------------------------------
# 1. Page Configuration
# ---------------------------------------------------------
st.set_page_config(
    page_title="Stock Scanner by kun p.",
    page_icon="🏛️",
    layout="wide",
    initial_sidebar_state="expanded"
)

# Custom CSS for Professional Look
st.markdown("""
    <style>
    .stMetric {
        background-color: #f8f9fa;
        padding: 15px;
        border-radius: 8px;
        border: 1px solid #e9ecef;
    }
    .stDataFrame {
        font-family: 'IBM Plex Mono', 'Consolas', monospace;
        font-size: 0.95rem;
    }
    div[data-testid="stExpander"] div[role="button"] p {
        font-size: 1.1rem;
        font-weight: 600;
    }
    </style>
    """, unsafe_allow_html=True)

# ---------------------------------------------------------
# 2. Data Caching & Fetching
# ---------------------------------------------------------
@st.cache_data(ttl=86400)
def get_sp500_tickers():
    url = 'https://en.wikipedia.org/wiki/List_of_S%26P_500_companies'
    tables = pd.read_html(url, storage_options={'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36'})
    return tables[0]['Symbol'].tolist()

@st.cache_data(ttl=86400)
def get_set100_tickers():
    # Hardcoded Proxy for SET100 (Top Liquid Stocks)
    base_tickers = [
        "PTT", "AOT", "CPALL", "ADVANC", "GULF", "BDMS", "SCB", "KBANK", "PTTEP", "DELTA",
        "INTUCH", "CPN", "SCC", "MINT", "CRC", "TRUE", "BEM", "PTTGC", "IVL", "SCGP",
        "TOP", "EA", "HMPRO", "BBL", "KTB", "GPSC", "OR", "TU", "CPF", "TIDLOR", 
        "JMART", "JMT", "COM7", "CBG", "OSP", "MTC", "SAWAD", "BANPU", "LH", "WHA",
        "AMATA", "CENTEL", "KTC", "BJC", "TTB", "BH", "GLOBAL", "EGCO", "RATCH", "BGRIM",
        "STA", "KCE", "HANA", "TISCO", "BCP", "BPP", "KKP", "TASCO", "CK", "PLANB",
        "MEGA", "BAM", "TLI", "ITC", "AWC", "BCH", "STGT", "RCL", "SPALI", "AP"
    ]
    return [f"{t}.BK" for t in base_tickers]

@st.cache_data(ttl=86400)
def get_nasdaq_tickers():
    url = 'https://en.wikipedia.org/wiki/Nasdaq-100'
    tables = pd.read_html(url, match='Ticker', storage_options={'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36'})
    return tables[0]['Ticker'].tolist()

def safe_float(val):
    try:
        return float(val) if val is not None else None
    except:
        return None

# --- Stage 1: Fast Scan (Basic Metrics) ---
def scan_market_basic(tickers, progress_bar, status_text):
    data_list = []
    total = len(tickers)
    
    for i, ticker in enumerate(tickers):
        # Update UI every 5 items to reduce lag overhead
        # Update UI every 5 items to reduce lag overhead
        if i % 3 == 0: 
            progress = (i + 1) / total
            progress_bar.progress(progress)
        # Rate Limiting Prevention (Aggressive for Cloud)
        time.sleep(0.5)

        try:
            # Fix: Only replace dot with dash for US tickers
            if ".BK" in ticker: formatted_ticker = ticker
            else: formatted_ticker = ticker.replace('.', '-')
                
            stock = yf.Ticker(formatted_ticker, session=session) # Try passing session
            
            # 1. Try Fetching Full Info
            try:
                info = stock.info
            except: 
                info = {}
            
            # 2. Fallback to Fast Info if Info is empty
            fast_info = {}
            if not info or 'currentPrice' not in info:
                try: 
                    # fast_info is a property, returns an object, let's dict-ify it manually or access attrs
                    fi = stock.fast_info
                    if fi.last_price:
                        fast_info['currentPrice'] = fi.last_price
                        fast_info['previousClose'] = fi.previous_close
                        info['currentPrice'] = fi.last_price # Backfill
                        # fast_info doesn't have PE/PEG/etc.
                except: pass

            # Debug check
            if 'currentPrice' not in info:
                print(f"FAILED {ticker}: No Price Data") 
                continue
            
            # Found valid data
            status_text.caption(f"Stage 1: Scanning **{ticker}** ({i+1}/{total}) | ✅ Found: {len(data_list)+1}")
            
            if 'currentPrice' in info:
                price = safe_float(info.get('currentPrice', fast_info.get('currentPrice')))
                eps = safe_float(info.get('trailingEps'))
                book_val = safe_float(info.get('bookValue'))
                pe = safe_float(info.get('trailingPE'))
                growth_q = safe_float(info.get('earningsQuarterlyGrowth')) 
                peg = safe_float(info.get('pegRatio'))
                
                # Fix PEG
                if peg is None and pe is not None and growth_q is not None and growth_q > 0:
                    try: peg = pe / (growth_q * 100)
                    except: pass

                # --- NEW: REALISTIC FAIR VALUE ---
                # Primary: Analyst Consensus Target (Expert Opinion)
                analyst_target = safe_float(info.get('targetMeanPrice'))
                
                # Secondary: Lynch Fair Value (PE = Growth Rate)
                # If growth is 15%, Fair PE is 15. Fair Price = 15 * EPS.
                lynch_fv = None
                if eps and growth_q and growth_q > 0:
                    lynch_fv = eps * (growth_q * 100)
                
                # Logic: Use Analyst Target if available, else Lynch, or Average
                fair_value = analyst_target if analyst_target else lynch_fv
                
                margin_safety = 0
                if fair_value and price and fair_value != 0:
                    margin_safety = ((fair_value - price) / fair_value) * 100

                # Scale Percentages (Decimal -> %)
                roe = safe_float(info.get('returnOnEquity'))
                if roe: roe *= 100
                
                div_yield = safe_float(info.get('dividendYield'))
                # User requested raw for yield (reverted scaling)
                
                op_margin = safe_float(info.get('operatingMargins'))
                if op_margin: op_margin *= 100
                
                rev_growth = safe_float(info.get('revenueGrowth'))
                if rev_growth: rev_growth *= 100
                
                data_list.append({
                    'Symbol': formatted_ticker,
                    'Company': info.get('shortName', 'N/A'),
                    'Sector': info.get('sector', 'N/A'),
                    'Price': price,
                    'PE': pe,
                    'PEG': peg,
                    'PB': safe_float(info.get('priceToBook')),
                    'ROE': roe,
                    'Div_Yield': div_yield,
                    'Debt_Equity': safe_float(info.get('debtToEquity')), 
                    'EPS_Growth': growth_q,
                    'Rev_Growth': rev_growth, # Added for Speculative Strategy
                    'Op_Margin': op_margin,
                    'Target_Price': analyst_target,
                    'Fair_Value': fair_value,
                    'Margin_Safety': margin_safety,
                    'YF_Obj': stock 
                })
        except Exception:
            continue
            
    return pd.DataFrame(data_list)

# --- Stage 2: Deep Dive (Historical) ---
def analyze_history_deep(df_candidates, progress_bar, status_text):
    """
    Takes the surviving candidates and pulls history for deeper insight strings
    """
    total = len(df_candidates)
    enhanced_data = []
    
    for i, (idx, row) in enumerate(df_candidates.iterrows()):
        progress = (i + 1) / total
        progress_bar.progress(progress)
        ticker = row['Symbol']
        status_text.caption(f"Stage 2: Deep Analysis of **{ticker}** ({i+1}/{total})")
        
        stock = row['YF_Obj']
        
        # Metrics
        consistency_str = "N/A"
        insight_str = ""
        cagr_rev = None
        cagr_ni = None
        
        try:
            # 1. Financials (Income Statement)
            fin = stock.financials
            if not fin.empty:
                fin = fin.T.sort_index() # Oldest -> Newest
                years = len(fin)
                
                if years >= 3:
                    # Consistency (Net Income)
                    ni_series = fin['Net Income'].dropna()
                    if len(ni_series) > 1:
                        diffs = ni_series.diff().dropna()
                        pos_years = (diffs > 0).sum()
                        total_intervals = len(diffs)
                        consistency_str = f"{pos_years}/{total_intervals} Yrs"
                        
                        if pos_years == total_intervals:
                            insight_str += "✅ Consistent Growth "
                        elif pos_years <= total_intervals / 2:
                            insight_str += "⚠️ Earnings Volatile "
                            
                    # CAGR Calculation
                    try:
                        start_rev = fin['Total Revenue'].iloc[0]
                        end_rev = fin['Total Revenue'].iloc[-1]
                        val = (end_rev / start_rev) ** (1/(years-1)) - 1
                        cagr_rev = val * 100
                    except: pass
                    
                    try:
                        start_ni = fin['Net Income'].iloc[0]
                        end_ni = fin['Net Income'].iloc[-1]
                        val = (end_ni / start_ni) ** (1/(years-1)) - 1
                        cagr_ni = val * 100
                    except: pass
            
            # 2. Dividend History (For High Yield Analysis)
            # Fetch max history to find streak
            divs = stock.dividends
            if not divs.empty:
                # Resample to yearly to count years with dividends
                divs_yearly = divs.resample('Y').sum()
                divs_yearly = divs_yearly[divs_yearly > 0]
                
                if not divs_yearly.empty:
                    # Count consecutive years from the end
                    streak = 0
                    last_year = divs_yearly.index[-1].year
                    current_year = pd.Timestamp.now().year
                    
                    # If last dividend was this year or last year, it's active
                    if last_year >= current_year - 1:
                        years_list = sorted(divs_yearly.index.year.tolist(), reverse=True)
                        for k in range(len(years_list)):
                            if k == 0: 
                                streak = 1
                                continue
                            if years_list[k] == years_list[k-1] - 1:
                                streak += 1
                            else:
                                break
                    
                    if streak > 0:
                        div_streak_str = f"{streak} Yrs"
                        if streak >= 10: div_streak_str = f"💎 {streak} Yrs"
                        elif streak >= 5: div_streak_str = f"⭐ {streak} Yrs"
                    else:
                        div_streak_str = "0 Yrs"
                else:
                    div_streak_str = "0 Yrs"
            else:
                div_streak_str = "0 Yrs"

            # 3. Price Performance (NEW)
            hist = stock.history(period="5y")
            perf = {}
            if not hist.empty:
                # FIX: TZ awareness issues. Convert to naive.
                try:
                    hist.index = hist.index.tz_localize(None)
                except: pass
                
                curr_price = hist['Close'].iloc[-1]
                
                # Helper to get return
                def get_ret(days_ago):
                    try: 
                        # Use searchsorted to find closest date index
                        # Now strict Timestamp is naive, compatible with Index
                        target_idx = hist.index.searchsorted(pd.Timestamp.now() - pd.Timedelta(days=days_ago))
                        if target_idx < len(hist):
                            old_price = hist['Close'].iloc[target_idx]
                            val = (curr_price - old_price) / old_price
                            return val * 100
                    except: pass
                    return None

                perf['1M'] = get_ret(30)
                perf['3M'] = get_ret(90)
                perf['6M'] = get_ret(180)
                perf['1Y'] = get_ret(365)
                perf['3Y'] = get_ret(365*3)
                perf['5Y'] = get_ret(365*5)
                
                # YTD
                current_year = pd.Timestamp.now().year
                ytd_start = hist[hist.index.year < current_year]
                if not ytd_start.empty:
                    ytd_price = ytd_start['Close'].iloc[-1]
                    perf['YTD'] = ((curr_price - ytd_price) / ytd_price) * 100
                else:
                    perf['YTD'] = None

        except Exception:
            div_streak_str = "Error"
            perf = {}
            pass
        
        # Build Data Dict
        data_item = {
            'Symbol': ticker,
            'Rev_CAGR_5Y': cagr_rev,
            'NI_CAGR_5Y': cagr_ni,
            'Consistency': consistency_str,
            'Div_Streak': div_streak_str,
            'Insight': insight_str if insight_str else "Stable"
        }
        # Merge perf metrics
        data_item.update(perf)
        enhanced_data.append(data_item)
        
    return pd.DataFrame(enhanced_data)

# ---------------------------------------------------------
# 3. Classifications & Scoring
# ---------------------------------------------------------
def classify_lynch(row):
    growth = row.get('EPS_Growth')
    yield_pct = row.get('Div_Yield')
    pb = row.get('PB')
    sector = row.get('Sector')
    
    if growth is None: return "⚪ Unknown"
    if growth >= 0.20: return "🚀 Fast Grower"
    if pb is not None and pb < 1.0: return "🏰 Asset Play"
    if growth < 0.10 and yield_pct is not None and yield_pct > 0.03: return "🐢 Slow Grower"
    if 0.10 <= growth < 0.20: return "🐘 Stalwart"
    cyclical_sectors = ['Energy', 'Basic Materials', 'Consumer Cyclical', 'Real Estate', 'Industrials']
    if sector in cyclical_sectors: return "🔄 Cyclical"
    return "😐 Average"

def calculate_fit_score(row, targets):
    score = 0
    max_score = len(targets) * 10
    details = []

    for metric, target_val, operator in targets:
        actual_val = row.get(metric)
        if pd.isna(actual_val) or actual_val is None:
            details.append(f"⚪ N/A")
            continue

        hit = False
        diff = 0
        if operator == '<':
            if actual_val <= target_val:
                score += 10; hit = True
            else:
                diff = actual_val - target_val
                if diff <= target_val * 0.2: score += 5
                elif diff <= target_val * 0.5: score += 2
        elif operator == '>':
            if actual_val >= target_val:
                score += 10; hit = True
            else:
                diff = actual_val - target_val
                if abs(diff) <= target_val * 0.2: score += 5
                elif abs(diff) <= target_val * 0.5: score += 2

        if not hit:
            # Format nicely
            pct_off = (diff / target_val) * 100 if target_val != 0 else 0
            details.append(f"❌ {metric} ({pct_off:+.0f}%)")

    final_score = int((score / max_score) * 100) if max_score > 0 else 0
    analysis_str = ", ".join(details) if details else "✅ Perfect Match"
    return final_score, analysis_str

# ---------------------------------------------------------
# PAGES
# ---------------------------------------------------------

def page_scanner():
    st.sidebar.header(get_text('sidebar_title'))

    st.sidebar.subheader("1. Universe & Scale")
    market_choice = st.sidebar.selectbox(get_text('market_label'), ["S&P 500", "NASDAQ 100", "SET 100 (Thailand)"])
    num_stocks = st.sidebar.slider(get_text('scan_limit'), 10, 600, 50)
    top_n_deep = st.sidebar.slider("Analyze Top N Deeply (Stage 2)", 5, 50, 10)

    st.sidebar.markdown("---")
    st.sidebar.subheader("2. Strategy Mandate")
    strategy = st.sidebar.selectbox(get_text('strategy_label'), ["Custom", "Growth at Reasonable Price (GARP)", "Deep Value", "High Yield", "Speculative Growth"])

    st.sidebar.subheader(get_text('mode_header'))
    strict_criteria = st.sidebar.multiselect(get_text('strict_label'), 
                                             ["PE", "PEG", "ROE", "Op_Margin", "Div_Yield", "Debt_Equity"],
                                             default=[],
                                             help="Selected metrics must PASS the threshold or the stock is removed.")

    perf_metrics_select = st.sidebar.multiselect(get_text('perf_label'),
                                                ["1M", "3M", "6M", "YTD", "1Y", "3Y", "5Y"],
                                                default=["YTD", "1Y"],
                                                help="Show price return % for these periods.")

    t_peg, t_pe, t_roe, t_de, t_evebitda = 1.5, 25.0, 0.15, 100.0, 12.0
    t_div, t_margin = 0.0, 0.10
    t_rev_growth = 0.0

    if strategy == "Growth at Reasonable Price (GARP)":
        t_peg = 1.2; t_pe = 30.0; t_roe = 0.15
    elif strategy == "Deep Value":
        t_peg = 1.0; t_pe = 15.0; t_evebitda = 8.0; t_roe = 0.08
    elif strategy == "High Yield":
        t_div = 0.03; t_pe = 20.0; t_roe = 0.10
    elif strategy == "Speculative Growth":
        t_pe = 500.0; t_peg = 5.0; t_roe = 0.05; t_rev_growth = 20.0

    with st.sidebar.expander(get_text('val_header'), expanded=True):
        val_pe = st.slider("Max P/E Ratio", 5.0, 500.0, float(t_pe))
        val_peg = st.slider("Max PEG Ratio", 0.1, 10.0, float(t_peg))
        val_evebitda = st.slider("Max EV/EBITDA", 1.0, 50.0, float(t_evebitda))

    with st.sidebar.expander(get_text('prof_header'), expanded=True):
        prof_roe = st.slider("Min ROE %", 0, 50, int(t_roe*100)) / 100
        prof_margin = st.slider("Min Op Margin %", 0, 50, int(t_margin*100)) / 100
        prof_div = st.slider("Min Dividend Yield %", 0, 15, int(t_div*100)) / 100
        if strategy == "Speculative Growth":
            growth_min = st.slider("Min Revenue Growth %", 0, 100, int(t_rev_growth))

    with st.sidebar.expander(get_text('risk_header'), expanded=False):
        risk_de = st.slider("Max Debt/Equity %", 0, 500, int(t_de), step=10)

    # Main Dashboard
    st.title(get_text('main_title'))
    st.info(get_text('about_desc'))
    st.caption(f"Universe: {market_choice} | Strategy: {strategy} | Scan Limit: {num_stocks}")

    if 'scan_results' not in st.session_state: st.session_state['scan_results'] = None
    if 'deep_results' not in st.session_state: st.session_state['deep_results'] = None

    if st.button(get_text('execute_btn'), type="primary"):
        # --- STAGE 1 ---
        tickers = []
        with st.spinner(get_text('stage1_msg')):
            if market_choice == "S&P 500": tickers = get_sp500_tickers()
            elif market_choice == "NASDAQ 100": tickers = get_nasdaq_tickers()
            elif market_choice == "SET 100 (Thailand)": tickers = get_set100_tickers()
            tickers = tickers[:num_stocks]
        
        st.info(f"Stage 1: Scanning {len(tickers)} stocks...")
        df = scan_market_basic(tickers, st.progress(0), st.empty())

        if not df.empty:
            # Strict Logic
            if strict_criteria:
                original_len = len(df)
                if "PE" in strict_criteria: df = df[df['PE'].fillna(999) <= val_pe]
                if "PEG" in strict_criteria: df = df[df['PEG'].fillna(999) <= val_peg]
                if "ROE" in strict_criteria: df = df[df['ROE'].fillna(0) >= prof_roe]
                if "Op_Margin" in strict_criteria: df = df[df['Op_Margin'].fillna(0) >= prof_margin]
                if "Div_Yield" in strict_criteria: df = df[df['Div_Yield'].fillna(0) >= prof_div]
                if "Debt_Equity" in strict_criteria: df = df[df['Debt_Equity'].fillna(999) <= risk_de]
                st.warning(f"Strict Mode: {original_len} -> {len(df)} remaining")

            # Scoring Targets
            if strategy == "Speculative Growth":
                targets = [('Rev_Growth', float(growth_min), '>'), ('EPS_Growth', 0.15, '>'),
                           ('ROE', prof_roe, '>'), ('Debt_Equity', risk_de, '<')]
            else:
                targets = [('PEG', val_peg, '<'), ('PE', val_pe, '<'), ('ROE', prof_roe, '>'),
                           ('Op_Margin', prof_margin, '>'), ('Div_Yield', prof_div, '>'), ('Debt_Equity', risk_de, '<')]
            
            results = df.apply(lambda row: calculate_fit_score(row, targets), axis=1, result_type='expand')
            if not df.empty:
                df['Fit_Score'] = results[0]
                df['Analysis'] = results[1]
                df['Lynch_Category'] = df.apply(classify_lynch, axis=1)
                
                # Sort and Cut
                df = df.sort_values(by='Fit_Score', ascending=False)
                top_candidates = df.head(top_n_deep)
                
                # --- STAGE 2 ---
                st.success(get_text('stage2_msg'))
                time.sleep(0.5)
                deep_metrics = analyze_history_deep(top_candidates, st.progress(0), st.empty())
                final_df = top_candidates.merge(deep_metrics, on='Symbol', how='left')
                
                st.session_state['scan_results'] = df
                st.session_state['deep_results'] = final_df
            else:
                st.error(get_text('no_data'))
        else: st.error("No data found.")

    # Display Logic
    if st.session_state['deep_results'] is not None:
        final_df = st.session_state['deep_results']
        df = st.session_state['scan_results']
        currency_fmt = "฿%.2f" if "SET" in market_choice or (len(df) > 0 and ".BK" in str(df['Symbol'].iloc[0])) else "$%.2f"

        st.markdown(f"### {get_text('results_header')}")
        
        # Columns
        core_cols = ["Fit_Score", "Symbol", "Price"]
        if strategy == "High Yield": strat_cols = ["Div_Yield", "Div_Streak", "Fair_Value", "Margin_Safety", "Analysis"]
        elif strategy == "Deep Value": strat_cols = ["PE", "PB", "Lynch_Category", "Fair_Value", "Margin_Safety", "Analysis"]
        elif strategy == "Speculative Growth": strat_cols = ["Rev_Growth", "PEG", "Lynch_Category", "Fair_Value", "Analysis"]
        else: strat_cols = ["PEG", "Rev_CAGR_5Y", "NI_CAGR_5Y", "Fair_Value", "Margin_Safety", "Analysis"]
        
        perf_cols = [c for c in perf_metrics_select if c in final_df.columns]
        final_cols = core_cols + perf_cols + strat_cols

        col_config = {
            "Fit_Score": st.column_config.ProgressColumn("Score", format="%d", min_value=0, max_value=100),
            "Symbol": "Ticker", "Price": st.column_config.NumberColumn("Price", format=currency_fmt),
            "Fair_Value": st.column_config.NumberColumn("Fair Value", format=currency_fmt),
            "Margin_Safety": st.column_config.NumberColumn("Safety", format="%.1f%%"),
            "Rev_Growth": st.column_config.NumberColumn("Rev Growth (Q)", format="%.1f%%"),
            "Div_Yield": st.column_config.NumberColumn("Yield %", format="%.2f%%"),
            "Analysis": st.column_config.TextColumn("Details", width="large")
        }
        for p in ["1M", "3M", "6M", "YTD", "1Y", "3Y", "5Y"]:
            col_config[p] = st.column_config.NumberColumn(p, format="%.1f%%")

        st.dataframe(final_df, column_order=final_cols, column_config=col_config, hide_index=True, use_container_width=True)
        
        with st.expander("📋 View Stage 1 Data (All Scanned Stocks)"):
            st.dataframe(
                df.drop(columns=['YF_Obj']),
                column_config={
                    "Price": st.column_config.NumberColumn(format=currency_fmt),
                    "PE": st.column_config.NumberColumn(format="%.1f"),
                    "PEG": st.column_config.NumberColumn(format="%.2f"),
                    "ROE": st.column_config.NumberColumn(format="%.1f%%"),
                    "Div_Yield": st.column_config.NumberColumn(format="%.2f%%"),
                    "Op_Margin": st.column_config.NumberColumn(format="%.1f%%"),
                    "Debt_Equity": st.column_config.NumberColumn(format="%.0f%%"),
                    "Upside": st.column_config.NumberColumn(format="%.1f%%"),
                }
            ) 

        # --- Manual Deep Dive Section ---
        st.markdown("---")
        st.header("🔬 Interactive Historical Charts")
        st.info("Select a stock to visualize 10-year trends.")
        
        if 'Symbol' in df.columns:
            selected_ticker = st.selectbox("Select Ticker:", df['Symbol'].tolist(), index=0)
            
            # OPTION: Auto-display charts on selection (Better flow for user)
            # or use button. If button, we need to wrap it or it's fine now because parent blocks won't unrender
            if selected_ticker:
                with st.spinner(f"Pulling full history for {selected_ticker}..."):
                    # Use cached object if possible, or new fetch
                    # We stored YF_Obj in df, we can retrieve
                    try: # optimization
                        stock_obj = df.loc[df['Symbol'] == selected_ticker, 'YF_Obj'].values[0]
                    except:
                        stock_obj = yf.Ticker(selected_ticker.replace('-', '.'))
                    
                    fin_stmt = stock_obj.financials
                    if not fin_stmt.empty:
                        fin_T = fin_stmt.T.sort_index(ascending=True)
                        fin_T.index = pd.to_datetime(fin_T.index).year
                        
                        st.subheader(f"📊 {selected_ticker} Financials")
                        chart_cols = [c for c in ['Total Revenue', 'Net Income', 'EBITDA'] if c in fin_T.columns]
                        if chart_cols: st.line_chart(fin_T[chart_cols])
                        st.dataframe(fin_T.style.format("{:,.0f}")) # No currency symbol to be safe
                    else:
                        st.warning("No financial history available for this stock.")

        else:
            st.error(get_text('no_data'))
            st.session_state['scan_results'] = None
            st.session_state['deep_results'] = None

    else:
        st.info("Define parameters and start the Two-Stage Screening.")

# ---------------------------------------------------------
# PAGES: Single Stock & Glossary
# ---------------------------------------------------------

def page_single_stock():
    st.title(get_text('deep_dive_title'))
    ticker = st.text_input(get_text('search_ticker'))
    
    if st.button(get_text('analyze_btn')) and ticker:
        with st.spinner(f"Analyzing {ticker}..."):
            # Reuse logic by creating a 1-item list
            # We need to hack this a bit: pass empty progress bar
            class MockProgress:
                def progress(self, x): pass
            
            class MockStatus:
                def caption(self, x): pass
                def empty(self): pass
                
            df = scan_market_basic([ticker], MockProgress(), st.empty())
            
            if not df.empty:
                row = df.iloc[0]
                price = row['Price']
                
                # Top Header
                st.subheader(f"{row['Symbol']} - {row['Company']}")
                c1, c2, c3 = st.columns(3)
                c1.metric("Price", f"{price} {row.get('Currency', '')}")
                c1.metric("Sector", row['Sector'])
                
                # Fetch deeper data for context
                deep_metrics = analyze_history_deep(df, MockProgress(), st.empty())
                if not deep_metrics.empty:
                    deep_row = deep_metrics.iloc[0]
                    # Merge manually for display
                    for k, v in deep_row.items(): row[k] = v

                # strategy checks
                st.markdown("### 🎯 Strategy Fit Scorecard")
                
                c_s1, c_s2, c_s3 = st.columns(3)
                
                # 1. GARP Score
                score, details = calculate_fit_score(row, [('PEG', 1.2, '<'), ('EPS_Growth', 0.15, '>'), ('ROE', 15.0, '>')])
                c_s1.metric("GARP Score", f"{score}/100")
                if details != "✅ Perfect Match": c_s1.caption(details)

                # 2. Value Score
                score, details = calculate_fit_score(row, [('PE', 15.0, '<'), ('PB', 1.5, '<'), ('Debt_Equity', 50.0, '<')])
                c_s2.metric("Deep Value Score", f"{score}/100")
                if details != "✅ Perfect Match": c_s2.caption(details)
                
                # 3. Dividend Score
                score, details = calculate_fit_score(row, [('Div_Yield', 4.0, '>'), ('Op_Margin', 10.0, '>')])
                c_s3.metric("Dividend Score", f"{score}/100")
                if details != "✅ Perfect Match": c_s3.caption(details)
                
                st.markdown("---")
                st.subheader("🔍 Financial Health Check")
                col1, col2 = st.columns(2)
                
                with col1:
                    st.markdown("**Valuation**")
                    st.write(f"- P/E: **{row.get('PE', 0):.1f}**")
                    st.write(f"- PEG: **{row.get('PEG', 0):.2f}**")
                    st.write(f"- P/B: **{row.get('PB', 0):.2f}**")
                    st.write(f"- Fair Value: **{row.get('Fair_Value', 0):.2f}**")
                
                with col2:
                    st.markdown("**Quality**")
                    st.write(f"- ROE: **{row.get('ROE', 0):.1f}%**")
                    st.write(f"- Margin: **{row.get('Op_Margin', 0):.1f}%**")
                    st.write(f"- Debt/Equity: **{row.get('Debt_Equity', 0):.0f}%**")
                    st.write(f"- Dividend: **{row.get('Div_Yield', 0):.2f}%**")
                
                # Show Chart
                st.markdown("### 📉 5-Year Price Trend")
                stock = row['YF_Obj']
                hist = stock.history(period="5y")
                if not hist.empty:
                    st.line_chart(hist['Close'])

            else:
                st.error("Could not fetch data.")

def page_glossary():
    st.title(get_text('glossary_title'))
    

    
    with st.expander("P/E Ratio (Price-to-Earnings)", expanded=True):
        st.write("""
        **What it is:** The price you pay for $1 of earnings.
        - **Low (< 15)**: Cheap (Value stock) or dying company.
        - **High (> 30)**: Expensive, but market expects high growth.
        - **Why it matters:** Tells you if a stock is 'on sale' or 'overpriced'.
        """)
        
    with st.expander("PEG Ratio (Price/Earnings-to-Growth)"):
        st.write("""
        **What it is:** P/E Ratio divided by Growth Rate.
        - **< 1.0**: Undervalued (Growth is cheap).
        - **> 1.5**: Expensive relative to growth.
        - **Why it matters:** Better than P/E for growth stocks. A P/E of 50 is fine if growth is 50% (PEG = 1).
        """)
        
    with st.expander("ROE (Return on Equity)"):
        st.write("""
        **What it is:** How efficiently management uses your money.
        - **> 15%**: Great management (Warren Buffett likes this).
        - **< 10%**: Mediocre or capital intensive.
        - **Why it matters:** Shows quality. High ROE companies compound wealth faster.
        """)
    
    with st.expander("Dividend Yield"):
        st.write("""
        **What it is:** Annual cash return just for holding the stock.
        - **4-6%**: Good income.
        - **> 10%**: Danger zone (Yield trap?).
        - **Why it matters:** Income generation. Important for retirees.
        """)
    
    with st.expander("Debt/Equity Ratio"):
        st.write("""
        **What it is:** How much debt the company has vs. shareholder money.
        - **< 50%**: Safe.
        - **> 100%**: Risky (unless it's a bank or utility).
        - **Why it matters:** High debt kills companies during recessions.
        """)

# ---------------------------------------------------------
# MAIN ROUTER
# ---------------------------------------------------------
if __name__ == "__main__":
    st.sidebar.title("🌐 Language / ภาษา")
    lang_choice = st.sidebar.radio("Language / ภาษา", ["English (EN)", "Thai (TH)"], horizontal=True)
    st.session_state['lang'] = 'EN' if "English" in lang_choice else 'TH'

    st.sidebar.title("Menu")
    page = st.sidebar.radio("Go to", ["Scanner", "Single Stock", "Glossary"])
    
    if page == "Scanner":
        page_scanner()
    elif page == "Single Stock":
        page_single_stock()
    elif page == "Glossary":
        page_glossary()


