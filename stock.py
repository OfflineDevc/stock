import streamlit as st
import yfinance as yf
import altair as alt # Visuals
import pandas as pd
import numpy as np
import time

import datetime
from deep_translator import GoogleTranslator

# --- TRANSLATION HELPER ---
@st.cache_data(ttl=86400, show_spinner=False)
def translate_text(text, target_lang='th'):
    try:
        if not text: return ""
        # Chunking might be needed for very long text, but summaries are usually < 5000 chars
        translator = GoogleTranslator(source='auto', target=target_lang)
        return translator.translate(text)
    except Exception as e:
        return text # Fallback to original


# --- PROFESSIONAL UI OVERHAUL ---
def inject_custom_css():
    st.markdown("""
    <style>
        /* 1. Google Font: Inter (Professional & Minimal) */
        @import url('https://fonts.googleapis.com/css2?family=Inter:wght@300;400;600;700&display=swap');
        
        html, body, [class*="css"]  {
            font-family: 'Inter', sans-serif;
        }

        /* 2. Main Container Animation (Fade In) */
        .main .block-container {
            animation: fadeIn 0.8s ease-in-out;
        }

        @keyframes fadeIn {
            0% { opacity: 0; transform: translateY(10px); }
            100% { opacity: 1; transform: translateY(0); }
        }

        /* 3. Button Styling (Minimal & Rounded) */
        div.stButton > button {
            background-color: #f0f2f6; /* Soft Gray */
            color: #31333F;
            border: 1px solid #dbe2e8;
            border-radius: 12px; /* Smooth Rounding */
            font-weight: 600;
            padding: 0.5rem 1rem;
            transition: all 0.2s ease-in-out;
            box-shadow: 0 2px 4px rgba(0,0,0,0.05); /* Soft Shadow */
        }
        
        div.stButton > button:hover {
            transform: translateY(-2px); /* Lift Effect */
            box-shadow: 0 4px 8px rgba(0,0,0,0.1);
            border-color: #3b82f6; /* Blue Accent */
            background-color: #ffffff;
            color: #3b82f6;
        }
        
        div.stButton > button:active {
            transform: scale(0.98); /* Click Press Effect */
        }
        
        /* Primary Button (Generate) specialized */
        button[kind="primary"] {
            background: linear-gradient(135deg, #2563eb 0%, #1e40af 100%);
            color: white !important;
            border: none;
            box-shadow: 0 4px 6px rgba(37, 99, 235, 0.2);
        }
        
        button[kind="primary"]:hover {
            background: linear-gradient(135deg, #3b82f6 0%, #1d4ed8 100%);
            box-shadow: 0 6px 12px rgba(37, 99, 235, 0.3);
        }

        /* 4. Metric Cards (Card Look) */
        [data-testid="stMetric"] {
            background-color: #ffffff;
            padding: 1rem;
            border-radius: 12px;
            border: 1px solid #f0f2f6;
            box-shadow: 0 2px 4px rgba(0,0,0,0.02);
            transition: transform 0.2s;
        }
        
        [data-testid="stMetric"]:hover {
             transform: translateY(-2px);
             box-shadow: 0 4px 8px rgba(0,0,0,0.05);
        }

        /* 5. Expander Styling (Cleaner) */
        .streamlit-expanderHeader {
            background-color: #f8f9fa;
            border-radius: 8px;
            font-weight: 600;
        }
    </style>
    """, unsafe_allow_html=True)

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
        'sector_label': "Select Sectors (Optional)",
        'lynch_label': "Select Lynch Categories (Optional)",
        'execute_btn': "🚀 Execute 2-Stage Screen",
        'main_title': "📈 Stonk!!! by kun p. & yahoo finance",
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
        'about_desc': "This program was created by Mr. Kun Poonkasetvatana. It was developed to solve the pain point that finding data is difficult, analyzing every stock takes too long, and similar tools are unreasonably expensive. Fetches data from Yahoo Finance to screen quickly. Currently developing AI to analyze fundamentals further, obeying 'Invest on what you know' and regular portfolio health checks.",
        # --- NEW UI KEYS ---
        'scanner_config': "🛠️ Scanner Configuration & Settings",
        'univ_scale': "1. Universe & Scale",
        'strat_mandate': "2. Strategy Mandate",
        'crit_thresh': "3. Criteria Thresholds",
        'opt_filters': "Optional Filters",
        'analyze_top_n': "Analyze Top N Deeply (Stage 2)",
        
        'port_config': "⚙️ Portfolio Configuration & Settings",
        'asset_univ': "1. Asset Universe",
        'strat_prof': "2. Strategic Profile",
        'risk_tol': "Risk Tolerance / Strategy",
        'max_holdings': "Max Holdings Count",
        'gen_port_btn': "🚀 Generate Portfolio",
        'port_target_caption': "Allocating to top stocks using Market Cap Weighting.",
        
        'status_processing': "🔄 Processing Market Data...",
        'status_fetch': "📡 Fetching Ticker List...",
        'status_scan': "🔬 Scanning stocks for fundamentals...",
        'status_scan_fail': "❌ Scan Failed: No data found.",
        'status_scan_complete': "✅ Market Scan Complete!",
        'status_deep': "🔍 Deep Analysis (Financials & CAGR)...",
        'status_deep_complete': "✅ Deep Analysis Complete!",
        
        'tab_holdings': "📋 Holdings",
        'tab_alloc': "🍕 Allocation (Sector)",
        'tab_logic': "⚖️ Weighting Logic",
        'equity_holdings': "1. Equity Holdings (30%)",
        'core_assets': "2. Core Asset Allocation (70%)",
        'core_assets_desc': "These are standard ETF Proxies for the Asset Classes.",
        
        'risk_low_desc': "🛡️ **Defensive**: Focus on **Dividends** and **Stability**. Low Debt, steady Cash Flow. Good for preserving capital.",
        'risk_med_desc': "⚖️ **Balanced (GARP)**: Growth at Reasonable Price. Mix of **Value** and **Growth**. The sweet spot for most investors.",
        'risk_high_desc': "🚀 **Aggressive**: Focus on **High Growth**. Ignores Dividends. Higher Risk (Debt/Volatility) accepted for max returns.",
        'risk_all_desc': "🌤️ **All Weather**: Balanced across seasons. **40% Bonds** (Utilities), **30% Stocks** (Tech), **15% Cmdty** (Energy), **15% Cash** (Finance).",
        
        'menu_health': "Portfolio HealthCheck",
        'menu_ai': "Stock AI Analysis",
        'under_dev': "🚧 Feature Under Development 🚧",
        'dev_soon': "Check back soon for AI-powered diagnostics!",
        'dev_dl': "Coming soon: Deep Learning Fundamental Analysis.",
        'biz_summary': "📝 **Business Summary**",
        'lynch_type': "Lynch Type",
        'score_garp': "GARP Score",
        'score_value': "Deep Value Score",
        'score_div': "Dividend Score",
        'score_multi': "🚀 Multibagger Score",
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
        'sector_label': "เลือกกลุ่มอุตสาหกรรม (Optional)",
        'lynch_label': "เลือกประเภทหุ้นตาม Lynch (Optional)",
        'execute_btn': "🚀 เริ่มสแกนหุ้น (2 ขั้นตอน)",
        'main_title': "📈 โปรแกรมสแกนหุ้น Stonk!!! โดย kun p. & yahoo finance",
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
        'about_desc': "โปรแกรมนี้ ถูกจัดทำโดย นาย กัญจน์ พูนเกษตรวัฒนา โปรเจคนี้ถูกพัฒนาเพื่อการใช้งานส่วนตัวจากการเจอ pain point ที่ว่าการหาข้อมูลมันยุ่งยากมากๆ และ การที่จะนั่งวิเคราะห์หุ้นทุกๆตัวใช้เวลานานเกินไป และ เว็ปที่ทำคล้ายๆแบบนี้ก็เสียเงินแพงเกินใช่เหตุ จึงดึงข้อมูลมาจาก yahoo finance เพื่อคัดหุ้นจากข้อมูลพื้นฐานอย่างรวดเร็ว สิ่งที่กำลังพัฒนาอยู่ตอนนี้คือเรื่องของ ปัญญาประดิษฐ์ที่นำมาวิเคราะห์เรื่องปัจจัยพื้นฐานอีกที และ ทำให้เราเข้าใจสิ่งที่เราจะลงทุนก่อน โดยอิงจาก Invest on what you know และจะมีการตรวจเช็คสภาพรถเสมอ ในหุ้นในพอร์ตฟอลิโอ",
        
        # --- THAI TRANSLATIONS ---
        'scanner_config': "🛠️ ตั้งค่าตัวสแกนหุ้น (Scanner Configuration)",
        'univ_scale': "1. เลือกตลาดและขอบเขต (Universe)",
        'strat_mandate': "2. กลยุทธ์การลงทุน (Strategy)",
        'crit_thresh': "3. เกณฑ์ชี้วัด (Criteria Thresholds)",
        'opt_filters': "ตัวกรองเพิ่มเติม (Optional)",
        'analyze_top_n': "จำนวนหุ้นที่จะวิเคราะห์เจาะลึก (Stage 2)",
        
        'port_config': "⚙️ ตั้งค่าพอร์ตการลงทุน (Portfolio Settings)",
        'asset_univ': "1. เลือกสินทรัพย์ (Asset Universe)",
        'strat_prof': "2. รูปแบบกลยุทธ์ (Strategy Profile)",
        'risk_tol': "ระดับความเสี่ยง / กลยุทธ์",
        'max_holdings': "จำนวนหุ้นสูงสุดในพอร์ต",
        'gen_port_btn': "🚀 สร้างพอร์ตการลงทุน (Generate)",
        'port_target_caption': "จัดสรรเงินลงทุนในหุ้นชั้นนำ โดยใช้น้ำหนักตามมูลค่าตลาด (Market Cap Weighting)",
        
        'status_processing': "🔄 กำลังประมวลผลข้อมูลตลาด...",
        'status_fetch': "📡 กำลังดึงรายชื่อหุ้น...",
        'status_scan': "🔬 กำลังสแกนงบการเงินและพื้นฐาน...",
        'status_scan_fail': "❌ สแกนล้มเหลว: ไม่พบข้อมูล",
        'status_scan_complete': "✅ สแกนตลาดเรียบร้อย!",
        'status_deep': "🔍 วิเคราะห์เจาะลึก (งบการเงิน & CAGR)...",
        'status_deep_complete': "✅ วิเคราะห์เจาะลึกเสร็จสิ้น!",
        
        'tab_holdings': "📋 รายชื่อหุ้นในพอร์ต",
        'tab_alloc': "🍕 สัดส่วนการลงทุน (Allocation)",
        'tab_logic': "⚖️ ตรรกะการจัดพอร์ต",
        'equity_holdings': "1. ส่วนของหุ้น (Equity Holdings 30%)",
        'core_assets': "2. สินทรัพย์หลัก (Core Assets 70%)",
        'core_assets_desc': "นี่คือ ETF ตัวแทนของสินทรัพย์ประเภทต่างๆ (พันธบัตร, ทองคำ, etc.)",

        'risk_low_desc': "🛡️ **Defensive (ปลอดภัยไว้ก่อน)**: เน้น **ปันผล** และ **ความมั่นคง**. หนี้ต่ำ, กระแสเงินสดนิ่ง. เหมาะสำหรับรักษาเงินต้น.",
        'risk_med_desc': "⚖️ **Balanced (สายกลาง GARP)**: เติบโตในราคาที่เหมาะสม. ผสมผสานระหว่าง **ความคุ้มค่า** และ **การเติบโต**. จุดที่ลงตัวสำหรับนักลงทุนส่วนใหญ่.",
        'risk_high_desc': "🚀 **Aggressive (เชิงรุก)**: เน้น **การเติบโตสูง**. ไม่สนปันผล. ยอมรับความเสี่ยงสูง (หนี้/ความผันผวน) เพื่อแลกผลตอบแทนสูงสุด.",
        'risk_all_desc': "🌤️ **All Weather (ทุกสภาวะ)**: สมดุลทุกฤดูกาล. **40% พันธบัตร** (หรือ Utility), **30% หุ้น** (Tech), **15% สินค้าโภคภัณฑ์** (Energy), **15% เงินสด** (Finance).",
        
        'menu_health': "ตรวจสุขภาพพอร์ต (HealthCheck)",
        'menu_ai': "วิเคราะห์หุ้นด้วย AI",
        'under_dev': "🚧 ระบบกำลังพัฒนา 🚧",
        'dev_soon': "พบกับระบบตรวจสุขภาพพอร์ตด้วย AI เร็วๆ นี้!",
        'dev_dl': "พบกับการวิเคราะห์ปัจจัยพื้นฐานด้วย Deep Learning เร็วๆ นี้",
        'biz_summary': "📝 **สรุปข้อมูลธุรกิจ** (จาก Yahoo Finance)",
        'lynch_type': "ประเภท Lynch",
        'score_garp': "คะแนน GARP (เติบโตรอบคอบ)",
        'score_value': "คะแนน Value (หุ้นคุณค่า)",
        'score_div': "คะแนน Dividend (ปันผล)",
        'score_multi': "🚀 คะแนน Multibagger (หุ้นเด้ง)",
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
    /* .stMetric removed for Dark Mode compatibility */
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

def filter_dual_class(tickers):
    """
    Removes duplicate dual-class shares. 
    Preferences: GOOGL > GOOG, FOXA > FOX, NWSA > NWS, BRK.B > BRK.A
    """
    # Key = Keep, Value = Drop
    duals = {
        'GOOGL': 'GOOG',
        'FOXA': 'FOX',
        'NWSA': 'NWS',
        'BRK.B': 'BRK.A',
        'BRK-B': 'BRK-A' 
    }
    
    final_list = list(tickers)
    for keep, drop in duals.items():
        if keep in final_list and drop in final_list:
            final_list.remove(drop)
            
    return final_list

@st.cache_data(ttl=86400)
def get_sp500_tickers():
    url = 'https://en.wikipedia.org/wiki/List_of_S%26P_500_companies'
    tables = pd.read_html(url, storage_options={'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36'})
    raw_tickers = tables[0]['Symbol'].tolist()
    return filter_dual_class(raw_tickers)

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
    raw_tickers = tables[0]['Ticker'].tolist()
    return filter_dual_class(raw_tickers)


def safe_float(val):
    try:
        return float(val) if val is not None else None
    except:
        return None

# --- Stage 1: Fast Scan (Basic Metrics) ---
def scan_market_basic(tickers, progress_bar, status_text, debug_container=None):
    data_list = []
    total = len(tickers)
    
    # --- BULK DOWNLOAD STRATEGY (Anti-Blocking) ---
    status_text.text("Stage 1: Bulk Downloading Prices...")
    price_map = {}
    
    try:
        dl_tickers = [t.replace('.', '-') if ".BK" not in t else t for t in tickers]
        if debug_container: debug_container.write(f"Attempting download for {len(dl_tickers)} tickers...")
        
        # Download 1 day of data
        bulk = yf.download(dl_tickers, period="1d", group_by='ticker', progress=False, auto_adjust=True)
        
        if debug_container: 
            debug_container.write(f"Bulk Shape: {bulk.shape}")
            debug_container.write(f"Bulk Cols: {bulk.columns}")
            if not bulk.empty: debug_container.write(f"Sample: {bulk.iloc[:, :2].head()}")
        
        # Parse MultiIndex
        if len(dl_tickers) == 1:
            t = dl_tickers[0]
            if not bulk.empty:
                try: 
                    # Handle different 1-ticker shapes
                    if 'Close' in bulk.columns: p = bulk['Close'].iloc[-1]
                    else: p = bulk.iloc[0,0] # Fallback blindly
                    price_map[t] = p
                except Exception as e:
                    if debug_container: debug_container.error(f"1-Ticker Parse Error: {e}")
        else:
            for t in dl_tickers:
                try:
                    # Check if ticker in columns (Level 0)
                    if t in bulk.columns:
                        p = bulk[t]['Close'].iloc[-1]
                        if not pd.isna(p): price_map[t] = p
                except: pass
                
        if debug_container: debug_container.write(f"Price Map Keys: {list(price_map.keys())[:5]}")
        
    except Exception as e:
        print(f"Bulk DL Failed: {e}")
        if debug_container: debug_container.error(f"Bulk DL Exception: {e}")

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
                
            stock = yf.Ticker(formatted_ticker)
            
            # 1. Get Price from Bulk (Fast, Reliable)
            price = price_map.get(formatted_ticker)
            
            # 2. Try Fetching Fundamentals (Info)
            try: info = stock.info
            except: info = {}
            
            # DEBUG: Log first item to see what's happening on Cloud
            if i == 0 and debug_container:
                pass # Clean logs
            
            # Fallback Price if not in Bulk
            if not price and 'currentPrice' in info:
                price = safe_float(info.get('currentPrice'))
            
            # Skip if no price at all
            if not price:
                 # Last ditch: fast_info
                try: 
                    fi = stock.fast_info
                    if fi.last_price: price = fi.last_price
                except: pass
            
            if not price:
                print(f"FAILED {ticker}: No Price Data") 
                continue
            
            # Found data (Price at least)
            status_text.caption(f"Stage 1: Analyzing **{ticker}** | ✅ Found: {len(data_list)+1}")
            
            # Use found price, treat info as optional but preferred
            if price:
                # Extract Fundamentals (might be None if info failed)
                eps = safe_float(info.get('trailingEps'))
                book_val = safe_float(info.get('bookValue'))
                pe = safe_float(info.get('trailingPE'))
                
                # Auto-Calc PE if missing
                if pe is None and price and eps and eps > 0:
                    pe = price / eps
                    
                growth_q = safe_float(info.get('earningsQuarterlyGrowth')) 
                # Fallback Growth (Yearly)
                if growth_q is None:
                    growth_q = safe_float(info.get('earningsGrowth'))

                peg = safe_float(info.get('pegRatio'))
                
                # Fallback: Try Trailing PEG (if Forward PEG is missing)
                if peg is None:
                    peg = safe_float(info.get('trailingPegRatio'))
                
                # Fix PEG (Manual Calc)
                if peg is None and pe is not None and growth_q is not None and growth_q > 0:
                    try: peg = pe / (growth_q * 100)
                    except: pass

                
                # Init variables potentially missing from empty 'info'
                roe = None
                op_margin = None
                div_yield = None
                debt_equity = None

                # --- NEW: MANUAL EPS/PE RECOVERY (If Cloud Blocked Key Metrics) ---
                if (pe is None) and price: # Check PE primarily, others follow
                    try:
                        # Fetch Financials (Income Stmt & Balance Sheet)
                        inc = stock.quarterly_income_stmt
                        bal = stock.quarterly_balance_sheet
                        
                        if i == 0 and debug_container:
                            debug_container.write(f"🔍 Analying {formatted_ticker} (Cloud Recovery Mode)")
                        
                        eps_ttm = None
                        
                        eps_ttm = None
                        net_income_ttm = None
                        op_income_ttm = None
                        revenue_ttm = None
                        
                        # Helper for TTM
                        def get_ttm(df, label):
                            if label in df.index:
                                s = pd.to_numeric(df.loc[label], errors='coerce')
                                return s.iloc[:4].sum()
                            return None

                        # INCOME STATEMENT METRICS (TTM)
                        if not inc.empty:
                            # EPS
                            eps_ttm = get_ttm(inc, 'Diluted EPS')
                            if eps_ttm and eps_ttm > 0:
                                eps = eps_ttm
                                if price: pe = price / eps_ttm if pe is None else pe
                            
                            # Net Income (for ROE)
                            net_income_ttm = get_ttm(inc, 'Net Income')
                            if net_income_ttm is None: net_income_ttm = get_ttm(inc, 'Net Income Common Stockholders')

                            # Op Income (for Margin)
                            op_income_ttm = get_ttm(inc, 'Operating Income')
                            if op_income_ttm is None: op_income_ttm = get_ttm(inc, 'Total Operating Income As Reported')
                                
                            # Revenue (for Margin)
                            revenue_ttm = get_ttm(inc, 'Total Revenue')
                            
                            # Operating Margin Calculation
                            if op_income_ttm and revenue_ttm and revenue_ttm > 0:
                                op_margin = (op_income_ttm / revenue_ttm) * 100

                        # BALANCE SHEET METRICS (Latest Quarter)
                        if not bal.empty:
                            # Stockholders Equity (for ROE, Debt/Eq)
                            equity = None
                            if 'Stockholders Equity' in bal.index:
                                equity = pd.to_numeric(bal.loc['Stockholders Equity'], errors='coerce').iloc[0]
                            elif 'Total Equity Gross Minority Interest' in bal.index: 
                                equity = pd.to_numeric(bal.loc['Total Equity Gross Minority Interest'], errors='coerce').iloc[0]
                            
                            # ROE Calculation
                            if roe is None and net_income_ttm and equity and equity > 0:
                                roe = (net_income_ttm / equity) * 100
                                
                            # Debt/Equity Calculation
                            if debt_equity is None and equity and equity > 0:
                                total_debt = 0
                                if 'Total Debt' in bal.index:
                                    total_debt = pd.to_numeric(bal.loc['Total Debt'], errors='coerce').iloc[0]
                                debt_equity = (total_debt / equity) * 100

                        # DIVIDEND YIELD RECOVERY - REMOVED AS REQUESTED (User: "Don't use formula")
                        # if div_yield is None: ... (Removed)

                    except Exception as e:
                        if i == 0 and debug_container: debug_container.error(f"Recovery ERROR: {e}")
                        pass
                
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

                # Scale Percentages (Decimal -> %) - ONLY if not already recovered
                if roe is None:
                    roe = safe_float(info.get('returnOnEquity'))
                    if roe is not None: roe *= 100
                if div_yield is None:
                    # Prefer Trailing Annual (Real paid) over Forward (Projected)
                    div_yield = safe_float(info.get('trailingAnnualDividendYield'))
                    if div_yield is None:
                        div_yield = safe_float(info.get('dividendYield'))
                    
                    
                    # Auto-Fix: Yahoo usually sends 0.05 for 5%. 
                    # If we get > 1.0 (e.g. 5.0), it's likely a scaling error.
                    if div_yield is not None and div_yield > 1.0: 
                        div_yield /= 100.0
                if op_margin is None:
                    op_margin = safe_float(info.get('operatingMargins'))
                    if op_margin is not None: op_margin *= 100
                
                rev_growth = safe_float(info.get('revenueGrowth'))
                if rev_growth is not None: rev_growth *= 100
                
                data_list.append({
                    'Symbol': formatted_ticker,
                    'Company': info.get('shortName', 'N/A'),
                    'Sector': info.get('sector', 'N/A'),
                    'Market_Cap': info.get('marketCap', 0), # Added for Weighting
                    'Price': price,
                    'PE': pe,
                    'PEG': peg,
                    'PB': safe_float(info.get('priceToBook')),
                    'ROE': roe,
                    'Div_Yield': div_yield,
                    'Debt_Equity': debt_equity if debt_equity is not None else safe_float(info.get('debtToEquity')), 
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
                # FIX: 'Y' is deprecated, use 'YE'
                divs_yearly = divs.resample('YE').sum()
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
    valid_targets_count = 0 
    details = []

    # Safe Defaults (Penalty Logic)
    # If a value is missing, we assign the WORST POSSIBLE value to ensure it fails the check.
    
    for metric, target_val, operator in targets:
        actual_val = row.get(metric)
        passed_val = actual_val
        is_missing = pd.isna(actual_val) or actual_val is None
        
        # Assign Penalty Value if Missing
        if is_missing:
            # Low is Better -> Penalty: High (9999)
            if metric in ['PE', 'PEG', 'Debt_Equity', 'PB']:
                passed_val = 9999.0 
            # High is Better -> Penalty: Low (-9999)
            elif metric in ['ROE', 'Op_Margin', 'Rev_Growth', 'EPS_Growth', 'Div_Yield']:
                passed_val = -9999.0 
            else:
                passed_val = 0.0 # Neutral fallback

        # We count it as a valid check (it will just fail)
        valid_targets_count += 1

        hit = False
        diff = 0
        
        # Check against Target
        if operator == '<':
            if passed_val <= target_val:
                score += 10; hit = True
            else:
                # Calculate diff using passed_val (could be penalty)
                diff = passed_val - target_val
                # Only give partial points if NOT missing
                if not is_missing:
                    if diff <= target_val * 0.2: score += 5
                    elif diff <= target_val * 0.5: score += 2
        elif operator == '>':
            if passed_val >= target_val:
                score += 10; hit = True
            else:
                if not is_missing:
                    # Calculate diff for logic, though penalties are huge
                    diff = passed_val - target_val 
                    if abs(diff) <= target_val * 0.2: score += 5
                    elif abs(diff) <= target_val * 0.5: score += 2

        if not hit:
            if is_missing:
                 # Explicit N/A Failure
                 details.append(f"❌ {metric} (N/A -> Fail)")
            else:
                 pct_off = (diff / target_val) * 100 if target_val != 0 else 0
                 details.append(f"❌ {metric} ({pct_off:+.0f}%)")
        else:
             details.append(f"✅ {metric}")

    max_score = valid_targets_count * 10
    final_score = int((score / max_score) * 100) if max_score > 0 else 0
    analysis_str = ", ".join(details) if details else "✅ Perfect Match"
    return final_score, analysis_str

# ---------------------------------------------------------
# PAGES
# ---------------------------------------------------------

def page_scanner():
    st.title(get_text('main_title'))
    st.info(get_text('about_desc'))

    # --- PROFESSIONAL UI: MAIN CONFIGURATION ---
    # Moved all controls from Sidebar to Main Page Expander
    with st.expander("🛠️ **Scanner Configuration & Settings**", expanded=True):
        
        # Row 1: High Level Strategy
        c_uni, c_strat = st.columns(2)
        with c_uni:
             st.subheader("1. Universe & Scale")
             market_choice = st.selectbox(get_text('market_label'), ["S&P 500", "NASDAQ 100", "SET 100 (Thailand)"])
             num_stocks = st.slider(get_text('scan_limit'), 10, 503, 50)
             top_n_deep = st.slider("Analyze Top N Deeply (Stage 2)", 5, 50, 10)
        
        with c_strat:
             st.subheader("2. Strategy Mandate")
             strategy = st.selectbox(get_text('strategy_label'), ["Custom", "Growth at Reasonable Price (GARP)", "Deep Value", "High Yield", "Speculative Growth"])
             
             # Mode & Period
             strict_criteria = st.multiselect(get_text('strict_label'), 
                                                  ["PE", "PEG", "ROE", "Op_Margin", "Div_Yield", "Debt_Equity"],
                                                  default=[],
                                                  help="Selected metrics must PASS the threshold or the stock is removed.")
             perf_metrics_select = st.multiselect(get_text('perf_label'),
                                                     ["1M", "3M", "6M", "YTD", "1Y", "3Y", "5Y"],
                                                     default=["YTD", "1Y"],
                                                     help="Show price return % for these periods.")

        st.markdown("---")
        
        # Row 2: Detailed Thresholds
        st.subheader("3. Criteria Thresholds")
        
        # Defaults
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
            
        c_val, c_prof, c_risk = st.columns(3)
        
        with c_val:
             st.markdown(f"**{get_text('val_header')}**")
             val_pe = st.slider("Max P/E Ratio", 5.0, 500.0, float(t_pe))
             val_peg = st.slider("Max PEG Ratio", 0.1, 10.0, float(t_peg))
             val_evebitda = st.slider("Max EV/EBITDA", 1.0, 50.0, float(t_evebitda))
             
        with c_prof:
             st.markdown(f"**{get_text('prof_header')}**")
             prof_roe = st.slider("Min ROE %", 0, 50, int(t_roe*100)) / 100
             prof_margin = st.slider("Min Op Margin %", 0, 50, int(t_margin*100)) / 100
             prof_div = st.slider("Min Dividend Yield %", 0, 15, int(t_div*100)) / 100
             if strategy == "Speculative Growth":
                 growth_min = st.slider("Min Revenue Growth %", 0, 100, int(t_rev_growth))
        
        with c_risk:
             st.markdown(f"**{get_text('risk_header')}**")
             risk_de = st.slider("Max Debt/Equity %", 0, 500, int(t_de), step=10)
             
             # Filters
             st.caption("Optional Filters")
             SECTORS = [
                "Technology", "Healthcare", "Financial Services", "Consumer Cyclical", 
                "Industrials", "Consumer Defensive", "Energy", "Utilities", 
                "Basic Materials", "Real Estate", "Communication Services"
            ]
             selected_sectors = st.multiselect(get_text('sector_label'), SECTORS, default=[])
            
             LYNCH_TYPES = [
                "🚀 Fast Grower", "🏰 Asset Play", "🐢 Slow Grower", 
                "🐘 Stalwart", "🔄 Cyclical", "😐 Average", "⚪ Unknown"
            ]
             selected_lynch = st.multiselect(get_text('lynch_label'), LYNCH_TYPES, default=[])

    st.caption(f"Universe: {market_choice} | Strategy: {strategy} | Scan Limit: {num_stocks}")

    if 'scan_results' not in st.session_state: st.session_state['scan_results'] = None
    if 'deep_results' not in st.session_state: st.session_state['deep_results'] = None

    
    # DEBUG EXPANDER
    debug_container = st.expander("🛠️ Debug Logs (Open if No Data)", expanded=False)

    if st.button(get_text('execute_btn'), type="primary"):
        # --- STAGE 1 ---
        tickers = []
        with st.spinner(get_text('stage1_msg')):
            if market_choice == "S&P 500": tickers = get_sp500_tickers()
            elif market_choice == "NASDAQ 100": tickers = get_nasdaq_tickers()
            elif market_choice == "SET 100 (Thailand)": tickers = get_set100_tickers()
            tickers = tickers[:num_stocks]
        
        st.info(f"Stage 1: Scanning {len(tickers)} stocks...")
        df = scan_market_basic(tickers, st.progress(0), st.empty(), debug_container)

        if not df.empty:
            original_len = len(df)
            
            # Strict Logic
            if strict_criteria:
                if "PE" in strict_criteria: df = df[df['PE'].fillna(999) <= val_pe]
                if "PEG" in strict_criteria: df = df[df['PEG'].fillna(999) <= val_peg]
                if "ROE" in strict_criteria: df = df[df['ROE'].fillna(0) >= prof_roe]
                if "Op_Margin" in strict_criteria: df = df[df['Op_Margin'].fillna(0) >= prof_margin]
                if "Div_Yield" in strict_criteria: df = df[df['Div_Yield'].fillna(0) >= prof_div]
                if "Debt_Equity" in strict_criteria: df = df[df['Debt_Equity'].fillna(999) <= risk_de]
                
            # Sector Filtering (Pre-Result)
            if selected_sectors:
                df = df[df['Sector'].isin(selected_sectors)]
                
            if strict_criteria or selected_sectors:
                st.warning(f"Strict/Filter Mode: {original_len} -> {len(df)} remaining")

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
                
                # Lynch Filtering (Post-Calc)
                if selected_lynch:
                    df = df[df['Lynch_Category'].isin(selected_lynch)]
                
                # Sort and Cut
                if 'Market_Cap' in df.columns:
                     df = df.sort_values(by=['Fit_Score', 'Market_Cap'], ascending=[False, False])
                else:
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

        if 'YF_Obj' in final_df.columns:
            display_df = final_df.drop(columns=['YF_Obj'])
        else:
            display_df = final_df

        st.dataframe(display_df, column_order=final_cols, column_config=col_config, hide_index=True, width="stretch")
        
        # Cloud Warning Check: If we have results but Scores are 0 (Limited Data)
        if 'Fit_Score' in final_df.columns and (final_df['Fit_Score'] == 0).all():
            st.warning("⚠️ **Data Recovery Mode Active**: Advanced metrics (P/E, ROE) were manually calculated from financial statements due to Cloud restrictions.")
        else:
            if final_df.shape[0] > 0 and 'YF_Obj' not in final_df.columns:
                 # Check if we have many N/A in key columns
                 if final_df['PE'].isna().sum() > len(final_df) * 0.5:
                      st.warning("⚠️ **Cloud Data Limitation**: Some advanced metrics might be missing. Using manual recovery where possible.")
        
        with st.expander("📋 View Stage 1 Data (All Scanned Stocks)"):
            # FIX: Drop YF_Obj to avoid Arrow Serialization Error
            if 'YF_Obj' in df.columns: dump_df = df.drop(columns=['YF_Obj'])
            else: dump_df = df
            
            st.dataframe(
                dump_df,
                column_config={
                    "Price": st.column_config.NumberColumn(format=currency_fmt),
                    "PE": st.column_config.NumberColumn(format="%.1f"),
                    "PEG": st.column_config.NumberColumn(format="%.2f"),
                    "ROE": st.column_config.NumberColumn(format="%.1f%%"),
                    "Div_Yield": st.column_config.NumberColumn(format="%.2f%%"),
                    "Op_Margin": st.column_config.NumberColumn(format="%.1f%%"),
                    "Debt_Equity": st.column_config.NumberColumn(format="%.0f%%"),
                    "Upside": st.column_config.NumberColumn(format="%.1f%%"),
                },
                width="stretch"
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
                
                # Calculate Lynch Category if missing
                lynch_cat = row.get('Lynch_Category')
                if not lynch_cat:
                    lynch_cat = classify_lynch(row)
                
                if not lynch_cat:
                    lynch_cat = classify_lynch(row)
                
                c1, c2, c3 = st.columns(3)
                c1.metric("Price", f"{price} {row.get('Currency', '')}")
                c2.metric("Sector", row['Sector'])
                c3.metric(get_text('lynch_type'), lynch_cat)
                
                # Fetch deeper data for context
                deep_metrics = analyze_history_deep(df, MockProgress(), st.empty())
                if not deep_metrics.empty:
                    deep_row = deep_metrics.iloc[0]
                    # Merge manually for display
                    for k, v in deep_row.items(): row[k] = v

                # NEW: Business Summary
                try:
                    stock_obj = row['YF_Obj']
                    summary = stock_obj.info.get('longBusinessSummary')
                    if summary:
                         # Translate if TH selected
                         if st.session_state.get('lang', 'EN') == 'TH':
                             summary = translate_text(summary, 'th')

                         with st.expander(f"{get_text('biz_summary')}: {row['Company']}", expanded=False):
                             st.write(summary)
                except: pass

                # strategy checks
                st.markdown("### 🎯 Strategy Fit Scorecard")
                
                c_s1, c_s2, c_s3 = st.columns(3)
                
                # 1. GARP Score
                score, details = calculate_fit_score(row, [('PEG', 1.2, '<'), ('EPS_Growth', 0.15, '>'), ('ROE', 15.0, '>')])
                c_s1.metric(get_text('score_garp'), f"{score}/100")
                if details != "✅ Perfect Match": c_s1.caption(details)

                # 2. Value Score
                score, details = calculate_fit_score(row, [('PE', 15.0, '<'), ('PB', 1.5, '<'), ('Debt_Equity', 50.0, '<')])
                c_s2.metric(get_text('score_value'), f"{score}/100")
                if details != "✅ Perfect Match": c_s2.caption(details)
                
                # 3. Dividend Score
                score, details = calculate_fit_score(row, [('Div_Yield', 4.0, '>'), ('Op_Margin', 10.0, '>')])
                c_s3.metric(get_text('score_div'), f"{score}/100")
                if details != "✅ Perfect Match": c_s3.caption(details)

                # 4. Multibagger Score (New)
                c_s4 = c_s1 # Reuse or create new row? Let's use correct layout.
                # Actually let's just make it 4 columns if space permits
                
                # RE-LAYOUT to 4 COLUMNS
                # But st.columns(3) is above. I need to edit the column setup to make it work gracefully.
                # Since I am in 'multi_replace', I can't easily change the `st.columns(3)` line which is far above line 1137.
                # I'll just append it to the bottom or use expander.
                
                st.caption("---")
                c_m1, c_m2 = st.columns(2)
                score, details = calculate_fit_score(row, [('Rev_Growth', 30.0, '>'), ('EPS_Growth', 20.0, '>'), ('PEG', 2.0, '<')])
                c_m1.metric(get_text('score_multi'), f"{score}/100")
                if details != "✅ Perfect Match": c_m1.caption(details)
                
                st.markdown("---")
                st.subheader("🔍 Financial Health Check")
                col1, col2 = st.columns(2)
                
                with col1:
                    st.markdown("**Valuation**")
                    st.write(f"- P/E: **{row.get('PE') if row.get('PE') is not None else 0:.1f}**")
                    st.write(f"- PEG: **{row.get('PEG') if row.get('PEG') is not None else 0:.2f}**")
                    st.write(f"- P/B: **{row.get('PB') if row.get('PB') is not None else 0:.2f}**")
                    st.write(f"- Fair Value: **{row.get('Fair_Value') if row.get('Fair_Value') is not None else 0:.2f}**")
                
                with col2:
                    st.markdown("**Quality**")
                    st.write(f"- ROE: **{row.get('ROE') if row.get('ROE') is not None else 0:.1f}%**")
                    st.write(f"- Margin: **{row.get('Op_Margin') if row.get('Op_Margin') is not None else 0:.1f}%**")
                    st.write(f"- Debt/Equity: **{row.get('Debt_Equity') if row.get('Debt_Equity') is not None else 0:.0f}%**")
                    st.write(f"- Dividend: **{row.get('Div_Yield') if row.get('Div_Yield') is not None else 0:.2f}%**")
                
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
    lang = st.session_state.get('lang', 'EN')

    tab1, tab2, tab3 = st.tabs(["🎛️ Settings & Tools", "📊 Financial Metrics", "🧠 Peter Lynch Categories"])

    # ==========================================
    # 1. SETTINGS & TOOLS
    # ==========================================
    with tab1:
        SETTINGS_DATA = {
            'Universe': {
                'EN': {
                    'title': "Universe & Scale",
                    'desc': "Where are we looking for stocks?",
                    'details': [
                        "**S&P 500**: 500 largest companies in the US. Stable, standard.",
                        "**NASDAQ 100**: Top 100 non-financial US companies. Heavy on Tech.",
                        "**SET 100**: Top 100 liquid stocks in Thailand.",
                        "**Scan Limit**: How many stocks to fetch initially. Higher = Slower but more complete.",
                        "**Deep Analyze (Stage 2)**: We only download full price history for the 'Winners' of Stage 1 to save time."
                    ]
                },
                'TH': {
                    'title': "ตลาดและขอบเขต (Universe)",
                    'desc': "เรากำลังหาหุ้นจากตระกร้าไหน?",
                    'details': [
                        "**S&P 500**: 500 บริษัทใหญ่สุดในอเมริกา (มาตรฐานโลก)",
                        "**NASDAQ 100**: 100 บริษัทเน้นเทคโนโลยีในอเมริกา (ซิ่งกว่า)",
                        "**SET 100**: 100 หุ้นสภาพคล่องสูงในไทย",
                        "**Scan Limit**: จำนวนหุ้นที่จะสแกนรอบแรก ยิ่งเยอะยิ่งเจอนาน",
                        "**Deep Analyze**: ระบบจะดึงงบย้อนหลัง 5-10 ปี เฉพาะตัวที่ผ่านเข้ารอบสุดท้ายเท่านั้น เพื่อความรวดเร็ว"
                    ]
                }
            },
            'Strategy': {
                'EN': {
                    'title': "Strategy Mandate",
                    'desc': "Preset filters for different investment styles.",
                    'details': [
                        "**GARP**: Growth at Reasonable Price. Good companies not too expensive.",
                        "**Deep Value**: Ugly cheap companies. High risk, high reward if they survive.",
                        "**High Yield**: Dividend focus. For income seekers.",
                        "**Speculative**: Betting on future growth. Ignore current profits."
                    ]
                },
                'TH': {
                    'title': "กลยุทธ์การลงทุน (Strategy)",
                    'desc': "สูตรสำเร็จสำหรับการคัดกรองหุ้นสไตล์ต่างๆ",
                    'details': [
                        "**GARP**: หุ้นเติบโตในราคาที่สมเหตุสมผล (สายกลาง)",
                        "**Deep Value**: หุ้นถูกจัดๆ (อาจจะมีปัญหาชั่วคราว) กำไรเยอะถ้าฟื้นตัว",
                        "**High Yield**: เน้นปันผลสูง กินดอกเบี้ย",
                        "**Speculative**: เก็งกำไรอนาคต ไม่สน P/E สนแค่ยอดขายโตไหม"
                    ]
                }
            },
            'Strict': {
                'EN': {
                    'title': "Strict Mode & Filters",
                    'desc': "Hard pass criteria. If a stock fails these, it is deleted immediately.",
                    'details': [
                        "**Strict Mode**: Checked metrics must pass the threshold. PROHIBITS bad stocks.",
                        "**Sector Filter**: Only look at specific industries.",
                        "**Timeframes (YTD, 1Y)**: Measure price performance over these periods."
                    ]
                },
                'TH': {
                    'title': "โหมดเข้มงวด (Strict Mode)",
                    'desc': "เกณฑ์ที่ 'ห้ามพลาด' โดยเด็ดขาด",
                    'details': [
                        "**Strict Mode**: ถ้าติ๊กเลือกค่าไหน หุ้นที่ไม่ผ่านเกณฑ์นั้นจะถูกลบทิ้งทันที (ไม่เอามาคิดคะแนน)",
                        "**Sector**: เลือกเฉพาะอุตสาหกรรมที่สนใจ",
                        "**Timeframes**: ช่วงเวลาที่จะดูผลตอบแทนราคา (YTD = ตั้งแต่ต้นปีถึงปัจจุบัน)"
                    ]
                }
            }
        }
        
        for key, data in SETTINGS_DATA.items():
            content = data[lang]
            with st.expander(f"⚙️ {content['title']}"):
                st.write(content['desc'])
                for line in content['details']:
                    st.markdown(f"- {line}")

        # ==========================================
    # 2. METRICS
    # ==========================================
    with tab2:
        METRICS_DATA = {
            'PE': {
                'EN': {
                    'title': "P/E Ratio",
                    'concept': "Price Tag",
                    'desc': "Price you pay for $1 of earnings.",
                    'formula': "$$ P/E = \\frac{Price}{EPS} $$",
                    'rule': "< 15 (Value), > 30 (Growth/Expensive)",
                    'guru': "**Peter Lynch**: 'If the P/E of Coca-Cola is 15, you’d expect the company to be growing at about 15% a year. If the P/E is less than the growth rate, you may have found yourself a bargain.'"
                },
                'TH': {
                    'title': "P/E Ratio",
                    'concept': "ป้ายราคาหุ้น",
                    'desc': "คุณจ่ายเงินกี่บาท เพื่อซื้อกำไร 1 บาทของบริษัท",
                    'formula': "$$ P/E = \\frac{\\text{ราคา}}{\\text{กำไรต่อหุ้น}} $$",
                    'rule': "ต่ำกว่า 15 = ถูก, สูงกว่า 30 = แพง (หรือโตแรง)",
                    'guru': "**Peter Lynch**: 'ถ้า P/E ของบริษัทคือ 15 คุณต้องคาดหวังว่ามันจะโต 15% ต่อปี ถ้า P/E ต่ำกว่าการเติบโต แปลว่าเจอของถูกแล้ว'"
                }
            },
            'PEG': {
                'EN': {
                    'title': "PEG Ratio",
                    'concept': "Fairness of Price",
                    'desc': "P/E adjusted for growth. Fixes the issue where high P/E looks bad but is actually okay for fast growers.",
                    'formula': "$$ PEG = \\frac{P/E}{Growth\\%} $$",
                    'rule': "< 1.0 (Cheap), > 1.5 (Expensive)",
                    'guru': "**Jim Slater (The Zulu Principle)**: 'A low PEG is the magic key to investment success. Anything under 1.0 is attractive, under 0.75 is very cheap.'"
                },
                'TH': {
                    'title': "PEG Ratio",
                    'concept': "ความแฟร์ของราคา",
                    'desc': "เอาความถูกแพง (P/E) มาหารด้วยความแรง (Growth) เพื่อดูว่าที่แพงน่ะ แพงสมเหตุสมผลไหม",
                    'formula': "$$ PEG = \\frac{P/E}{\\text{การเติบโต}} $$",
                    'rule': "ต่ำกว่า 1.0 = น่าซื้อ, เกิน 1.5 = เริ่มไม่คุ้ม",
                    'guru': "**Jim Slater**: 'PEG ต่ำคือกุญแจวิเศษสู่ความสำเร็จ ค่าที่ต่ำกว่า 1.0 คือน่าสน และถ้าต่ำกว่า 0.75 ถือว่าถูกมาก'"
                }
            },
            'EVEBITDA': {
               'EN': {
                    'title': "EV/EBITDA",
                    'concept': "The Takeover Price",
                    'desc': "Uses Enterprise Value (Debt included) vs Cash Flow (EBITDA). Better than P/E for debt-heavy companies.",
                    'formula': "$$ \\frac{Market Cap + Debt - Cash}{EBITDA} $$",
                    'rule': "< 10 is generally healthy.",
                    'guru': "**Deep Value Investors**: 'Acquirers look at EV/EBITDA because it represents the true cost to buy the whole company, including paying off its debt.'"
                },
                'TH': {
                    'title': "EV/EBITDA",
                    'concept': "ราคาเหมาเข่ง",
                    'desc': "มองภาพรวมทั้งหนี้สินและเงินสด เทียบกับกระแสเงินสดสดที่ทำได้ (EBITDA) ดีกว่า P/E สำหรับหุ้นที่มีหนี้เยอะหรือค่าเสื่อมเยอะ",
                    'formula': "$$ \\frac{\\text{มูลค่าบริษัท + หนี้ - เงินสด}}{EBITDA} $$",
                    'rule': "ต่ำกว่า 10 มักจะถือว่าถูก",
                    'guru': "**นักลงทุนสาย Value**: 'คนที่จะมา Takeover บริษัทจะดูค่านี้ เพราะมันคือราคาจริงที่เขาต้องจ่ายรวมถึงหนี้สินที่ต้องแบกรับ'"
                } 
            },
            'ROE': {
                'EN': {
                    'title': "ROE",
                    'concept': "Management Quality",
                    'desc': "Return on Equity. How much profit they generate from shareholder money.",
                    'formula': "$$ ROE = \\frac{Net Income}{Equity} $$",
                    'rule': "> 15% is Great (Buffett Style)",
                    'guru': "**Warren Buffett**: 'Focus on companies with high Return on Equity and little debt. It shows management is good at allocating capital.'"
                },
                'TH': {
                    'title': "ROE",
                    'concept': "ฝีมือผู้บริหาร",
                    'desc': "เอาเงินผู้ถือหุ้นไป 100 บาท ทำกำไรกลับมาได้กี่บาท",
                    'formula': "$$ ROE = \\frac{\\text{กำไรสุทธิ}}{\\text{ส่วนของผู้ถือหุ้น}} $$",
                    'rule': "เกิน 15% ถือว่าเก่งมาก (Buffett ชอบ)",
                    'guru': "**Warren Buffett**: 'จงมองหาบริษัทที่มี ROE สูง และหนี้ต่ำ นั่นแสดงว่าผู้บริหารเก่งในการนำเงินเราไปต่อยอด'"
                }
            },
             'Margin': {
                'EN': {
                    'title': "Operating Margin",
                    'concept': "Profitability Power",
                    'desc': "Percentage of revenue left after paying for production costs (before tax/interest).",
                    'formula': "$$ \\frac{Operating Income}{Revenue} $$",
                    'rule': "Higher is better. > 15% indicates a 'Moat'.",
                    'guru': "**Pat Dorsey (Morningstar)**: 'High margins are a sign of a wide economic moat. It means the company has pricing power or structural advantages.'"
                },
                'TH': {
                    'title': "Operating Margin",
                    'concept': "อำนาจในการทำกำไร",
                    'desc': "ขายของ 100 บาท หักต้นทุนการผลิตแล้วเหลือเข้าบริษัทกี่บาท (บ่งบอกความแข็งแกร่งของแบรนด์)",
                    'formula': "$$ \\frac{\\text{กำไรจากการดำเนินงาน}}{\\text{ยอดขาย}} $$",
                    'rule': "ยิ่งมากยิ่งดี. เกิน 15% แปลว่าแกร่ง คู่แข่งสู้ยาก",
                    'guru': "**Pat Dorsey**: 'Margin สูงๆ คือสัญญาณของป้อมปราการทางธุรกิจ (Moat) แปลว่าบริษัทมีอำนาจต่อรองราคาหรือมีความได้เปรียบ'"
                }
            },
            'DE': {
                'EN': {
                    'title': "Debt/Equity",
                    'concept': "Bankruptcy Risk",
                    'desc': "How much debt do they have?",
                    'formula': "$$ D/E = \\frac{Total Debt}{Equity} $$",
                    'rule': "< 100% (1.0) is safe.",
                    'guru': "**Benjamin Graham**: 'A defensive investor should not purchase a stock with a substantial amount of debt. Safety first.'"
                },
                'TH': {
                    'title': "Debt/Equity",
                    'concept': "ความเสี่ยงเจ๊ง",
                    'desc': "มีหนี้กี่บาท เทียบกับเงินตัวเอง",
                    'formula': "$$ D/E = \\frac{\\text{หนี้สินรวม}}{\\text{ส่วนของผู้ถือหุ้น}} $$",
                    'rule': "ไม่ควรเกิน 100% (1.0) ยกเว้นกลุ่มการเงิน",
                    'guru': "**Benjamin Graham**: 'นักลงทุนที่เน้นปลอดภัย ไม่ควรซื้อหุ้นที่มีหนี้เยอะเกินไป ความปลอดภัยต้องมาก่อน'"
                }
            }
        }

        for key, data in METRICS_DATA.items():
            content = data[lang]
            with st.expander(f"📊 {content['title']} - {content['concept']}"):
                st.write(content['desc'])
                st.info(f"Target: {content['rule']}")
                if 'guru' in content:
                    st.warning(f"💬 {content['guru']}")
                st.markdown(content['formula'])


    # ==========================================
    # 3. PETER LYNCH
    # ==========================================
    with tab3:
        st.markdown("### 🧠 The Six Categories of Peter Lynch")
        st.caption("From the book 'One Up on Wall Street'. Knowing what you own is key.")
        
        LYNCH_DATA = {
            'FastGrower': {
                'EN': {
                    'title': "🚀 Fast Growers",
                    'desc': "Aggressive growth companies (20-25% a year).",
                    'strat': "The big winners. Land of the 10-baggers. Volatile but rewarding.",
                    'risk': "If growth slows, price crashes hard."
                },
                'TH': {
                    'title': "🚀 Fast Growers (หุ้นโตเร็ว)",
                    'desc': "บริษัทขนาดเล็ก-กลาง ที่เติบโตปีละ 20-25%",
                    'strat': "นี่คือกลุ่มที่จะเปลี่ยนชีวิต (10 เด้ง) ซื้อเมื่อยังโต ขายเมื่อหยุดโต",
                    'risk': "ถ้าไตรมาสไหนโตน้อยกว่าคาด ราคาจะร่วงหนักมาก"
                }
            },
            'Stalwart': {
                'EN': {
                    'title': "🐘 Stalwarts",
                    'desc': "Large, old companies (Coca-Cola, PTT). Grow 10-12%.",
                    'strat': "Buy for recession protection and steady 30-50% gains.",
                    'risk': "Don't expect them to double quickly."
                },
                'TH': {
                    'title': "🐘 Stalwarts (หุ้นแข็งแกร่ง)",
                    'desc': "ยักษ์ใหญ่ที่โตช้าลง (10-12%) เช่น PTT, SCC, Coke",
                    'strat': "เอาไว้หลบภัยเศรษฐกิจ กินกำไรเรื่อยๆ 30-50% พอได้ ไม่หวือหวา",
                    'risk': "อย่าไปหวังให้มันโตเป็นเด้งในเวลาสั้นๆ"
                }
            },
            'SlowGrower': {
                'EN': {
                    'title': "🐢 Slow Growers",
                    'desc': "Grow slightly faster than GDP. Usually pay high dividends.",
                    'strat': "Buy for the Dividend Yield only.",
                    'risk': "Capital appreciation is minimal."
                },
                'TH': {
                    'title': "🐢 Slow Growers (หุ้นโตช้า)",
                    'desc': "โตเท่าๆกับ GDP ประเทศ เน้นจ่ายปันผล",
                    'strat': "ซื้อเพื่อกินปันผลอย่างเดียว อย่าหวังส่วนต่างราคา",
                    'risk': "ถ้าราคาไม่ขึ้น และปันผลก็งด = จบเห่"
                }
            },
            'Cyclical': {
                'EN': {
                    'title': "🔄 Cyclicals",
                    'desc': "Rise and fall with the economy (Cars, Steel, Airlines).",
                    'strat': "Timing is everything. Buy when P/E is HIGH (earnings low), Sell when P/E is LOW.",
                    'risk': "Holding them at the wrong cycle can lose 80%."
                },
                'TH': {
                    'title': "🔄 Cyclicals (หุ้นวัฏจักร)",
                    'desc': "กำไรขึ้นลงตามรอบศก. (น้ำมัน, เรือ, เหล็ก)",
                    'strat': "จังหวะคือทุกอย่าง! ซื้อเมื่อ P/E สูง (กำไรตกต่ำสุดขีด) ขายเมื่อ P/E ต่ำ",
                    'risk': "ถ้าถือผิดรอบ อาจขาดทุนยับและรอนานเป็นปีกว่าจะหลุดดอย"
                }
            },
             'AssetPlay': {
                'EN': {
                    'title': "🏰 Asset Plays",
                    'desc': "Company sitting on valuable assets (Land, Cash) worth more than stock price.",
                    'strat': "Buy and wait for the value to be unlocked.",
                    'risk': "The 'Value Trap'. Management might never sell the assets."
                },
                'TH': {
                    'title': "🏰 Asset Plays (หุ้นทรัพย์สินมาก)",
                    'desc': "มีที่ดิน, เงินสด หรือของมีค่า ที่มูลค่ามากกว่าราคาหุ้นทั้งบริษัท",
                    'strat': "ซื้อแล้วรอให้ตลาดรับรู้ หรือมีการขายสินทรัพย์",
                    'risk': "อาจจะเป็นกับดัก ถ้าผู้บริหารกอดสมบัติไว้ไม่ยอมทำอะไร"
                }
            }
        }
        
        for key, data in LYNCH_DATA.items():
            content = data[lang]
            with st.expander(content['title']):
                st.write(f"**Definition**: {content['desc']}")
                st.write(f"**Strategy**: {content['strat']}")
                st.error(f"**Risk**: {content['risk']}")


# ---------------------------------------------------------


def page_scanner():
    st.title(get_text('main_title'))
    st.info(get_text('about_desc'))

    # --- PROFESSIONAL UI: MAIN CONFIGURATION ---
    # Moved all controls from Sidebar to Main Page Expander
    with st.expander(get_text('scanner_config'), expanded=True):
        
        # Row 1: High Level Strategy
        c_uni, c_strat = st.columns(2)
        with c_uni:
             st.subheader(get_text('univ_scale'))
             market_choice = st.selectbox(get_text('market_label'), ["S&P 500", "NASDAQ 100", "SET 100 (Thailand)"])
             num_stocks = st.slider(get_text('scan_limit'), 10, 503, 50)
             top_n_deep = st.slider(get_text('analyze_top_n'), 5, 50, 10)
        
        with c_strat:
             st.subheader(get_text('strat_mandate'))
             strategy = st.selectbox(get_text('strategy_label'), ["Custom", "Growth at Reasonable Price (GARP)", "Deep Value", "High Yield", "Speculative Growth", "Multibagger (High Risk)"])
             
             # Mode & Period
             strict_criteria = st.multiselect(get_text('strict_label'), 
                                                  ["PE", "PEG", "ROE", "Op_Margin", "Div_Yield", "Debt_Equity"],
                                                  default=[],
                                                  help="Selected metrics must PASS the threshold or the stock is removed.")
             perf_metrics_select = st.multiselect(get_text('perf_label'),
                                                     ["1M", "3M", "6M", "YTD", "1Y", "3Y", "5Y"],
                                                     default=["YTD", "1Y"],
                                                     help="Show price return % for these periods.")

        st.markdown("---")
        
        # Row 2: Detailed Thresholds
        st.subheader(get_text('crit_thresh'))
        
        # Defaults
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
        elif strategy == "Multibagger (High Risk)":
            t_pe = 999.0; t_peg = 3.0; t_roe = 0.05; t_rev_growth = 30.0
            
        c_val, c_prof, c_risk = st.columns(3)
        
        with c_val:
             st.markdown(f"**{get_text('val_header')}**")
             val_pe = st.slider("Max P/E Ratio", 5.0, 500.0, float(t_pe))
             val_peg = st.slider("Max PEG Ratio", 0.1, 10.0, float(t_peg))
             val_evebitda = st.slider("Max EV/EBITDA", 1.0, 50.0, float(t_evebitda))
             
        with c_prof:
             st.markdown(f"**{get_text('prof_header')}**")
             prof_roe = st.slider("Min ROE %", 0, 50, int(t_roe*100)) / 100
             prof_margin = st.slider("Min Op Margin %", 0, 50, int(t_margin*100)) / 100
             prof_div = st.slider("Min Dividend Yield %", 0, 15, int(t_div*100)) / 100
             if strategy == "Speculative Growth" or strategy == "Multibagger (High Risk)":
                 growth_min = st.slider("Min Revenue Growth %", 0, 100, int(t_rev_growth))
        
        with c_risk:
             st.markdown(f"**{get_text('risk_header')}**")
             risk_de = st.slider("Max Debt/Equity %", 0, 500, int(t_de), step=10)
             
             # Filters
             st.caption(get_text('opt_filters'))
             SECTORS = [
                "Technology", "Healthcare", "Financial Services", "Consumer Cyclical", 
                "Industrials", "Consumer Defensive", "Energy", "Utilities", 
                "Basic Materials", "Real Estate", "Communication Services"
            ]
             selected_sectors = st.multiselect(get_text('sector_label'), SECTORS, default=[])
            
             LYNCH_TYPES = [
                "🚀 Fast Grower", "🏰 Asset Play", "🐢 Slow Grower", 
                "🐘 Stalwart", "🔄 Cyclical", "😐 Average", "⚪ Unknown"
            ]
             selected_lynch = st.multiselect(get_text('lynch_label'), LYNCH_TYPES, default=[])

    st.caption(f"Universe: {market_choice} | Strategy: {strategy} | Scan Limit: {num_stocks}")

    if 'scan_results' not in st.session_state: st.session_state['scan_results'] = None
    
    # DEBUG EXPANDER
    if 'deep_results' not in st.session_state: st.session_state['deep_results'] = None
    debug_container = st.expander("🛠️ Debug Logs (Open if No Data)", expanded=False)

    # 2-Stage Scan Execution
    if st.button(get_text('execute_btn'), type="primary", use_container_width=True):
        st.write(get_text('stage1_msg'))
        prog = st.progress(0)
        status = st.empty()
        
        # 1. Get Tickers
        if "S&P" in market_choice: tickers = get_sp500_tickers()
        elif "NASDAQ" in market_choice: tickers = get_nasdaq_tickers()
        else: tickers = get_set100_tickers()
        
        tickers = tickers[:num_stocks] # Limit scan
        
        # 2. Stage 1 Scan
        df_basic = scan_market_basic(tickers, prog, status, debug_container)
        
        if df_basic.empty:
            st.error("No data fetched.")
            return

        st.success(get_text('stage2_msg'))
        
        # 3. Filtering Stage 1 (Fast)
        # Apply strict filters before fetching deep data
        filtered = df_basic.copy()
        
        # Strict Logic
        if strict_criteria:
            if "PE" in strict_criteria: filtered = filtered[filtered['PE'].fillna(999) <= val_pe]
            if "PEG" in strict_criteria: filtered = filtered[(filtered['PEG'].fillna(999) <= val_peg) & (filtered['PEG'] > 0)]
            if "ROE" in strict_criteria: filtered = filtered[filtered['ROE'].fillna(0) >= prof_roe] # Basic ROE check
            if "Op_Margin" in strict_criteria: filtered = filtered[filtered['Op_Margin'].fillna(0) >= prof_margin]
            if "Div_Yield" in strict_criteria: filtered = filtered[filtered['Div_Yield'].fillna(0) >= prof_div]
            if "Debt_Equity" in strict_criteria: filtered = filtered[filtered['Debt_Equity'].fillna(999) <= risk_de]
        
        # 4. Filter by Sector
        if selected_sectors:
            filtered = filtered[filtered['Sector'].isin(selected_sectors)]
            
        if strict_criteria or selected_sectors:
             st.info(f"Filtered {len(df_basic)} -> {len(filtered)} stocks based on strict criteria.")
        
        if filtered.empty:
            st.warning(get_text('no_data'))
            return
            
        # 5. Determine Scoring Targets based on Strategy
        if strategy == "Speculative Growth":
            targets = [('Rev_Growth', float(growth_min), '>'), ('EPS_Growth', 0.15, '>'),
                       ('ROE', prof_roe, '>'), ('Debt_Equity', risk_de, '<')]
        elif strategy == "Multibagger (High Risk)":
             targets = [('Rev_Growth', float(growth_min), '>'), ('EPS_Growth', 0.20, '>'),
                       ('ROE', prof_roe, '>'), ('PEG', 2.0, '<')] # Cheap Growth check
        else:
            targets = [('PEG', val_peg, '<'), ('PE', val_pe, '<'), ('ROE', prof_roe, '>'),
                       ('Op_Margin', prof_margin, '>'), ('Div_Yield', prof_div, '>'), ('Debt_Equity', risk_de, '<')]
        
        # 6. Calc Score
        results = filtered.apply(lambda row: calculate_fit_score(row, targets), axis=1, result_type='expand')
        if not filtered.empty:
            filtered['Fit_Score'] = results[0]
            filtered['Analysis'] = results[1]
            filtered['Lynch_Category'] = filtered.apply(classify_lynch, axis=1)
            
            # Lynch Filtering
            if selected_lynch:
                filtered = filtered[filtered['Lynch_Category'].isin(selected_lynch)]
            
            # Sort
            if 'Market_Cap' in filtered.columns:
                 filtered = filtered.sort_values(by=['Fit_Score', 'Market_Cap'], ascending=[False, False])
            else:
                 filtered = filtered.sort_values(by='Fit_Score', ascending=False)
            
            top_candidates = filtered.head(top_n_deep)
            
            # --- STAGE 2: DEEP DIVE ---
            time.sleep(0.5)
            deep_metrics = analyze_history_deep(top_candidates, st.progress(0), st.empty())
            final_df = top_candidates.merge(deep_metrics, on='Symbol', how='left')
            
            st.session_state['scan_results'] = filtered
            st.session_state['deep_results'] = final_df
        else:
            st.error(get_text('no_data'))
            return

    # Display Logic
    if st.session_state['deep_results'] is not None:
        final_df = st.session_state['deep_results']
        currency_fmt = "฿%.2f" if "SET" in market_choice or (len(final_df) > 0 and ".BK" in str(final_df['Symbol'].iloc[0])) else "$%.2f"

        st.markdown(f"### {get_text('results_header')}")
        
        # Columns
        core_cols = ["Fit_Score", "Symbol", "Price"]
        if strategy == "High Yield": strat_cols = ["Div_Yield", "Div_Streak", "Fair_Value", "Margin_Safety", "Analysis"]
        elif strategy == "Deep Value": strat_cols = ["PE", "PB", "Lynch_Category", "Fair_Value", "Margin_Safety", "Analysis"]
        elif strategy == "Speculative Growth": strat_cols = ["Rev_Growth", "PEG", "Lynch_Category", "Fair_Value", "Analysis"]
        else: strat_cols = ["PEG", "Rev_CAGR_5Y", "NI_CAGR_5Y", "Fair_Value", "Margin_Safety", "Analysis"]
        
        perf_cols = [c for c in perf_metrics_select if c in final_df.columns]
        final_cols = core_cols + perf_cols + strat_cols
        
        # Filter valid cols
        valid_final_cols = [c for c in final_cols if c in final_df.columns]

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

        if 'YF_Obj' in final_df.columns:
            display_df = final_df.drop(columns=['YF_Obj'])
        else:
            display_df = final_df

        st.dataframe(display_df, column_order=valid_final_cols, column_config=col_config, hide_index=True, width="stretch")
        
        # Chart
        st.markdown("### 🔬 Interactive Historical Charts")
        if 'Symbol' in final_df.columns:
             sel = st.selectbox("Select Stock to View:", final_df['Symbol'].unique())
             if sel:
                 try:
                     # Attempt to get object
                     row = final_df[final_df['Symbol'] == sel].iloc[0]
                     if 'YF_Obj' in row:
                         stock = row['YF_Obj']
                         hist = stock.history(period="2y")
                         st.line_chart(hist['Close'])
                 except: pass # fallback



def page_portfolio():
    st.title("Intelligent Portfolio")
    st.markdown("---")
    
    
    # 1. Configuration Panel (Professional Layout)
    with st.expander(get_text('port_config'), expanded=True):
        c1, c2 = st.columns([1, 1])
        
        with c1:
             st.subheader(get_text('asset_univ'))
             market_choice = st.radio(get_text('market_label'), ["S&P 500", "SET 100", "NASDAQ 100"], horizontal=True, key="p_market")
             n_stocks = st.slider(get_text('max_holdings'), 5, 50, 20, key="p_n")
             
        with c2:
             st.subheader(get_text('strat_prof'))
             risk_choice = st.select_slider(
                get_text('risk_tol'), 
                options=["Low (Defensive)", "Medium (Balanced)", "High (Aggressive)", "All Weather (Ray Dalio Proxy)"],
                value="Medium (Balanced)",
                key="p_risk"
             )
             
             risk_descs = {
                "Low (Defensive)": get_text('risk_low_desc'),
                "Medium (Balanced)": get_text('risk_med_desc'),
                "High (Aggressive)": get_text('risk_high_desc'),
                "All Weather (Ray Dalio Proxy)": get_text('risk_all_desc')
             }
             st.info(risk_descs.get(risk_choice, ""))


    # Action Area
    col_btn, col_info = st.columns([1, 3])
    with col_btn:
        generate_btn = st.button(get_text('gen_port_btn'), type="primary", use_container_width=True)
    with col_info:
        st.caption(f"**Target**: Top {n_stocks} stocks in **{market_choice}**. {get_text('port_target_caption')}")
    
    if generate_btn:
        # Modern Status Container
        with st.status(get_text('status_processing'), expanded=True) as status_box:
            # 1. Get Tickers
            st.write(get_text('status_fetch'))
            if "S&P" in market_choice: tickers = get_sp500_tickers()
            elif "NASDAQ" in market_choice: tickers = get_nasdaq_tickers()
            else: tickers = get_set100_tickers()
            
            # 2. Scanning
            st.write(f"{get_text('status_scan')} ({len(tickers)})")
            prog = st.progress(0)
            
            scan_placeholder = st.empty()
            df_scan = scan_market_basic(tickers, prog, scan_placeholder)
            
            if df_scan.empty:
                status_box.update(label=get_text('status_scan_fail'), state="error")
                st.error("No stocks found. Try again.")
                return
            status_box.update(label=get_text('status_scan_complete'), state="complete")
        
        # 3.5 Enrichment
        with st.status(get_text('status_deep'), expanded=True) as enrich_status:
            enrich_prog = st.progress(0)
        
            # Helper to process row
            def enrich_row(row):
                # ... (Logic identical to before)
                stock = row['YF_Obj']
                updates = {}
                try:
                    fin = stock.financials
                    if not fin.empty: # ... Logic
                        fin = fin.T.sort_index()
                        years = len(fin)
                        if years >= 3:
                            # Rev CAGR
                            try:
                                s = float(fin['Total Revenue'].iloc[0])
                                e = float(fin['Total Revenue'].iloc[-1])
                                if s > 0 and e > 0:
                                    updates['Rev_CAGR_5Y'] = ((e/s)**(1/(years-1)) - 1) * 100
                                else: updates['Rev_CAGR_5Y'] = None
                            except: updates['Rev_CAGR_5Y'] = None
                            
                            # NI CAGR
                            try:
                                s = float(fin['Net Income'].iloc[0])
                                e = float(fin['Net Income'].iloc[-1])
                                if s > 0 and e > 0: # Ensure positive for power calc
                                    updates['NI_CAGR_5Y'] = ((e/s)**(1/(years-1)) - 1) * 100
                                else: updates['NI_CAGR_5Y'] = None
                            except: updates['NI_CAGR_5Y'] = None
                except: pass
                
                # Smart PEG Fill (using historical Growth if avail)
                if pd.isna(row.get('PEG')) or row.get('PEG') == 0:
                    pe = row.get('PE')
                    cagr = updates.get('NI_CAGR_5Y')
                    if pe and cagr and cagr > 0:
                         updates['PEG'] = pe / cagr
                
                enrich_prog.progress(0.5) # Simulated progress
                return pd.Series(updates)

            # Apply Enrichment
            if not df_scan.empty:
                enriched = df_scan.apply(enrich_row, axis=1)
                for col in enriched.columns:
                    df_scan[col] = enriched[col]
            
            enrich_status.update(label=get_text('status_deep_complete'), state="complete")
            enrich_prog.progress(1.0)
            enrich_prog.empty()


        # 4. Strategy Mapping (Logic remains same)
        targets_map = {
             "Low (Defensive)": [('Div_Yield', 0.03, '>'), ('PE', 20.0, '<'), ('Debt_Equity', 100.0, '<'), ('ROE', 10.0, '>')],
             "Medium (Balanced)": [('PEG', 1.5, '<'), ('PE', 30.0, '<'), ('ROE', 12.0, '>'), ('Op_Margin', 10.0, '>')],
             "High (Aggressive)": [('Rev_Growth', 15.0, '>'), ('PEG', 2.0, '<'), ('ROE', 5.0, '>')],
             "All Weather (Ray Dalio Proxy)": [('ROE', 12.0, '>'), ('Debt_Equity', 80.0, '<'), ('PE', 25.0, '<'), ('Op_Margin', 10.0, '>')]
        }
        
        targets = targets_map[risk_choice]
        st.subheader(f"🧠 AI Analysis Result ({risk_choice})")
        
        # ... (Fit Score & Sort Logic Same) ...
        if 'Ticker' not in df_scan.columns: df_scan['Ticker'] = df_scan['Symbol']
        results = df_scan.apply(lambda row: calculate_fit_score(row, targets), axis=1)
        df_scan['Fit Score'] = results.apply(lambda x: x[0])
        df_scan['Type'] = df_scan.apply(classify_lynch, axis=1)
        final_df = df_scan[df_scan['Fit Score'] >= 50].sort_values(by=['Fit Score', 'Market_Cap'], ascending=[False, False])
        
        portfolio = final_df.head(n_stocks).copy()
        
        if portfolio.empty:
            st.warning(get_text('no_data'))
            return

        # ... (Weighting Logic Same) ...
        total_mcap = portfolio['Market_Cap'].sum()
        full_portfolio = pd.DataFrame()
        assets_df = pd.DataFrame()
        
        # ... (All Weather Logic Same) ...
        if risk_choice == "All Weather (Ray Dalio Proxy)":
            equity_weight = 0.30
            if total_mcap > 0:
                portfolio['Weight_Raw'] = portfolio['Market_Cap'] / total_mcap
                portfolio['Weight %'] = portfolio['Weight_Raw'] * equity_weight * 100
                portfolio['Bucket'] = "Equities (Stock)"
            else:
                portfolio['Weight %'] = (equity_weight * 100) / len(portfolio)
                portfolio['Bucket'] = "Equities (Stock)"

            assets_data = [
                {'Ticker': 'TLT', 'Bucket': 'Long Bonds', 'Weight %': 40.0, 'Price': 95.0, 'Company': 'iShares 20+ Year Treasury Bond ETF', 'Sector': 'ETF'},
                {'Ticker': 'IEF', 'Bucket': 'Interm Bonds', 'Weight %': 15.0, 'Price': 92.0, 'Company': 'iShares 7-10 Year Treasury Bond ETF', 'Sector': 'ETF'},
                {'Ticker': 'GLD', 'Bucket': 'Gold', 'Weight %': 7.5, 'Price': 185.0, 'Company': 'SPDR Gold Shares', 'Sector': 'ETF'},
                {'Ticker': 'DBC', 'Bucket': 'Commodities', 'Weight %': 7.5, 'Price': 22.0, 'Company': 'Invesco DB Commodity Index', 'Sector': 'ETF'}
            ]
            assets_df = pd.DataFrame(assets_data)
            full_portfolio = pd.concat([portfolio, assets_df], ignore_index=True)
        else:
            if total_mcap > 0:
                portfolio['Weight_Raw'] = portfolio['Market_Cap'] / total_mcap
                portfolio['Weight %'] = portfolio['Weight_Raw'] * 100
            else:
                portfolio['Weight %'] = 100 / len(portfolio)
            portfolio['Bucket'] = portfolio['Sector']
            full_portfolio = portfolio.copy()


        # 7. Visualization
        st.success(f"✅ Generated Professional Portfolio: {len(portfolio)} Stocks")
        
        # Portfolio Stats (Equity Only)
        avg_pe = portfolio['PE'].mean()
        avg_div = portfolio['Div_Yield'].mean()
        avg_roe = portfolio['ROE'].mean()
        
        # Top Level Metrics
        m1, m2, m3, m4 = st.columns(4)
        m1.metric("Avg P/E (Equity)", f"{avg_pe:.1f}")
        m2.metric("Equity Yield", f"{avg_div:.2%}")
        m3.metric("Quality (ROE)", f"{avg_roe:.1f}%")
        m4.metric("Strategy", risk_choice)
        
        # --- TABBED ANALYSIS ---
        tab1, tab2, tab3 = st.tabs([get_text('tab_holdings'), get_text('tab_alloc'), get_text('tab_logic')])
        
        with tab1:
            cols_to_show = ['Ticker', 'Company', 'Bucket', 'Type', 'Sector', 'Price', 'Fit Score', 'PE', 'PEG', 'Rev_CAGR_5Y', 'NI_CAGR_5Y', 'Div_Yield', 'Weight %']
            col_cfg = {
                "Ticker": st.column_config.TextColumn("Symbol"),
                "Bucket": st.column_config.TextColumn("Asset Class"), 
                "Price": st.column_config.NumberColumn(format="%.2f"),
                "Fit Score": st.column_config.ProgressColumn("Score", format="%d", min_value=0, max_value=100),
                "PE": st.column_config.NumberColumn(format="%.1f"),
                "PEG": st.column_config.NumberColumn(format="%.2f"),
                "Rev_CAGR_5Y": st.column_config.NumberColumn("Rev CAGR", format="%.1f%%"),
                "NI_CAGR_5Y": st.column_config.NumberColumn("NI CAGR", format="%.1f%%"),
                "Div_Yield": st.column_config.NumberColumn("Yield", format="%.2f%%"),
                "Weight %": st.column_config.NumberColumn("Weight", format="%.2f%%")
            }
            
            if risk_choice == "All Weather (Ray Dalio Proxy)":
                st.subheader(get_text('equity_holdings'))
                valid_cols = [c for c in cols_to_show if c in portfolio.columns]
                st.dataframe(portfolio[valid_cols], column_config=col_cfg, width="stretch", hide_index=True)
                
                st.subheader(get_text('core_assets'))
                st.info(get_text('core_assets_desc'))
                asset_cols = ['Ticker', 'Company', 'Bucket', 'Weight %', 'Price']
                st.dataframe(assets_df[asset_cols], column_config=col_cfg, width="stretch", hide_index=True)
                
            else:
                valid_cols = [c for c in cols_to_show if c in portfolio.columns]
                st.dataframe(portfolio[valid_cols], column_config=col_cfg, width="stretch", height=500, hide_index=True)

            
        with tab2:
             c1, c2 = st.columns([2, 1])
             with c1:
                 st.subheader("🌍 Portfolio Allocation")
                 st.caption("Breakdown by Individual Holding & Group")
                 
                 # Prepare Chart Data
                 if risk_choice == "All Weather (Ray Dalio Proxy)":
                     chart_df = full_portfolio.copy()
                     color_col = "Bucket"
                     legend_title = "Asset Class"
                 else:
                     chart_df = portfolio.copy()
                     chart_df['Bucket'] = chart_df['Sector'] 
                     color_col = "Bucket" 
                     legend_title = "Sector"

                 # Create Label for Chart
                 chart_df['Label'] = chart_df['Ticker'] + " (" + chart_df['Weight %'].map('{:.1f}%'.format) + ")"

                 # Donut Chart (Altair) - Individual Stocks
                 base = alt.Chart(chart_df).encode(theta=alt.Theta("Weight %", stack=True))
                 
                 pie = base.mark_arc(outerRadius=120, innerRadius=60).encode(
                    color=alt.Color(color_col, legend=alt.Legend(title=legend_title)), 
                    order=alt.Order("Weight %", sort="descending"),
                    tooltip=["Ticker", "Bucket", "Weight %", "Sector"] 
                 )
                 
                 text = base.mark_text(radius=160).encode( # Increased radius for visibility
                    text=alt.Text("Label"), 
                    order=alt.Order("Weight %", sort="descending"),
                    color=alt.value("white") 
                 )
                 
                 st.altair_chart(pie + text, use_container_width=True)
             
             with c2:
                 st.subheader("Type Allocation")
                 st.bar_chart(portfolio['Type'].value_counts())

                
        with tab3:
            st.info("""
            **Why Market Cap Weighting?**
            - **Professional Standard**: S&P 500 and Nasdaq 100 use this.
            - **Stability**: Larger, more established companies get more money.
            - **Self-Correcting**: As companies grow, they become a larger part of your portfolio naturally.
            
            **How it works here:**
            1. We select the Top 20 stocks that match your **Strategy Score**.
            2. We allocate money based on **Company Size (Market Cap)**.
            3. *Result*: You own more of the 'Blue Chips' and less of the volatile small players.
            """)







def page_howto():
    st.title("📖 How to Use / คู่มือการใช้งาน")
    lang = st.session_state.get('lang', 'EN')
    
    HOWTO_DATA = {
        'Intro': {
            'EN': """
            **Welcome to the Stock Scanner!**  
             This tool is designed to help you **find good stocks quickly** without reading 100 annual reports.  
             It works in 2 stages:  
             1. **Wide Scan**: Checks hundreds of stocks for basic criteria (Price, P/E).  
             2. **Deep Dive**: Digs into the history of the best ones to find "consistency".
            """,
            'TH': """
            **ยินดีต้อนรับสู่โปรแกรมสแกนหุ้น!**  
            เครื่องมือนี้ช่วยให้คุณ **หาหุ้นดีๆ ได้ในไม่กี่วินาที** โดยไม่ต้องนั่งอ่านงบเองเป็นร้อยบริษัท  
            หลักการทำงานมี 2 ขั้นตอน:  
            1. **สแกนกว้าง (Wide Scan)**: กวาดดูหุ้นทั้งตลาด เพื่อคัดตัวที่เข้าเกณฑ์พื้นฐาน (เช่น P/E ต่ำ).  
            2. **เจาะลึก (Deep Dive)**: เอาตัวที่เข้ารอบมาดูประวัติย้อนหลังว่า "ดีจริงไหม" หรือแค่ฟลุ๊ค
            """
        },
        'Step1': {
            'EN': {
                'title': "Step 1: Setup (Universe & Scale)",
                'desc': """
                - **Select Market**: Choose S&P 500 (US Big Caps) or SET 100 (Thai Big Caps).
                - **Scan Limit**: Start with **50** for speed. Use **500** when you have time (takes 2-3 mins).
                """
            },
            'TH': {
                'title': "ขั้นตอนที่ 1: ตั้งค่าขอบเขต (Setup)",
                'desc': """
                - **เลือกตลาด (Market)**: เช่น S&P 500 (หุ้นใหญ่เมกา) หรือ SET 100 (หุ้นใหญ่ไทย)
                - **จำนวนสแกน (Limit)**: มือใหม่แนะนำ **50 ตัวแรก** ก่อนเพื่อทดสอบ ถ้าจริงจังค่อยปรับเป็น 500 (ใช้เวลา 2-3 นาที)
                """
            }
        },
        'Step2': {
            'EN': {
                'title': "Step 2: Strategy (The 'Brain')",
                'desc': """
                This is the most important part.  
                - **GARP**: Balanced. Good for most people.
                - **Dividend**: If you want cash flow > 4%.
                - **Deep Value**: If you want to buy very cheap stocks (Risky).
                - **Speculative**: If you want growth at any price.
                """
            },
            'TH': {
                'title': "ขั้นตอนที่ 2: เลือกกลยุทธ์ (The Brain)",
                'desc': """
                ส่วนที่สำคัญที่สุด โปรแกรมจะคัดหุ้นตามสูตรที่คุณเลือก:  
                - **GARP (แนะนำ)**: หุ้นเติบโตในราคาที่ไม่แพงเกินไป (สายกลาง)
                - **High Yield**: เน้นหุ้นปันผลเยอะ (>3-4%)
                - **Deep Value**: เน้นหุ้นถูกมากๆ (P/E ต่ำ) แต่อาจมีความเสี่ยง
                - **Speculative**: เน้นหุ้นซิ่ง ยอดขายโตแรง ไม่สน P/E
                """
            }
        },
        'Step3': {
            'EN': {
                'title': "Step 3: Execution & Results",
                'desc': """
                - Click **🚀 Execute**.
                - Wait for the progress bar.
                - **The Table**:
                    - **Fit Score**: 100 is perfect match.
                    - **Fair Value**: The 'Real' price vs Market Price.
                    - **Margin of Safety**: How much discount? (Positive is GOOD).
                """
            },
            'TH': {
                'title': "ขั้นตอนที่ 3: ดูผลลัพธ์ (Execution)",
                'desc': """
                - กดปุ่ม **🚀 เริ่มสแกน**
                - **ตารางผลลัพธ์**:
                    - **Fit Score**: คะแนนความตรงโจทย์ (เต็ม 100)
                    - **Fair Value**: ราคาที่ควรจะเป็น (ประเมินโดยนักวิเคราะห์/สูตร)
                    - **Margin of Safety**: ส่วนลดจากราคาจริง (ยิ่งเยอะยิ่งดี = มีแต้มต่อ)
                """
            }
        }
    }
    
    # Render Intro
    st.info(HOWTO_DATA['Intro'][lang])
    st.markdown("---")
    
    # Render Steps
    st.header(HOWTO_DATA['Step1'][lang]['title'])
    st.write(HOWTO_DATA['Step1'][lang]['desc'])
    
    st.header(HOWTO_DATA['Step2'][lang]['title'])
    st.write(HOWTO_DATA['Step2'][lang]['desc'])
    
    st.header(HOWTO_DATA['Step3'][lang]['title'])
    st.write(HOWTO_DATA['Step3'][lang]['desc'])

# ---------------------------------------------------------
if __name__ == "__main__":
    inject_custom_css() # Apply Professional Styles
    
    st.sidebar.title("🌐 Language / ภาษา")
    lang_choice = st.sidebar.radio("Language / ภาษา", ["English (EN)", "Thai (TH)"], horizontal=True)
    st.session_state['lang'] = 'EN' if "English" in lang_choice else 'TH'

    st.sidebar.title("Menu")
    page = st.sidebar.radio("Go to", ["Scanner", "Auto Portfolio", "Single Stock", "Portfolio HealthCheck", "Stock AI Analysis", "Glossary", "How to Use"])
    
    if page == "Scanner":
        page_scanner()
    elif page == "Auto Portfolio":
        page_portfolio()
    elif page == "Single Stock":
        page_single_stock()
    elif page == "Portfolio HealthCheck":
        st.title(get_text('menu_health'))
        st.markdown("---")
        st.warning(get_text('under_dev'))
        st.info(get_text('dev_soon'))
    elif page == "Stock AI Analysis":
        st.title(get_text('menu_ai'))
        st.markdown("---")
        st.warning(get_text('under_dev'))
        st.info(get_text('dev_dl'))
    elif page == "Glossary":
        page_glossary()
    elif page == "How to Use":
        page_howto()
