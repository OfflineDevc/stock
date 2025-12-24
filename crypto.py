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


# --- CACHING HELPERS (Optimization) ---
@st.cache_data(ttl=3600*12, show_spinner=False)
def fetch_cached_info(ticker):
    """Cache the heavy API call for stock metadata (with Retry)."""
    retries = 3
    for attempt in range(retries):
        try:
            return yf.Ticker(ticker).info
        except Exception as e:
            err_msg = str(e).lower()
            if "too many requests" in err_msg or "rate limited" in err_msg or "429" in err_msg:
                if attempt < retries - 1:
                    sleep_time = (2 ** attempt) + (0.1 * (attempt+1)) # Exponential Backoff: 1.1s, 2.2s, 4.3s
                    print(f"[{ticker}] Rate Limited. Retrying in {sleep_time:.2f}s...")
                    time.sleep(sleep_time)
                    continue
            
            print(f"[{ticker}] Info Error: {e}")
            return {'__error__': str(e)}
    return {}

# Retry Helper for Object access (when we have obj but need property)
def safe_get_info(stock_obj):
    val = None
    try:
        val = stock_obj.info
    except Exception:
        # Retry logic 
        try:
             time.sleep(1)
             val = stock_obj.info
        except:
             pass
    
    return val if val is not None else {}




@st.cache_data(ttl=3600*12, show_spinner=False)
def fetch_cached_history(ticker, period='5y'):
    """Cache the history fetch for deep analysis (with Retry)."""
    retries = 3
    for attempt in range(retries):
        try:
            return yf.Ticker(ticker).history(period=period)
        except Exception as e:
            err_msg = str(e).lower()
            if "too many requests" in err_msg or "rate limited" in err_msg or "429" in err_msg:
                 if attempt < retries - 1:
                    time.sleep((2 ** attempt))
                    continue
            return pd.DataFrame()
    return pd.DataFrame()

# --- PROFESSIONAL UI OVERHAUL ---
def inject_custom_css():
    st.markdown("""
        <style>
        /* Main Font */
        @import url('https://fonts.googleapis.com/css2?family=Roboto:wght@300;400;700&display=swap');
        html, body, [class*="css"] {
            font-family: 'Roboto', sans-serif;
        }
        
        /* Custom Keyframes for Page Transitions */
        @keyframes fadeInSlideUp {
            0% { opacity: 0; transform: translateY(20px); filter: blur(5px); }
            100% { opacity: 1; transform: translateY(0); filter: blur(0); }
        }

        @keyframes pulseGlow {
            0% { box-shadow: 0 0 5px rgba(0, 51, 102, 0.2); }
            50% { box-shadow: 0 0 15px rgba(0, 51, 102, 0.5); }
            100% { box-shadow: 0 0 5px rgba(0, 51, 102, 0.2); }
        }

        /* Apply Page Transition to the main content area */
        .block-container {
            padding-top: 1rem;
            animation: fadeInSlideUp 0.8s cubic-bezier(0.16, 1, 0.3, 1) forwards;
            max_width: 1200px;
            padding-left: 2rem;
            padding-right: 2rem;
            margin: auto;
        }

        /* Responsive Breakpoint for Large Screens to prevent stretching */
        @media (min-width: 1200px) {
            .block-container {
                max-width: 1200px !important;
            }
        }
        
        /* Hide Streamlit Header/Toolbar */
        header {visibility: hidden;}
        [data-testid="stToolbar"] {visibility: hidden;}
        .stDeployButton {display:none;}

        /* CFA-Style Blue Header for Tabs (Full Width) */
        .stTabs [data-baseweb="tab-list"] {
            gap: 0px; /* Remove gap between tabs */
            background-color: transparent; 
            padding: 0px;
            border-bottom: 2px solid #003366;
        }

        .stTabs [data-baseweb="tab"] {
            flex-grow: 1; /* Stretch to fill width */
            height: 50px;
            white-space: pre-wrap;
            background-color: #f8f9fa; /* Light gray for unselected */
            transition: all 0.3s ease;
            border-radius: 0px; /* No corners */
            color: #003366; 
            font-weight: 600;
            border: none; /* Clean Look */
            display: flex;
            align-items: center;
            justify-content: center;
        }

        .stTabs [data-baseweb="tab"]:hover {
            background-color: #e9ecef;
            color: #002244;
        }

        .stTabs [aria-selected="true"] {
            background-color: #003366 !important; /* Active Blue */
            color: #ffffff !important;
            font-weight: 700;
            transform: scale(1.02);
            box-shadow: 0 4px 10px rgba(0,0,0,0.1);
        }
        
        /* Metrics & Buttons */
        div[data-testid="stMetricValue"] {
            font-size: 1.4rem !important;
            color: #003366;
            animation: fadeInSlideUp 1s ease-out;
        }
        
        /* Primary Button Blue */
        div.stButton > button:first-child {
            background-color: #003366;
            color: white;
            border-radius: 8px;
            border: none;
            padding: 0.6rem 1.2rem;
            font-weight: 600;
            transition: all 0.3s cubic-bezier(0.4, 0, 0.2, 1);
        }
        div.stButton > button:first-child:hover {
            background-color: #002244;
            color: white;
            transform: translateY(-2px);
            box-shadow: 0 6px 15px rgba(0, 51, 102, 0.3);
            animation: pulseGlow 2s infinite;
        }
        div.stButton > button:first-child:active {
            transform: translateY(0);
        }

        </style>
    """, unsafe_allow_html=True)

# --- LOCALIZATION & TEXT ASSETS ---

TRANS = {
    'EN': {
        'sidebar_title': "🏛️ Scanner Controls",
        'market_label': "Crypto Category",
        'strategy_label': "Strategy Preset",
        'mode_header': "3. Mode",
        'strict_label': "Select Strictly Enforced Metrics",
        'perf_label': "Performance Metrics",
        'val_header': "� On-Chain (Valuation)",
        'prof_header': "⚡ Momentum (Technical)",
        'risk_header': "🛡️ Risk & Volatility",
        'sector_label': "Select Narrative (Optional)",
        'lynch_label': "Select Cycle Phase (Optional)",
        'execute_btn': "🚀 Execute Crypash Scan",
        'main_title': "Crypash",
        'scan_limit': "Scan Limit",
        'results_header': "🏆 Top Coins (Cycle & On-Chain Analysis)",
        'stage1_msg': "📡 Stage 1: Fetching Universe...",
        'stage2_msg': "✅ Stage 1 Complete. Analyzing Top Candidates...",
        'no_data': "❌ No coins matched your STRICT criteria.",
        'deep_dive_title': "🔍 Deep Dive Analysis",
        'glossary_title': "📚 Crypto Glossary",
        'search_ticker': "Enter Coin Symbol (e.g. BTC-USD, ETH-USD)",
        'analyze_btn': "Analyze Coin",
        'about_title': "ℹ️ About Crypash",
        'about_desc': "Professional Crypto Analysis Platform using Cycle Theory, On-Chain Metrics (MVRV), and Power Law support bands. Designed for serious investors to find high-probability setups.",
        
        'scanner_config': "🛠️ Scanner Configuration & Settings",
        'univ_scale': "1. Universe & Scale",
        'strat_mandate': "2. Strategy Mandate",
        'crit_thresh': "3. Criteria Thresholds",
        'opt_filters': "Optional Filters",
        'analyze_top_n': "Analyze Top N Deeply (Stage 2)",
        
        'port_config': "⚙️ Portfolio Configuration", # Legacy key but keeping safe
        'asset_univ': "1. Asset Universe",
        'strat_prof': "2. Strategic Profile",
        'risk_tol': "Risk Tolerance",
        'max_holdings': "Max Holdings Count",
        'gen_port_btn': "🚀 Generate Portfolio",
        'port_target_caption': "Allocating based on Market Cap Weighting.",
        
        'status_processing': "🔄 Processing Chain Data...",
        'status_fetch': "📡 Fetching Coin List...",
        'status_scan': "🔬 Scanning On-Chain Metrics...",
        'status_scan_fail': "❌ Scan Failed: No data.",
        'status_scan_complete': "✅ Scan Complete!",
        'status_deep': "🔍 Deep Analysis (Volatility & Cycle)...",
        'status_deep_complete': "✅ Deep Analysis Complete!",
        
        'tab_holdings': "📋 Holdings",
        'tab_alloc': "🍕 Allocation",
        'tab_logic': "⚖️ Weighting Logic",
        'risk_high_desc': "🚀 **Euphoria**: Chasing parabolic moves. High risk of bag-holding.",
        
        'menu_health': "Portfolio Health",
        'menu_ai': "AI Insight",
        'under_dev': "🚧 Feature Under Development 🚧",
        'dev_soon': "Check back soon!",
        'dev_dl': "Coming soon: Machine Learning Models.",
        'biz_summary': "📝 **Project Summary**",
        'lynch_type': "Narrative Type",
        'score_garp': "Cycle Score",
        'score_value': "Value Score",
        'score_div': "Yield Score",
        'score_multi': "Alpha Score",

        # --- NEW DASHBOARD & UI ---
        'market_sentiment_title': "### 🧭 Market Sentiment (CNN-Style Proxy)",
        'fear_greed_title': "Fear & Greed Index (Proxy)",
        'vix_caption': "Driven by VIX: {vix:.2f} (Lower VIX = Higher Greed)",
        'state_extreme_fear': "🥶 Extreme Fear",
        'state_fear': "😨 Fear",
        'state_neutral': "😐 Neutral",
        'state_greed': "😎 Greed",
        'state_extreme_greed': "🤑 Extreme Greed",
        'state_extreme_greed': "🤑 Extreme Greed",
        'faq_title': "📚 Definition & Methodology (FAQs)",
        'max_pe': "Max P/E Ratio",
        'max_peg': "Max PEG Ratio",
        'max_evebitda': "Max EV/EBITDA",
        'min_roe': "Min ROE %",
        'min_margin': "Min Op Margin %",
        'min_div': "Min Dividend Yield %",
        'min_rev_growth': "Min Revenue Growth %",
        'max_de': "Max Debt/Equity %", # Reserved
        'debug_logs': "🛠️ Debug Logs (Open if No Data)",
        'port_title': "Portfoliokub",
        'ai_analysis_header': "🧠 AI Analysis Result ({risk})",
        'gen_success': "✅ Generated Professional Portfolio: {n} Coins",
        
        # Tooltips
        # Tooltips (Updated for Crypto)
        'lynch_tooltip': "",
        'lynch_desc': "Cycle Phases (Wyckoff/Market Cycle):\n- Accumulation: Smart Money buying quietly.\n- Markup: Public participation phase.\n- Distribution: Smart Money selling.\n- Markdown: Price decline.",
        'sector_tooltip': "",
        'sector_desc': "Narrative Categories (e.g. L1, DeFi, GameFi). Capital rotates between narratives.",
        'backtest_title': "🕑 Historical Backtest & Simulation",
        'backtest_desc': "See how this portfolio would have performed in the past vs S&P 500.",
        'backtest_config': "⚙️ Backtest Configuration",
        'invest_mode': "Investment Mode",
        'time_period': "Time Period",
        'invest_amount': "Investment Amount",
        'run_backtest_btn': "🚀 Run Backtest",
        'historical_chart_title': "### 🔬 Interactive Historical Charts",
        'select_stock_view': "Select Coin to View:",
        'nav_scanner': "Crypto Scanner",
        'nav_portfolio': "Auto Portfolio",
        'nav_single': "Single Coin Analysis",
        'nav_health': "Portfolio Health",
        'nav_ai': "AI Insight",
        'nav_glossary': "Crypto Glossary",
        'nav_help': "How to Use",
        'footer_caption': "Professional Crypto Analytics Platform",
        'health_check_title': "🔍 On-Chain Health Check",
        'val_label': "Valuation",
        'qual_label': "Quality",
        # Dead keys removed (Guru/Analyst/Holders)
        'no_target': "No analyst target price available.",
        'err_recs': "Could not fetch recommendations.",
        'price_trend_title': "📉 5-Year Price Trend",
        'err_fetch': "Could not fetch data.",
        'perfect_match': "✅ Perfect Match",
        'backtest_summary': "Performance Summary",
        'final_val_label': "Final Portfolio Value",
        'bench_val_label': "S&P 500 Benchmark",
        'alpha_label': "Alpha (vs Market)",
        'winning': "Winning",
        'losing': "Losing",
        'gap_annual': "Performance Gap (Annual)",
        'my_port_legend': "My Portfolio",
        'bench_legend': "S&P 500 (SPY)",
        'cagr_label': "CAGR (Avg/Year)",
        'annualized_label': "Annualized",
        'na_short': "N/A (< 1 Year)",
        'na': "N/A",
        'backtest_failed': "Backtest Failed",
        'lang_label': "Language / ภาษา",
        'health_coming_soon': "Coming soon in Q1 2026. This module will analyze your upload portfolio for risk factors.",
        'ai_coming_soon': "Deep Learning module integration in progress.",
        'tab_settings': "🎛️ Settings & Tools",
        'tab_metrics': "📊 Financial Metrics",
        'tab_lynch': "🧠 Peter Lynch Categories",
        
        'port_alloc_title': "🌍 Portfolio Allocation",
        'port_alloc_caption': "Breakdown by Individual Holding & Group",
        'type_alloc_title': "Type Allocation",
        'equity_only': "Equity Only",
        'asset_class_label': "Asset Class",
        'sector_label_short': "Sector",
        'weight_label': "Weight",
        'ticker_label': "Symbol",
        'price_label': "Price",
        'score_label': "Score",
        'rev_cagr_label': "Rev CAGR",
        'ni_cagr_label': "NI CAGR",
        'yield_label': "Yield",
        'why_mcap_title': "**Why Market Cap Weighting?**",
        'why_mcap_desc': "- **Professional Standard**: S&P 500 and Nasdaq 100 use this.\n- **Stability**: Larger, more established companies get more money.\n- **Self-Correcting**: As companies grow, they become a larger part of your portfolio naturally.",
        'how_works_title': "**How it works here:**",
        'how_works_desc': "1. We select the Top 20 stocks that match your **Strategy Score**.\n2. We allocate money based on **Company Size (Market Cap)**.",
        'how_works_desc': "1. We select the Top 20 stocks that match your **Strategy Score**.\n2. We allocate money based on **Company Size (Market Cap)**.",
    },
    'TH': {
        'sidebar_title': "🏛️ ตั้งค่าการสแกน",
        'market_label': "หมวดหมู่เหรียญ (Universe)",
        'strategy_label': "กลยุทธ์ (Strategy)",
        'mode_header': "3. โหมดคัดกรอง",
        'strict_label': "เลือกเกณฑ์คัดออก (Strict)",
        'perf_label': "เลือกช่วงเวลาวัดผล",
        'val_header': "� On-Chain (พื้นฐาน)",
        'prof_header': "⚡ Momentum (กราฟ)",
        'risk_header': "🛡️ ความผันผวน (Risk)",
        'sector_label': "เลือก Narrative (ธีมเหรียญ)",
        'lynch_label': "เลือกวัฏจักร (Cycle Phase)",
        
        # Tooltips
        'lynch_tooltip': "ℹ️",
        'lynch_desc': "วัฏจักรตลาด:\n- Accumulation: ช่วงสะสมของ (วาฬเก็บ)\n- Markup: ช่วงราคาขึ้น\n- Distribution: ช่วงกระจายของ (วาฬขาย)\n- Markdown: ช่วงราคาลง",
        'sector_tooltip': "ℹ️",
        'sector_desc': "Narrative คือธีมการลงทุน เช่น L1 (โครงสร้างพื้นฐาน), DeFi (การเงิน), Meme (เก็งกำไร)",
        
        'execute_btn': "🚀 เริ่มสแกน Crypash",
        'main_title': "Crypash",
        'scan_limit': "จำนวนจำกัดการสแกน",
        'results_header': "🏆 ผลลัพธ์เหรียญน่าสนใจ",
        'stage1_msg': "📡 กำลังดึงข้อมูลเหรียญ...",
        'stage2_msg': "✅ โหลดเสร็จสิ้น กำลังวิเคราะห์...",
        'no_data': "❌ ไม่พบเหรียญที่ตรงตามเงื่อนไข",
        'deep_dive_title': "🔍 เจาะลึกรายตัว (Deep Dive)",
        'glossary_title': "📚 คลังความรู้คริปโต",
        'search_ticker': "พิมพ์ชื่อเหรียญ (เช่น BTC-USD)",
        'analyze_btn': "วิเคราะห์เหรียญ",
        'about_title': "ℹ️ เกี่ยวกับโปรเจกต์",
        'about_desc': "แพลตฟอร์มวิเคราะห์คริปโตระดับมืออาชีพ เน้นข้อมูล On-Chain และวัฏจักรตลาด (Cycle Theory) เพื่อหาจุดเข้าซื้อที่มีโอกาสชนะสูง",

        'scanner_config': "🛠️ ตั้งค่าสแกนเนอร์",
        'univ_scale': "1. ขอบเขตการค้นหา",
        'strat_mandate': "2. กลยุทธ์",
        'crit_thresh': "3. เกณฑ์การคัดกรอง",
        'opt_filters': "ตัวกรองเสริม",
        'analyze_top_n': "วิเคราะห์เชิงลึก N ตัวบน",
        
        'port_config': "⚙️ จัดพอร์ตโฟลิโอ",
        'asset_univ': "1. สินทรัพย์",
        'strat_prof': "2. รูปแบบความเสี่ยง",
        'risk_tol': "ระดับความเสี่ยง",
        'max_holdings': "จำนวนเหรียญสูงสุด",
        'gen_port_btn': "🚀 สร้างพอร์ต",
        'port_target_caption': "จัดสรรตามมูลค่าตลาด (Market Cap Weighting)",
        
        'status_processing': "🔄 กำลังประมวลผล...",
        'status_fetch': "📡 ดึงข้อมูล...",
        'status_scan': "🔬 สแกน On-Chain...",
        'status_scan_fail': "❌ ผิดพลาด: ไม่พบข้อมูล",
        'status_scan_complete': "✅ สแกนเสร็จสิ้น!",
        'status_deep': "🔍 วิเคราะห์เชิงลึก...",
        'status_deep_complete': "✅ วิเคราะห์เสร็จสิ้น!",

        'tab_holdings': "📋 รายชื่อเหรียญ",
        'tab_alloc': "🍕 สัดส่วน (Allocation)",
        'tab_logic': "⚖️ ที่มาการคำนวณ",
        'risk_high_desc': "🚀 **Euphoria**: ซื้อตอนคนฮิต (ความเสี่ยงสูง ระวังดอย)",

        'menu_health': "ตรวจสุขภาพพอร์ต",
        'menu_ai': "AI วิเคราะห์",
        'under_dev': "🚧 กำลังพัฒนา 🚧",
        'dev_soon': "พบกันเร็วๆนี้",
        'dev_dl': "ระบบ Deep Learning กำลังมา",
        'biz_summary': "📝 **สรุปภาพรวม**",
        'lynch_type': "ประเภทวัฏจักร",
        'score_garp': "คะแนนวัฏจักร",
        'score_value': "คะแนนความคุ้มค่า",
        'score_div': "คะแนน Staking (Yield)",
        'score_multi': "🚀 คะแนน Alpha (To The Moon)",

        # --- NEW DASHBOARD & UI ---
        'market_sentiment_title': "### 🧭 สภาวะตลาด (Market Sentiment)",
        'fear_greed_title': "ดัชนี Fear & Greed (Proxy)",
        'vix_caption': "คำนวณจาก VIX: {vix:.2f} (ยิ่ง VIX ต่ำ = ตลาดพึงพอใจ/โลภ)",
        'state_extreme_fear': "🥶 กลัวสุดขีด (Extreme Fear)",
        'state_fear': "😨 กลัว (Fear)",
        'state_neutral': "😐 ปกติ (Neutral)",
        'state_greed': "😎 โลภ (Greed)",
        'state_extreme_greed': "🤑 โลภสุดขีด (Extreme Greed)",

        'faq_title': "📚 คำนิยามและระเบียบวิธี (FAQs)",
        'debug_logs': "🛠️ บันทึกการตรวจสอบ (Debug Logs)",
        'port_title': "พอร์ตฟอลิโอคับ",
        'ai_analysis_header': "🧠 ผลการวิเคราะห์ด้วย AI ({risk})",
        'gen_success': "✅ สร้างพอร์ตการลงทุนสำเร็จ: {n} เหรียญ",
        'quality_roe_label': "คุณภาพ (ROE เฉลี่ย)",
        'backtest_title': "🕑 การทดสอบย้อนหลัง (Historical Backtest)",
        'backtest_desc': "ดูผลตอบแทนในอดีตของพอร์ตนี้เปรียบเทียบกับดัชนี S&P 500",
        'backtest_config': "⚙️ ตั้งค่าการทดสอบย้อนหลัง",
        'invest_mode': "รูปแบบการลงทุน",
        'time_period': "ช่วงเวลา",
        'invest_amount': "จำนวนเงินลงทุน",
        'run_backtest_btn': "🚀 เริ่มทดสอบย้อนหลัง",
        'historical_chart_title': "### 🔬 กราฟราคาย้อนหลัง",
        'select_stock_view': "เลือกคริปโตเพื่อดูรายละเอียด:",
        'nav_scanner': "สแกนคริปโต",
        'nav_portfolio': "พอร์ตอัตโนมัติ",
        'nav_single': "วิเคราะห์รายตัว",
        'nav_health': "สุขภาพพอร์ต",
        'nav_ai': "วิเคราะห์ AI",
        'nav_glossary': "คลังคำศัพท์",
        'nav_help': "วิธีใช้งาน",
        'footer_caption': "แพลตฟอร์มวิเคราะห์คริปโตระดับมืออาชีพ",
        'health_check_title': "🔍 ตรวจสุขภาพทางการเงิน",
        'val_label': "ความถูกแพง (Valuation)",
        'qual_label': "คุณภาพธุรกิจ (Quality)",
        'guru_intel_title': "🧠 ข้อมูลจากเซียนและนักวิเคราะห์",
        'tab_holders': "🏛️ ผู้ถือคริปโตสถาบัน (Guru Proxy)",
        'tab_recs': "🗣️ คำแนะนำจากนักวิเคราะห์",
        'holders_desc': "กองทุนและสถาบันชั้นนำที่ถือคริปโตตัวนี้",
        'no_holders': "ไม่พบข้อมูลการถือคริปโตของสถาบัน",
        'err_holders': "ไม่สามารถดึงข้อมูลผู้ถือคริปโตสถาบันได้",
        'consensus_target': "ราคาเป้าหมายเฉลี่ย (Consensus)",
        'vs_current': "เทียบกับราคาปัจจุบัน",
        'no_target': "ไม่พบข้อมูลราคาเป้าหมาย",
        'err_recs': "ไม่สามารถดึงข้อมูลคำแนะนำได้",
        'price_trend_title': "📉 แนวโน้มราคาย้อนหลัง 5 ปี",
        'err_fetch': "ไม่สามารถดึงข้อมูลได้",
        'perfect_match': "✅ ผ่านเกณฑ์ทุกข้อ",
        'backtest_summary': "สรุปผลตอบแทน (Performance Summary)",
        'final_val_label': "มูลค่าพอร์ตสุทธิ",
        'bench_val_label': "ดัชนีอ้างอิง S&P 500",
        'alpha_label': "ผลตอบแทนส่วนเกิน (Alpha)",
        'winning': "ชนะตลาด",
        'losing': "แพ้ตลาด",
        'gap_annual': "ส่วนต่างผลตอบแทนต่อปี",
        'my_port_legend': "พอร์ตของฉัน",
        'bench_legend': "ดัชนี S&P 500 (SPY)",
        'cagr_label': "ผลตอบแทนเฉลี่ยต่อปี (CAGR)",
        'annualized_label': "ปรับเป็นค่ารายปี (Annualized)",
        'na_short': "N/A (ข้อมูลไม่ถึง 1 ปี)",
        'na': "N/A",
        'backtest_failed': "การทดสอบย้อนหลังล้มเหลว",
        'lang_label': "ภาษาที่แสดง / Language",
        'health_coming_soon': "จะเปิดให้ใช้งานในไตรมาสที่ 1 ปี 2026 โดยโมดูลนี้จะช่วยวิเคราะห์พอร์ตที่คุณอัปโหลดเพื่อหาปัจจัยความเสี่ยง",
        'ai_coming_soon': "กำลังอยู่ระหว่างการพัฒนาโมดูลการวิเคราะห์เชิงลึก (Deep Learning)",
        'tab_settings': "🎛️ เครื่องมือและการตั้งค่า",
        'tab_metrics': "📊 ตัวชี้วัดทางการเงิน",
        'tab_lynch': "🧠 ประเภทคริปโตตาม Peter Lynch",
        
        'port_alloc_title': "🌍 สัดส่วนการลงทุน (Allocation)",
        'port_alloc_caption': "แสดงสัดส่วนตามรายตัวและกลุ่มสินทรัพย์",
        'type_alloc_title': "สัดส่วนตามประเภทคริปโต",
        'equity_only': "เฉพาะคริปโต",
        'asset_class_label': "ประเภทสินทรัพย์",
        'sector_label_short': "อุตสาหกรรม",
        'weight_label': "น้ำหนัก %",
        'ticker_label': "ชื่อคริปโต",
        'price_label': "ราคา",
        'score_label': "คะแนน",
        'rev_cagr_label': "โตรายได้",
        'ni_cagr_label': "โตกำไร",
        'yield_label': "ปันผล",
        'why_mcap_title': "**ทำไมต้องจัดน้ำหนักตามมูลค่าตลาด (Market Cap Weighting)?**",
        'why_mcap_desc': "- **มาตรฐานสากล**: ดัชนีหลักอย่าง S&P 500 และ Nasdaq 100 ใช้ระบบนี้\n- **ความมั่นคง**: ให้เงินทำงานในบริษัทที่ใหญ่และมั่นคงกว่าในสัดส่วนที่สูงกว่า\n- **ปรับตัวอัตโนมัติ**: เมื่อบริษัทเติบโตขึ้น สัดส่วนในพอร์ตก็จะเพิ่มขึ้นเองตามธรรมชาติ",
        'how_works_title': "**หลักการทำงานของระบบ:**",
        'how_works_desc': "1. เราคัดเลือกคริปโต 20 อันดับแรกที่ได้คะแนน **Strategy Score** สูงสุด\n2. จัดสรรเงินลงทุนตาม **ขนาดของบริษัท (Market Cap)**",

        'nav_help': "คู่มือการใช้งาน (How to Use)",
    }
}

def get_text(key):
    lang = st.session_state.get('lang', 'EN')
    return TRANS[lang].get(key, key)

# --- MARKET & GURU DATA ---

@st.cache_data(ttl=3600, show_spinner=False)
def fetch_market_indicators():
    indicators = {}
    try:
        # 1. Crypto Fear & Greed (Alternative.me API)
        import requests
        try:
            r = requests.get("https://api.alternative.me/fng/", timeout=2)
            if r.status_code == 200:
                data = r.json()
                fng_val = int(data['data'][0]['value'])
                fng_class = data['data'][0]['value_classification']
                indicators['FG_Score'] = fng_val
                indicators['FG_Class'] = fng_class
        except:
             # Fallback to VIX Proxy if API fails
            vix = yf.Ticker("^VIX")
            vix_val = vix.fast_info.last_price
            score = 100 - ((vix_val - 12) / (35 - 12) * 100)
            indicators['FG_Score'] = int(max(0, min(100, score)))
            indicators['FG_Class'] = "Proxy (VIX)"

        # 2. Bitcoin Dominance Proxy (BTC Market Cap / Total - Hard to get Total from YF)
        # We'll use BTC Price Trend as "Cycle Strength"
        btc = yf.Ticker("BTC-USD")
        hist = btc.history(period="1y")
        if not hist.empty:
            current = hist['Close'].iloc[-1]
            ma200 = hist['Close'].rolling(200).mean().iloc[-1]
            indicators['Trend_Diff'] = ((current - ma200) / ma200) * 100
            
    except Exception as e:
        print(f"Market Data Error: {e}")
        
    return indicators

def render_market_dashboard():
    data = fetch_market_indicators()
    if not data: return 

    st.markdown(get_text('market_sentiment_title'))
    
    # --- ROW 1: FEAR & GREED + CYCLE ---
    c1, c2 = st.columns([1, 1])
    
    with c1:
        score = data.get('FG_Score', 50)
        state = data.get('FG_Class', 'Neutral')
        
        # Color Logic
        if score < 25: color = "red"
        elif score > 75: color = "green"
        else: color = "orange"
        
        st.metric(get_text('fear_greed_title'), f"{score}/100", state)
        st.progress(score / 100)
        st.caption("Source: Alternative.me")

    with c2:
        # Cycle Strength (BTC vs 200DMA)
        trend = data.get('Trend_Diff', 0)
        st.metric("Bitcoin Bull Market Support", f"{trend:+.1f}%", "Above 200 DMA" if trend > 0 else "Below Support")
        st.caption("Distance from 200-Day Moving Average. > 0% is Bullish.")
        if trend > 0: st.success("Bitcon is in a Bull Trend 🐂")
        else: st.error("Bitcoin is in a Bear/Correction Trend 🐻")

    # --- ROW 2: FAQs ---
    with st.expander(get_text('faq_title')):
        st.markdown("""
        **What is the Fear & Greed Index?**  
        It is a way to gauge stock market movements and whether stocks are fairly priced. The logic is that **excessive fear drives prices down** (opportunity), and **too much greed drives them up** (correction risk).

        **How is it Calculated? (Official vs Proxy)**  
        - *Official (CNN)*: Compiles 7 indicators (Momentum, Strength, Breadth, Options, Junk Bonds, Volatility, Safe Haven).  
        - *Our Proxy*: We rely primarily on **Volatility (VIX)** and **Market Momentum** due to real-time data availability.

        **Scale:**  
        - **0-25**: Extreme Fear 🥶  
        - **25-45**: Fear 😨  
        - **45-55**: Neutral 😐  
        - **55-75**: Greed 😎  
        - **75-100**: Extreme Greed 🤑
        """)



# ---------------------------------------------------------
# 1. Page Configuration
# ---------------------------------------------------------
st.set_page_config(
    page_title="Crypash",
    page_icon="🪙",
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



# --- CRYPTO UNIVERSE DATA ---
@st.cache_data(ttl=86400)
def get_crypto_universe(category='Top 50'):
    """
    Returns a list of Yahoo Finance tickers for Cryptocurrencies.
    Examples: 'BTC-USD', 'ETH-USD'
    """
    
    # 1. Top 50 (Market Cap Proxy)
    top_50 = [
        'BTC-USD', 'ETH-USD', 'BNB-USD', 'SOL-USD', 'XRP-USD', 'DOGE-USD', 'ADA-USD', 'SHIB-USD', 
        'AVAX-USD', 'TRX-USD', 'DOT-USD', 'LINK-USD', 'MATIC-USD', 'UNI-USD', 'LTC-USD', 
        'BCH-USD', 'ATOM-USD', 'XLM-USD', 'ETC-USD', 'XMR-USD', 'FIL-USD', 'HBAR-USD', 
        'APT-USD', 'CRO-USD', 'LDO-USD', 'ARB-USD', 'NEAR-USD', 'VET-USD', 'MKR-USD', 
        'QNT-USD', 'AAVE-USD', 'GRT-USD', 'ALGO-USD', 'STX-USD', 'SAND-USD', 'EGLD-USD', 
        'THETA-USD', 'FTM-USD', 'EOS-USD', 'MANA-USD', 'FLOW-USD', 'AXS-USD', 'NEO-USD',
        'XTZ-USD', 'KCS-USD', 'CHZ-USD', 'GALA-USD', 'KLAY-USD', 'RUNE-USD', 'CRV-USD',
        # Top 100-200 Extension
        'HBAR-USD', 'VET-USD', 'ICP-USD', 'FIL-USD', 'EGLD-USD', 'MANA-USD', 'SAND-USD',
        'AXS-USD', 'THETA-USD', 'EOS-USD', 'AAVE-USD', 'FLOW-USD', 'QNT-USD', 'GRT-USD',
        'SNX-USD', 'NEO-USD', 'XEC-USD', 'MKR-USD', 'KLAY-USD', 'GNO-USD', 'CAKE-USD',
        'CFX-USD', 'ROSE-USD', 'WOO-USD', 'LUNC-USD', 'ZEC-USD', 'IOTA-USD', 'DASH-USD',
        'COMP-USD', 'FXS-USD', 'LRC-USD', 'ZIL-USD', 'DYDX-USD', 'CVX-USD', 'ENJ-USD',
        'BAT-USD', 'TWT-USD', 'MINA-USD', 'RVN-USD', 'XEM-USD', '1INCH-USD', 'HOT-USD',
        'GLM-USD', 'CELO-USD', 'KSM-USD', 'NEXO-USD', 'BAL-USD', 'JASMY-USD', 'AR-USD',
        'QTUM-USD', 'ANKR-USD', 'TFUEL-USD', 'ONT-USD', 'KAVA-USD', 'ILV-USD', 'GMT-USD',
        'YFI-USD', 'MASK-USD', 'JST-USD', 'GLMR-USD', 'WBTC-USD', 'BTT-USD', 'SXP-USD'
    ]

    # ... existing categories ...
    l1 = [
        'BTC-USD', 'ETH-USD', 'SOL-USD', 'ADA-USD', 'AVAX-USD', 'TRX-USD', 'DOT-USD', 
        'ATOM-USD', 'NEAR-USD', 'ALGO-USD', 'FTM-USD', 'SUI-USD', 'SEI-USD', 'TIA-USD',
        'APT-USD', 'INJ-USD', 'KAS-USD', 'TON-USD', 'MINA-USD', 'HBAR-USD'
    ]
    
    # Combined Large List (~250+ Tickers covering Bitkub Major, L1, DeFi, GameFi, Meme, AI)
    all_market = list(set(top_50 + l1 + [
        # Major & Stable (Bitkub Group 1-2)
        'BTC-USD', 'ETH-USD', 'BCH-USD', 'XRP-USD', 'LTC-USD', 'BNB-USD', 'USDT-USD', 'USDC-USD', 'DAI-USD',
        # L1/Platform (Group 3)
        'ADA-USD', 'SOL-USD', 'DOT-USD', 'AVAX-USD', 'NEAR-USD', 'MATIC-USD', 'OP-USD', 'ARB-USD', 'TRX-USD', 
        'FTM-USD', 'ATOM-USD', 'SUI-USD', 'SEI-USD', 'IOST-USD', 'ZIL-USD', 'HBAR-USD', 'CELO-USD',
        # Meme (Group 4)
        'DOGE-USD', 'SHIB-USD', 'BONK-USD', 'PEPE-USD', 'FLOKI-USD', 'MEME-USD', 
        # GameFi (Group 5)
        'SAND-USD', 'MANA-USD', 'GALA-USD', 'AXS-USD', 'ENJ-USD', 'ILV-USD', 'APE-USD', 'BLUR-USD', 'CHZ-USD',
        # DeFi (Group 6)
        'LINK-USD', 'UNI-USD', 'AAVE-USD', 'CRV-USD', 'MKR-USD', 'COMP-USD', 'SUSHI-USD', 'BAND-USD',
        # AI & New (Group 7)
        'TAO-USD', 'RNDR-USD', 'WLD-USD', 'IMX-USD', 'LDO-USD', 'INJ-USD', 'DYDX-USD', 'GRT-USD', 'LUNC-USD',
        # Extended Market (Top 100-300 Fillers)
        'STX-USD', 'FIL-USD', 'VET-USD', 'QNT-USD', 'THETA-USD', 'EOS-USD', 'FLOW-USD', 'EGLD-USD', 'XTZ-USD', 'KCS-USD',
        'RUNE-USD', 'FXS-USD', 'KAVA-USD', 'MINA-USD', 'GNO-USD', '1INCH-USD', 'WOO-USD', 'ROSE-USD', 'AGIX-USD', 'FET-USD',
        'OCEAN-USD', 'AKT-USD', 'STRK-USD', 'ORDI-USD', 'TIA-USD', 'KAS-USD', 'TON-USD', 'XLM-USD', 'XMR-USD', 'ETC-USD',
        'BGB-USD', 'LEO-USD', 'OKB-USD', 'CRO-USD', 'MNT-USD', 'BSV-USD', 'ALGO-USD', 'BEAM-USD', 'ASTR-USD', 'GLM-USD',
        'LRC-USD', 'BAT-USD', 'TWT-USD', 'CVX-USD', 'BAL-USD', 'YFI-USD', 'ZEC-USD', 'IOTA-USD', 'NEO-USD', 'DASH-USD',
        'QTUM-USD', 'XEM-USD', 'RVN-USD', 'HOT-USD', 'ZRX-USD', 'ANKR-USD', 'ICX-USD', 'WAVES-USD', 'OMG-USD', 'SC-USD'
    ]))

    if category == 'Layer 1': return l1
    if category == 'DeFi': return defi
    if category == 'Meme': return meme
    if category == 'AI & Big Data': return ai_coins
    if category == 'All (Top 200)': return all_market
    
    # Default to Top 50
    return top_50


# --- CRYPTO METRIC HELPERS ---
def calculate_rsi(series, period=14):
    delta = series.diff()
    gain = (delta.where(delta > 0, 0)).rolling(window=period).mean()
    loss = (-delta.where(delta < 0, 0)).rolling(window=period).mean()
    rs = gain / loss
    return 100 - (100 / (1 + rs))

def calculate_macd(close, fast=12, slow=26, signal=9):
    exp1 = close.ewm(span=fast, adjust=False).mean()
    exp2 = close.ewm(span=slow, adjust=False).mean()
    macd = exp1 - exp2
    signal_line = macd.ewm(span=signal, adjust=False).mean()
    hist = macd - signal_line
    return macd, signal_line, hist

def calculate_atr(high, low, close, period=14):
    high_low = high - low
    high_close = (high - close.shift()).abs()
    low_close = (low - close.shift()).abs()
    ranges = pd.concat([high_low, high_close, low_close], axis=1)
    true_range = ranges.max(axis=1)
    return true_range.rolling(period).mean()

def calculate_adx(high, low, close, period=14):
    plus_dm = high.diff()
    minus_dm = low.diff()
    plus_dm[plus_dm < 0] = 0
    minus_dm[minus_dm > 0] = 0
    
    tr = calculate_atr(high, low, close, period=1) # TR for ADX calc
    atr = tr.rolling(period).mean()
    
    plus_di = 100 * (plus_dm.ewm(alpha=1/period).mean() / atr)
    minus_di = 100 * (minus_dm.abs().ewm(alpha=1/period).mean() / atr)
    dx = (abs(plus_di - minus_di) / (plus_di + minus_di)) * 100
    adx = dx.rolling(period).mean()
    return adx

def calculate_mvrv_z_proxy(series, window=200):
    ma = series.rolling(window=window).mean()
    std = series.rolling(window=window).std()
    z_score = (series - ma) / std
    return z_score

# --- Stage 1: Fast Scan (Batch) ---
def scan_market_basic(tickers, progress_bar, status_text, debug_container=None):
    data_list = []
    status_text.text("Stage 1: Fetching Market Data (Batch Mode)...")
    
    if not tickers: return pd.DataFrame()
    
    import pandas as pd
    
    # Batch Download for Speed
    try:
        data = yf.download(tickers, period="2y", group_by='ticker', threads=True)
    except Exception as e:
        status_text.error(f"Download Failed: {e}")
        return pd.DataFrame()

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
            
            narrative = classify_narrative(ticker)
            
            # 5. Price Change
            price = closes.iloc[-1]
            chg_7d = (price - closes.iloc[-8]) / closes.iloc[-8] * 100 if len(closes) > 7 else 0
            chg_30d = (price - closes.iloc[-31]) / closes.iloc[-31] * 100 if len(closes) > 31 else 0
            
            
            # 3. Risk Score (20%)
            risk_s = 50
            if vol_30d < 60: risk_s = 100
            elif vol_30d > 120: risk_s = 0
            else: risk_s = 100 - ((vol_30d - 60) / 60 * 100)
            risk_s = max(0, min(100, int(risk_s)))
            
            # 4. Sent Score (20%) - Volume Proxy
            sent_s = 50
            try:
                vol_curr = hist['Volume'].iloc[-1]
                vol_avg = hist['Volume'].tail(30).mean()
                if vol_avg > 0:
                    vol_r = vol_curr / vol_avg
                    if vol_r > 1.5: sent_s = 80
                    elif vol_r < 0.5: sent_s = 30
                
                # Bull Market Sentiment (SMA200 reused)
                if price > sma200_val: sent_s = 80
            except: pass
            
            # --- PRO SCORE CALCULATION (Centralized Expert Engine) ---
            scores = calculate_crypash_score(ticker, hist)
            total_pro_score = scores['total']
            
            analysis_str = "Neutral"
            if total_pro_score >= 75: analysis_str = "💎 Elite"
            elif total_pro_score >= 55: analysis_str = "✅ Buy"
            elif total_pro_score <= 35: analysis_str = "⚠️ Avoid"
            
            data_list.append({
                'Symbol': ticker,
                'Narrative': narrative,
                'Price': price,
                'Pro_Score': total_pro_score,
                'Pro_Rating': analysis_str,
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
            
    if not data_list:
        return pd.DataFrame()
        
    return pd.DataFrame(data_list)



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
        stock = row['YF_Obj']
        status_text.caption(f"Stage 2: Deep Analysis of **{ticker}** ({i+1}/{total})")
        
        # Metrics
        consistency_str = "N/A"
        insight_str = ""
        cagr_rev = None
        cagr_ni = None
        div_streak_str = "None"

        try:
            # Price Performance (NEW)
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
            'Insight': insight_str if insight_str else "Stable"
        }
        # Merge perf metrics
        data_item.update(perf)
        enhanced_data.append(data_item)
        
    return pd.DataFrame(enhanced_data)

# ---------------------------------------------------------
# 3. Classifications & Scoring
# ---------------------------------------------------------
# ---------------------------------------------------------
# 3. Classifications & Scoring (Crypto Native)
# ---------------------------------------------------------
def classify_narrative(ticker):
    """
    Classifies coins into Crypto Narratives / Sectors.
    """
    t = ticker.upper()
    
    # 1. Store of Value
    if 'BTC' in t or 'PAXG' in t or 'XAUT' in t: return "👑 Store of Value"
    
    # 2. Smart Contracts (L1)
    l1s = ['ETH', 'SOL', 'ADA', 'BNB', 'AVAX', 'TRX', 'DOT', 'ATOM', 'NEAR', 'ALGO', 'SUI', 'SEI', 'APT', 'FTM']
    if any(x in t for x in l1s): return "🏗️ Smart Contract (L1)"
    
    # 3. DeFi
    defi = ['UNI', 'AAVE', 'MKR', 'LDO', 'CRV', 'SNX', 'COMP', 'RPL', 'GMX', 'DYDX', 'JUP']
    if any(x in t for x in defi): return "🏦 DeFi & Yield"
    
    # 4. Scaling (L2)
    l2s = ['MATIC', 'ARB', 'OP', 'IMX', 'MNT', 'STRK']
    if any(x in t for x in l2s): return "⚡ Layer 2 (Scaling)"
    
    # 5. Meme
    memes = ['DOGE', 'SHIB', 'PEPE', 'WIF', 'BONK', 'FLOKI', 'MEME']
    if any(x in t for x in memes): return "🤡 Meme / High Beta"
    
    # 6. AI & DePIN
    ai = ['RNDR', 'FET', 'TAO', 'AKT', 'OCEAN', 'AGIX', 'WLD']
    if any(x in t for x in ai): return "🤖 AI & DePIN"
    
    return "🪙 Altcoin"



# ---------------------------------------------------------
# PAGES
# ---------------------------------------------------------

def page_scanner():
    c_title, c_link = st.columns([3, 1])
    with c_title:
        st.title(get_text('main_title'))
    with c_link:
        st.markdown("<br> [**Check out Stockub 📈**](https://stockub.streamlit.app/)", unsafe_allow_html=True)
    st.info(get_text('about_desc'))

    # --- PROFESSIONAL UI: MAIN CONFIGURATION ---
    # Moved all controls from Sidebar to Main Page Expander
    with st.expander("🛠️ **Scanner Configuration & Settings**", expanded=True):
        
        # Row 1: High Level Strategy
        c_uni, c_strat = st.columns(2)
        with c_uni:
             st.subheader("1. Crypto Universe")
             market_choice = st.selectbox("Select Category", ["Top 50", "Layer 1", "DeFi", "Meme", "AI & Big Data", "All (Top 200)"])
             num_stocks = st.slider(get_text('scan_limit'), 10, 200, 50)
             top_n_deep = st.slider("Analyze Top N Deeply (Stage 2)", 5, 20, 10)
        
        with c_strat:
             st.subheader("2. Strategy Mandate")
             strategy = st.selectbox("Strategy Profile", ["Cycle Hunter (Z-Score)", "Momentum (Trend)", "DeFi Yield", "All Coins"])
             
             # Mode & Period
             strict_criteria = st.multiselect("Active Filters", 
                                                  ["MVRV_Z", "RSI", "Vol_30D"],
                                                  default=[],
                                                  help="Filter out coins that don't meet these criteria")
             perf_metrics_select = st.multiselect(get_text('perf_label'),
                                                     ["7D", "30D", "YTD", "1Y"],
                                                     default=["7D", "30D"],
                                                     help="Show price change %")

        st.markdown("---")
        
        # Row 2: Detailed Thresholds
        st.subheader("3. Criteria Thresholds")
        
        # Default Crypto Settings (Professional "Whale" Setup)
        c_mvrv, c_rsi, c_risk = st.columns(3)

        with c_mvrv:
            st.markdown("##### 🐋 On-Chain (Valuation)")
            st.caption("Identify accumulations or overheated zones.")
            val_mvrv = st.slider("Max MVRV Z-Score", min_value=-3.0, max_value=10.0, value=3.5, step=0.1, help="< 0: Undervalued (Bottom), > 3.5: Overvalued (Top)")
            
        with c_rsi:
            st.markdown("##### ⚡ Momentum (Technical)")
            st.caption("Catch reversals or trend strength.")
            val_rsi = st.slider("Max RSI (14D)", min_value=10, max_value=90, value=75, step=5, help="> 70: Overbought, < 30: Oversold")
            
        with c_risk:
            st.markdown("##### 🛡️ Risk & Volatility")
            st.caption("Filter out extreme volatility.")
            risk_vol = st.slider("Max 30D Volatility %", min_value=10, max_value=200, value=150, step=10)

        # Removed Stock Sectors & Lynch Categories as they don't apply
        selected_sectors = [] 
        selected_lynch = []

    st.caption(f"Universe: {market_choice} | Strategy: {strategy} | Scan Limit: {num_stocks}")

    if 'scan_results' not in st.session_state: st.session_state['scan_results'] = None
    if 'deep_results' not in st.session_state: st.session_state['deep_results'] = None

    
    # DEBUG EXPANDER
    debug_container = st.expander("🛠️ Debug Logs (Open if No Data)", expanded=False)

    if st.button(get_text('execute_btn'), type="primary"):
        # --- STAGE 1 ---
        tickers = []
        with st.spinner(get_text('stage1_msg')):
            tickers = get_crypto_universe(market_choice)
            tickers = tickers[:num_stocks]
        
        st.info(f"Stage 1: Scanning {len(tickers)} coins")
        df = scan_market_basic(tickers, st.progress(0), st.empty(), debug_container)

        if not df.empty:
            original_len = len(df)
            
            # Strict Logic
            if strict_criteria:
                if "MVRV_Z" in strict_criteria: df = df[df['MVRV_Z'] <= val_mvrv]
                if "RSI" in strict_criteria: df = df[df['RSI'] <= val_rsi]
                if "Vol_30D" in strict_criteria: df = df[df['Vol_30D'] <= risk_vol]

            st.session_state['scan_results'] = df
            # Skip Deep Results merge for now as we don't have deep analysis function updated yet
            st.session_state['deep_results'] = df 

            if df.empty:
                st.warning(get_text('no_data'))
        else:
            st.error("No data found.")

    # Display Logic
    if st.session_state['scan_results'] is not None:
        df = st.session_state['scan_results']
        
        # FIX: Check if cached DF has new columns. If not, clear and rerun.
        if 'Pro_Score' not in df.columns:
            st.session_state['scan_results'] = None
            st.rerun()
            return
        
        st.markdown(f"### {get_text('results_header')}")
        
        # Color Styling for Cycle State
        # Color Styling for Cycle State & Rating
        def color_cycle(val):
            # Pro Rating Colors
            if isinstance(val, str):
                if "Elite" in val: return "background-color: #d1e7dd; color: #0f5132; font-weight: bold" # Success Green
                if "Buy" in val: return "color: #198754; font-weight: bold"
                if "Avoid" in val: return "color: #dc3545"
                # Cycle Colors
                if "Accumulation" in val: return "background-color: #d4edda; color: #155724; font-weight: bold"
                if "Euphoria" in val: return "background-color: #f8d7da; color: #721c24; font-weight: bold"
                if "Greed" in val: return "background-color: #fff3cd; color: #856404"
            return ""

        # Columns to display
        display_cols = ['Symbol', 'Narrative', 'Pro_Score', 'Pro_Rating', 'Price', 'Cycle_State', 'MVRV_Z', 'RSI', 'Vol_30D', '7D', '30D']
        
        st.dataframe(
            df[display_cols].style.applymap(color_cycle, subset=['Cycle_State', 'Pro_Rating'])
            .format({
                'Price': '${:,.2f}',
                'MVRV_Z': '{:.2f}',
                'RSI': '{:.1f}',
                'Vol_30D': '{:.1f}%',
                '7D': '{:+.1f}%',
                '30D': '{:+.1f}%'
            }),
            column_config={
                "Pro_Score": st.column_config.ProgressColumn("Pro Score (0-100)", min_value=0, max_value=100, format="%d"),
                "MVRV_Z": st.column_config.NumberColumn("On-Chain Z-Score", help="< 0 is Buy, > 3 is Sell"),
                "RSI": st.column_config.ProgressColumn("Momentum (RSI)", min_value=0, max_value=100, format="%.0f"),
                "Cycle_State": "Cycle Evaluation"
            },
            hide_index=True,
            use_container_width=True
        ) 

        # --- Manual Deep Dive Section ---
        st.markdown("---")
        st.header("🔬 Interactive Historical Charts")
        st.info("Select a coin to visualize historical trends.")
        
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
                        stock_obj = None
                    
                    if stock_obj is None:
                        stock_obj = yf.Ticker(selected_ticker)
                    
                    
                    # CRYPTO: Show Price History instead of Financials
                    hist_data = stock_obj.history(period="1y")
                    if not hist_data.empty:
                        st.subheader(f"📈 {selected_ticker} Price Action (1Y)")
                        st.line_chart(hist_data['Close'])
                        
                        # Show Volume if available
                        if 'Volume' in hist_data.columns:
                            st.caption("Volume Trend")
                            st.bar_chart(hist_data['Volume'])
                    else:
                        st.warning("No price history available for this coin.")

        # Cache Clearing for Debugging
        # Cache Clearing for Debugging
        if st.checkbox("Show Advanced Options", key='adv_opt'):
            if st.button("🗑️ Clear Data Cache"):
                st.cache_data.clear()
                st.success("Cache Cleared! Rerun the scan.")
    
    elif st.session_state.get('scan_results') is None:
         # Only show this if no results AND no scan happening
         # But wait, if we are just idling, we don't want error.
         pass
         # st.info("Define parameters and start the Two-Stage Screening.")


def calculate_power_law_btc(days_since_genesis):
    """
    Giovanni Santostasi's Power Law for Bitcoin:
    Price = 10^-17 * (days)^5.8 roughly.
    We'll use a simplified fit for demo purposes or exact params if known.
    Model: Price = 10 ** ( -17.3 + 5.8 * log10(days) )
    Genesis: 2009-01-03
    """
    import math
    try:
        if days_since_genesis <= 0: return 0
        log_days = math.log10(days_since_genesis)
        # Parameters approximated from public charts
        log_price = -17.3 + 5.8 * log_days
        return 10 ** log_price
    except:
        return 0

def calculate_cycle_risk(current_price, ath):
    """
    Simple Risk Gauge: Dist form ATH.
    If Price ~= ATH, Risk is High (Local Top).
    If Price << ATH, Risk is Lower (Drawdown).
    """
    if not ath or ath == 0: return 0.5
    drawdown = (current_price - ath) / ath
    # Drawdown is negative e.g. -0.8
    # Risk Metric (0 to 1): 1 = At ATH (High Risk), 0 = -85% Down (Low Risk)
    
    # Map -0.85 (Low Risk) to 0.1
    # Map 0.0 (High Risk) to 0.9
    risk = 1.0 + drawdown # e.g. 1 + (-0.2) = 0.8
    return max(0.1, min(0.95, risk))

def calculate_stoch_rsi(series, period=14, smoothK=3, smoothD=3):
    """
    StochRSI = (RSI - MinRSI) / (MaxRSI - MinRSI)
    """
    delta = series.diff()
    gain = (delta.where(delta > 0, 0)).rolling(period).mean()
    loss = (-delta.where(delta < 0, 0)).rolling(period).mean()
    rs = gain / loss
    rsi = 100 - (100 / (1 + rs))
    
    stoch_rsi = (rsi - rsi.rolling(period).min()) / (rsi.rolling(period).max() - rsi.rolling(period).min())
    k = stoch_rsi.rolling(smoothK).mean() * 100
    d = k.rolling(smoothD).mean()
    return k, d

def calculate_cci(high, low, close, period=20):
    tp = (high + low + close) / 3
    sma = tp.rolling(period).mean()
    mad = tp.rolling(period).apply(lambda x: pd.Series(x).mad())
    cci = (tp - sma) / (0.015 * mad)
    return cci

# ---------------------------------------------------------
# PRO INTELLIGENCE SCORING (Startup Grade)
# ---------------------------------------------------------
def calculate_crypash_score(ticker, hist, info=None):
    """
    ULTIMATE EXPERT SCORING ENGINE (15+ Metrics)
    Pillars: On-Chain (35%), Momentum (25%), Risk (20%), Sentiment (20%).
    Includes Structural Proxies for missing On-Chain data.
    """
    score_cards = {
        'total': 0, 
        'value': 0, 'momentum': 0, 'health': 0, 'sentiment': 0,
        'details': {'value': [], 'momentum': [], 'health': [], 'sentiment': []},
        'analysis': []
    }
    
    current_price = hist['Close'].iloc[-1]
    ath = hist['Close'].max()
    vol_30d = hist['Close'].pct_change().std() * (365**0.5) * 100 
    
    # ==============================================================================
    # 1. ON-CHAIN & VALUATION (35%)
    # Metrics: MVRV, NUPL Proxy, Netflow Proxy, Whale Proxy
    # ==============================================================================
    onchain_score = 0
    onchain_count = 0
    
    # A. MVRV Z-Score (The King)
    mvrv = calculate_mvrv_z_proxy(hist['Close']).iloc[-1] if len(hist) > 200 else 1.0
    if mvrv <= -0.5: 
        onchain_score += 100; onchain_count += 3 # Weighted x3
        score_cards['details']['value'].append(f"MVRV Z: {mvrv:.2f} (Undervalued) [++Strong Buy]")
    elif mvrv >= 3.5: 
        onchain_score += 0; onchain_count += 3
        score_cards['details']['value'].append(f"MVRV Z: {mvrv:.2f} (Overheated) [Sell]")
    elif 0 < mvrv < 3.5:
        onchain_score += (100 - (mvrv / 3.5 * 100)); onchain_count += 3
        score_cards['details']['value'].append(f"MVRV Z: {mvrv:.2f} (Fair Value)")

    # B. NUPL Proxy (Net Unrealized Profit/Loss) -> Modeled via RSI + MVRV blend
    # If RSI low + MVRV low = Capitulation (Negative NUPL)
    rsi = calculate_rsi(hist['Close']).iloc[-1]
    nupl_state = "Neutral"
    if mvrv < 0 and rsi < 40: nupl_state = "Capitulation (<0)"; nupl_score = 100
    elif mvrv > 3 and rsi > 70: nupl_state = "Euphoria (>0.7)"; nupl_score = 0
    else: nupl_score = 50
    onchain_score += nupl_score; onchain_count += 1
    score_cards['details']['value'].append(f"NUPL (Proxy): {nupl_state}")

    # C. Exchange Netflow Proxy (Structural)
    # Theory: Low Volatility + Consolidation = Outflow (Accumulation)
    # Theory: High Volatility + Price Drop = Inflow (Panic Selling)
    recent_vol = hist['Close'].pct_change().tail(7).std() * 100
    netflow_score = 50
    if recent_vol < 2.0: # Very stable price action
        netflow_score = 80
        score_cards['details']['value'].append("Netflow: Potential Outflow (Accumulation)")
    elif recent_vol > 5.0 and current_price < hist['Close'].iloc[-7]:
        netflow_score = 20
        score_cards['details']['value'].append("Netflow: Potential Inflow (Panic)")
    onchain_score += netflow_score; onchain_count += 1
    
    # D. Whale Accumulation Score (Volume Divergence)
    # Rising Volume with Flat/Rising Price = Buying
    whale_score = 50
    try:
        vol_sma20 = hist['Volume'].rolling(20).mean().iloc[-1]
        vol_curr = hist['Volume'].iloc[-1]
        price_sma20 = hist['Close'].rolling(20).mean().iloc[-1]
        
        if vol_curr > vol_sma20 * 1.5 and current_price <= price_sma20 * 1.05:
            whale_score = 100
            score_cards['details']['value'].append("Whale Activity: Aggressive Buying detected")
        elif vol_curr > vol_sma20 and current_price < price_sma20:
            whale_score = 80
            score_cards['details']['value'].append("Whale Activity: Accumulation")
        else:
            score_cards['details']['value'].append("Whale Activity: Neutral")
    except: pass
    onchain_score += whale_score; onchain_count += 1
    
    score_cards['value'] = int(onchain_score / max(1, onchain_count))

    # ==============================================================================
    # 2. MOMENTUM (25%)
    # Metrics: RSI, Stoch RSI, MACD, ADX, CCI, EMA Trend
    # ==============================================================================
    mom_score_sum = 0
    mom_count = 0
    
    # A. RSI (14)
    if rsi <= 30: rsis = 100; score_cards['details']['momentum'].append(f"RSI: {rsi:.1f} (Oversold)")
    elif rsi >= 70: rsis = 0; score_cards['details']['momentum'].append(f"RSI: {rsi:.1f} (Overbought)")
    else: rsis = 50
    mom_score_sum += rsis; mom_count += 1
    
    # B. Stoch RSI
    try:
        k, d = calculate_stoch_rsi(hist['Close'])
        k_val = k.iloc[-1]
        if k_val < 20: stoch_s = 90; score_cards['details']['momentum'].append(f"Stoch RSI: {k_val:.1f} (Bottom)")
        elif k_val > 80: stoch_s = 10; score_cards['details']['momentum'].append(f"Stoch RSI: {k_val:.1f} (Top)")
        else: stoch_s = 50
        mom_score_sum += stoch_s; mom_count += 1
    except: pass
    
    # C. MACD
    macd, signal_line, _ = calculate_macd(hist['Close'])
    if macd.iloc[-1] > signal_line.iloc[-1]: 
        mom_score_sum += 100; mom_count += 1
        score_cards['details']['momentum'].append("MACD: Bullish")
    else:
        mom_score_sum += 20; mom_count += 1
        score_cards['details']['momentum'].append("MACD: Bearish")
        
    # D. ADX (Strength)
    adx = calculate_adx(hist['High'], hist['Low'], hist['Close']).iloc[-1]
    if adx > 25: 
        mom_score_sum += 80; mom_count += 1
        score_cards['details']['momentum'].append(f"ADX: {adx:.1f} (Strong Trend)")
        
    # E. CCI (Commodity Channel Index)
    try:
        cci = calculate_cci(hist['High'], hist['Low'], hist['Close']).iloc[-1]
        if cci < -100: cci_s = 90; score_cards['details']['momentum'].append("CCI: Oversold (< -100)")
        elif cci > 100: cci_s = 10; score_cards['details']['momentum'].append("CCI: Overbought (> 100)")
        else: cci_s = 50
        mom_score_sum += cci_s; mom_count += 1
    except: pass
    
    score_cards['momentum'] = int(mom_score_sum / max(1, mom_count))

    # ==============================================================================
    # 3. RISK & HEALTH (20%)
    # Metrics: Volatility, Drawdown, Liquidity Ratio
    # ==============================================================================
    risk_sum = 0
    risk_count = 0
    
    # A. Volatility
    if vol_30d < 60: vs = 100; score_cards['details']['health'].append(f"Vol: {vol_30d:.0f}% (Safe)")
    elif vol_30d > 120: vs = 0; score_cards['details']['health'].append(f"Vol: {vol_30d:.0f}% (High Risk)")
    else: vs = 50
    risk_sum += vs; risk_count += 1
    
    # B. Drawdown
    dd_pct = (current_price - ath) / ath
    if dd_pct > -0.3: ds = 80; score_cards['details']['health'].append(f"DD: {dd_pct*100:.0f}% (Resilient)")
    elif dd_pct < -0.8: ds = 40; score_cards['details']['health'].append(f"DD: {dd_pct*100:.0f}% (Deep Value/Risk)")
    else: ds = 60
    risk_sum += ds; risk_count += 1
    
    # C. Liquidity Ratio (Vol / MarketCap) - Proxy using Price*Vol as liquidity score
    # We don't have Mcap easily in history without info, assuming Volume represents liquidity depth
    avg_vol_usd = (hist['Volume'] * hist['Close']).rolling(30).mean().iloc[-1]
    if avg_vol_usd > 1_000_000: ls = 100 # > $1M daily vol
    elif avg_vol_usd < 100_000: ls = 20 # Illiquid
    else: ls = 60
    risk_sum += ls; risk_count += 1
    score_cards['details']['health'].append(f"Liq Depth: ${avg_vol_usd/1e6:.1f}M/day")
    
    score_cards['health'] = int(risk_sum / max(1, risk_count))
    
    # ==============================================================================
    # 4. SENTIMENT (20%)
    # Metrics: Funding Proxy, Open Interest Proxy
    # ==============================================================================
    sent_sum = 0
    sent_count = 0
    has_sentiment = True
    
    # A. Funding Rate Proxy (Heat)
    # Price vs SMA20. If Price >>> SMA20, Funding is likely positive (Longs paying Shorts)
    sma20 = hist['Close'].rolling(20).mean().iloc[-1]
    dev = (current_price - sma20) / sma20
    if dev > 0.15: # +15% over SMA20
        fs = 20 # Crowded Longs
        score_cards['details']['sentiment'].append("Funding Est: Overheated (>0.01%)")
    elif dev < -0.1:
        fs = 90 # Crowded Shorts (Short Squeeze potential)
        score_cards['details']['sentiment'].append("Funding Est: Negative (Shorts Crowded)")
    else:
        fs = 60
        score_cards['details']['sentiment'].append("Funding Est: Neutral")
    sent_sum += fs; sent_count += 1
    
    # B. Open Interest Proxy (Volume Trend)
    try:
        vol_change = hist['Volume'].diff().rolling(3).mean().iloc[-1]
        if vol_change > 0 and current_price > sma20:
            os = 80
            score_cards['details']['sentiment'].append("OI Proxy: Rising (Bullish)")
        else:
            os = 50
    except: os = 50
    sent_sum += os; sent_count += 1
    
    score_cards['sentiment'] = int(sent_sum / max(1, sent_count))
        
    # --- Composite Weighting ---
    total_score = (score_cards['value'] * 0.35) + \
                  (score_cards['momentum'] * 0.25) + \
                  (score_cards['health'] * 0.20) + \
                  (score_cards['sentiment'] * 0.20)
                  
    # Expert Penalties
    if vol_30d > 120: 
        total_score -= 15
        score_cards['analysis'].append("⚠️ Penalty: High Vol (-15)")
        
    score_cards['total'] = max(0, min(100, int(total_score)))
    
    # Final Analysis Tag
    if score_cards['total'] >= 75: score_cards['analysis'].append("💎 **Strong Buy**: Institutional Grade.")
    elif score_cards['total'] >= 50: score_cards['analysis'].append("✅ **Buy**: Healthy Structure.")
    elif score_cards['total'] >= 30: score_cards['analysis'].append("😐 **Neutral**: Wait.")
    else: score_cards['analysis'].append("⚠️ **Sell**: Broken Structure.")
    
    return score_cards


# ---------------------------------------------------------
# PAGES: Single Stock & Glossary
# ---------------------------------------------------------


def page_single_coin():
    st.title(get_text('deep_dive_title'))
    all_tickers = get_crypto_universe('All (Top 200)')
    # Ensure BTC-USD is first or default
    if "BTC-USD" in all_tickers:
        all_tickers.remove("BTC-USD")
        all_tickers.insert(0, "BTC-USD")
        
    search_label = f"{get_text('search_ticker')} ({len(all_tickers)} Available)"
    ticker = st.selectbox(search_label, all_tickers, index=0)
    
    if st.button(get_text('analyze_btn')) or ticker:
        with st.spinner(f"Analyzing On-Chain Data for {ticker}..."):
            try:
                # 1. Fetch Deep Data
                stock = yf.Ticker(ticker)
                hist = stock.history(period="max")
                
                if hist.empty:
                    st.error("No data found.")
                    return

                # 2. Calc Metrics
                current_price = hist['Close'].iloc[-1]
                ath = hist['Close'].max()
                drawdown = (current_price - ath) / ath
                # Genesis: 2009-01-03
                # Fix timezone issue
                genesis = pd.Timestamp("2009-01-03").tz_localize(hist.index.tz)
                days_since_genesis = (hist.index[-1] - genesis).days
                
                # Metrics
                narrative = classify_narrative(ticker)
                mvrv_z = calculate_mvrv_z_proxy(hist['Close']).iloc[-1] if len(hist) > 200 else 0
                rsi = calculate_rsi(hist['Close']).iloc[-1] if len(hist) > 14 else 50
                risk_score = calculate_cycle_risk(current_price, ath)
                
                # --- PRO INTELLIGENCE (Signal Source) ---
                scores = calculate_crypash_score(ticker, hist)
                
                # --- SIGNAL LOGIC (Unified with Expert Score) ---
                signal = "NEUTRAL �"
                if scores['total'] >= 75: 
                    signal = "STRONG BUY �"
                elif scores['total'] >= 55:
                    signal = "ACCUMULATE �"
                elif scores['total'] <= 35:
                    signal = "WEAK / AVOID 🔴"
                    
                # 3. Header
                st.markdown(f"## {ticker} {narrative}")
                
                # Signal Banner (Unified)
                if "BUY" in signal or "ACCUMULATE" in signal: 
                    st.success(f"### RECOMMENDATION: {signal} (Score: {scores['total']})")
                elif "WEAK" in signal: 
                    st.error(f"### RECOMMENDATION: {signal} (Score: {scores['total']})")
                else: 
                    st.warning(f"### RECOMMENDATION: {signal} (Score: {scores['total']})")

                c1, c2, c3, c4 = st.columns(4)
                c1.metric("Price", f"${current_price:,.2f}", f"{(current_price/hist['Close'].iloc[-2]-1)*100:.2f}%")
                c2.metric("ATH (Cycle High)", f"${ath:,.2f}", f"{drawdown*100:.1f}% From Top")
                c3.metric("MVRV Z-Score", f"{mvrv_z:.2f}", "Overvalued" if mvrv_z > 3 else "Undervalued")
                c4.metric("Cycle Risk Gauge", f"{risk_score*100:.0f}/100", "Extreme Risk" if risk_score > 0.8 else "Safe Zone")

                # --- PRO SCORECARD (Expert Intelligence) ---
                st.markdown("---")
                st.subheader("🏆 Crypash Pro Score (Expert Intelligence)")
                
                scores = calculate_crypash_score(ticker, hist)
                
                sc_main, sc_val, sc_mom, sc_risk, sc_sent = st.columns([1.5, 1, 1, 1, 1])
                
                # Dynamic Logic for Colorizing
                total_color = "normal"
                if scores['total'] >= 80: total_color = "off" # Use delta color
                
                with sc_main:
                    st.metric("Total Score", f"{scores['total']}/100", 
                             "Strong Buy" if scores['total']>=75 else "Neutral" if scores['total']>=40 else "Sell")
                    st.progress(scores['total'])
                    for ana in scores['analysis']:
                        st.caption(ana)

                with sc_val:
                    st.caption("🦄 On-Chain")
                    st.metric("Valuation", f"{scores['value']}", label_visibility="collapsed")
                    st.progress(scores['value'])
                    with st.expander("Details"):
                        for d in scores['details'].get('value', []): st.caption(d)

                with sc_mom:
                    st.caption("🚀 Momentum")
                    st.metric("Momentum", f"{scores['momentum']}", label_visibility="collapsed")
                    st.progress(scores['momentum'])
                    with st.expander("Details"):
                        for d in scores['details'].get('momentum', []): st.caption(d)

                with sc_risk:
                    st.caption("🛡️ Risk/Health")
                    st.metric("Health", f"{scores['health']}", label_visibility="collapsed")
                    st.progress(scores['health'])
                    with st.expander("Details"):
                        for d in scores['details'].get('health', []): st.caption(d)
                    
                with sc_sent:
                    st.caption("🧠 Sentiment")
                    sent_val = scores.get('sentiment', 'N/A')
                    if sent_val == 0: sent_str = "N/A"
                    else: sent_str = str(sent_val)
                    
                    st.metric("Sentiment", sent_str, label_visibility="collapsed")
                    st.progress(sent_val if sent_val != "N/A" else 0)
                    with st.expander("Details"):
                        for d in scores['details'].get('sentiment', []): st.caption(d)
                
                st.markdown("---")
                st.divider()

                # 4. Power Law / Fair Value Card (Only for BTC for now)
                if "BTC" in ticker.upper():
                    st.subheader("⚡ Bitcoin Power Law Support")
                    fair_val = calculate_power_law_btc(days_since_genesis)
                    
                    c_pl1, c_pl2 = st.columns([2, 1])
                    with c_pl1:
                         st.info("The Power Law models Bitcoin's growth as a function of time. It has held support for 15 years.")
                         # Simple Plot
                         st.line_chart(hist['Close'].tail(1000))
                    
                    with c_pl2:
                         dev_pct = (current_price/fair_val-1)*100
                         # Percentile Logic (Approx)
                         rank_pct = 50 + (dev_pct / 2) # e.g. +100% dev -> 100th, -50% -> 25th
                         rank_pct = max(1, min(99, rank_pct))
                         
                         st.metric("Power Law Support (Floor)", f"${fair_val:,.0f}", f"Deviation: {dev_pct:.1f}%")
                         st.progress(int(rank_pct))
                         st.caption(f"Percentile Rank: {rank_pct:.0f}% (Historical High)")
                         
                         if current_price < fair_val:
                             st.success("PRICE BELOW POWER LAW! HISTORIC BUY ZONE.")
                         elif dev_pct < 20:
                             st.success("ACCUMULATION ZONE (Near Support)")
                         else:
                             st.warning("Price above Power Law Support. Normal Bull Market behavior.")
                
                else:
                    # Altcoin Cycle Multiplier
                    st.subheader("🌊 Altcoin Cycle Multiplier")
                    st.info(f"Altcoins follow Bitcoin but with higher beta. {ticker} is currently {drawdown*100:.1f}% from its All-Time High.")

                # 5. Charts
                st.subheader("📈 On-Chain Strength (RSI)")
                st.line_chart(hist['Close'].tail(365))

            except Exception as e:
                import traceback
                st.error(f"Analysis Failed: {e}")
                st.code(traceback.format_exc())



# ---------------------------------------------------------
# PAGES: Glossary (Crypto)
# ---------------------------------------------------------

def page_glossary():
    st.title("📚 Crypto Glossary")
    st.info("Learn the key metrics used in Crypash.")
    
    metrics = {
        "MVRV Z-Score": "Market Value to Realized Value. Measures if price is 'overheated' vs the average cost basis of all holders. > 3.0 is Selling Zone, < 0 is Accumulation.",
        "RSI (Relative Strength)": "Momentum indicator. > 70 is Overbought, < 30 is Oversold.",
        "Power Law": "Bitcoin's long-term logarithmic growth trend. Acts as a 'fair value' floor over decades.",
        "Cycle Risk Gauge": "Measures how close we are to the All-Time High. Near ATH = High Cycle Risk.",
        "Realized Price": "The average price at which every Bitcoin last moved. It's the 'Cost Basis' of the network."
    }
    
    for k, v in metrics.items():
        with st.expander(f"📘 {k}"):
            st.write(v)

        









def page_howto():
    st.title("📖 How to Use / คู่มือการใช้งาน")
    lang = st.session_state.get('lang', 'EN')
    
    HOWTO_DATA = {
        'Intro': {
            'EN': """
            **Hello Crypash!(Beta)**  
            This tool uses **Cycle Theory** and **On-Chain Data** to find high-probability setups.  
            Unlike stock scanners that look at P/E, we look at **Market Psychology** and **Blockchain Activity**.
            """,
            'TH': """
            **Hello Crypash!(Beta)**  
            เครื่องมือนี้ไม่ได้ดูแค่กราฟ แต่ใช้ **ทฤษฎีวัฏจักร (Cycle Theory)** และ **ข้อมูล On-Chain** เพื่อหาจุดเข้าซื้อที่เจ้ามือซ่อนไม่ได้
            """
        },
        'Step1': {
            'EN': {
                'title': "1. The Metrics (Expert Explanations)",
                'desc': """
                ### 🐋 MVRV Z-Score (The "Fair Value" Gauge)
                - **What it is**: Ratio of Market Cap (Price) vs Realized Cap (Cost Basis of all coins).
                - **Guru Says**: *"When Z-Score < 0, it means the market is valued LESS than what people paid for it. This is the Buy Zone."* - Glassnode
                - **Strategy**: Buy when < 0 (Green), Sell when > 3.5 (Red).

                ### ⚡ RSI (Momentum)
                - **What it is**: Speed of price changes.
                - **Guru Says**: *"RSI > 70 is overheated. RSI < 30 is oversold."* - Technical Analysis 101
                
                ### 🌈 Power Law (BTC Only)
                - **What it is**: Mathematical model showing Bitcoin's floor price growing over time.
                - **Guru Says**: *"Bitcoin has never broken its Power Law support for 15 years. It's the ultimate floor."* - PlanB / Giovanni
                """
            },
            'TH': {
                'title': "1. ทำความรู้จักค่าต่างๆ (ฉบับเซียน)",
                'desc': """
                ### 🐋 MVRV Z-Score (ดัชนีวัดความถูกแพง)
                - **คืออะไร**: เทียบ "ราคาตลาด" กับ "ต้นทุนเฉลี่ยของคนทั้งตลาด" (Realized Price)
                - **เซียนบอกว่า**: *"ถ้าค่าต่ำกว่า 0 แปลว่าตอนนี้ **ของถูกกว่าต้นทุนเจ้ามือ** (Deep Value) เป็นจุดซื้อที่ปลอดภัยที่สุดในรอบวัฏจักร"*
                - **การใช้**: โซนสีเขียว (< 0) คือสะสม, โซนสีแดง (> 3.5) คือฟองสบู่แตก

                ### ⚡ RSI (โมเมนตัม)
                - **คืออะไร**: แรงส่งของราคา
                - **เซียนบอกว่า**: *"ถ้าเกิน 70 คือ **ไล่ราคา** (ระวังดอย), ถ้าต่ำกว่า 30 คือ **ขายทิ้ง** (จุดเด้งสั้นๆ)"*
                
                ### 🌈 Bitcoin Power Law (กฎแห่งพลัง)
                - **คืออะไร**: เส้นแนวรับตามธรรมชาติของ Bitcoin ที่ไม่เคยหลุดมา 15 ปี
                - **เซียนบอกว่า**: *"ถ้าซื้อมือ Bitcoin ต่ำกว่าเส้น Power Law คุณแทบจะไม่มีทางขาดทุนในระยะยาว"*
                """
            }
        },
        'Step2': {
            'EN': {
                'title': "2. How to Scan",
                'desc': """
                1. **Select Universe**: Choose 'All (Top 200)' for broad search or 'Layer 1' for specific sectors.
                2. **Config Limits**: Use 200 for full market scan.
                3. **Active Filters**:
                   - Use **MVRV_Z** to find undervalued gems.
                   - Use **Vol_30D** to avoid dead coins (need some volatility).
                """
            },
            'TH': {
                'title': "2. วิธีสแกนหาเหรียญต้นรอบ",
                'desc': """
                1. **เลือก Universe**: แนะนำ **'All (Top 200)'** เพื่อกวาดดูทั้งตลาด
                2. **Active Filters (ตัวกรอง)**:
                   - ติ๊ก **MVRV_Z** ถ้าอยากหาเหรียญที่ **ถูกจัดๆ (Undervalued)**
                   - ติ๊ก **RSI** ถ้าอยากหาเหรียญที่ **กำลังซิ่ง (Momentum)**
                3. **กด Execute**: รอระบบดึงข้อมูล On-Chain
                """
            }
        },
        'Step3': {
            'EN': {
                'title': "3. Deep Dive",
                'desc': """
                Click **Single Coin Analysis** to see the **Cycle Risk Gauge**.
                - **Safe Zone**: 0-30% Risk (Good for Long Term).
                - **Danger Zone**: 80-100% Risk (Take Profit).
                """
            },
            'TH': {
                'title': "3. เจาะลึกรายตัว (Deep Dive)",
                'desc': """
                ไปที่หน้า **Single Coin Analysis** พิมพ์ชื่อเหรียญ
                - ดู **Cycle Risk Gauge**: เข็มวัดความเสี่ยง
                   - **โซนปลอดภัย**: 0-30% (เหมาะสะสมยาว)
                   - **โซนอันตราย**: 80-100% (ควรขายทำกำไร)
                """
            }
        },
        'Step4': {
            'EN': {
                'title': "4. Expert Criteria Thresholds",
                'desc': """
                | **Category** | **Metric** | **Buy Zone (Safe)** | **Sell Zone (Risk)** | **Interpretation** |
                | :--- | :--- | :--- | :--- | :--- |
                | **🦄 On-Chain** | **MVRV Z-Score** | < 0.0 | > 3.5 | < -1.5 is historic bottom. > 7 is cycle top. |
                | | **Exchange Netflow** | Outflow (Negative) | Inflow (Positive) | Coins leaving exchanges = Accumulation. |
                | **🚀 Momentum** | **RSI (14D)** | < 30 (Oversold) | > 70 (Overbought) | RSI < 30 + Price Support = Strong Entry. |
                | | **MACD** | Bullish Cross | Bearish Cross | MACD > Signal is trend confirmation. |
                | **🛡️ Risk** | **Volatility (30D)** | < 60% | > 120% | High Volatility is normal for small caps, dangerous for large caps. |
                | | **Drawdown** | -80% to -90% | < -20% (Near ATH) | Deep drawdown offers high R:R but requires patience. |
                | **🧠 Sentiment** | **Volume Trend** | Rising + Flat Price | Spiking + High Price | Volume implies interest. Smart money buys quietly. |
                """
            },
            'TH': {
                'title': "4. เจาะลึกเกณฑ์การให้คะแนน (Criteria Thresholds)",
                'desc': """
                | **หมวดหมู่** | **ตัวชี้วัด (Metric)** | **โซนซื้อ (ปลอดภัย)** | **โซนขาย (เสี่ยง)** | **คำอธิบาย** |
                | :--- | :--- | :--- | :--- | :--- |
                | **🦄 On-Chain** | **MVRV Z-Score** | < 0.0 | > 3.5 | < -1.5 คือก้นเหวประวัติศาสตร์ / > 7 คือดอย |
                | | **Netflow** | ไหลออก (Outflow) | ไหลเข้า (Inflow) | ไหลออก = วาฬเก็บของเข้า Wallet |
                | **🚀 Momentum** | **RSI** | < 30 (ขายมากเกิน) | > 70 (ซื้อมากเกิน) | RSI ต่ำกว่า 30 มักจะมีแรงเด้งสั้นๆ |
                | **🛡️ Risk** | **Volatility** | < 60% | > 120% | ผันผวนต่ำ = ปลอดภัย / ผันผวนสูง = เสี่ยง |
                | **🧠 Sentiment** | **Volume** | วอลุ่มเข้า + ราคานิ่ง | วอลุ่มพีค + ราคาพุ่ง | วอลุ่มเข้าตอนราคานิ่ง คือเจ้าเก็บของ |
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
    
    st.header(HOWTO_DATA['Step4'][lang]['title'])
    st.write(HOWTO_DATA['Step4'][lang]['desc'])

# ---------------------------------------------------------
if __name__ == "__main__":
    inject_custom_css() # Apply Professional Styles
    
    # --- PRE-CALCULATE LANGUAGE STATE ---
    # We must determine language BEFORE rendering tabs, otherwise they lag one step behind.
    # Check if widget was interacted with (it's in session state as 'lang_choice_key')
    if 'lang_choice_key' in st.session_state:
        # Update immediately based on widget value
        pass # Widget triggers rerun, so we read it below or use key
        
    # Hack: Render the radio button logic-first but UI-later? No, can't move UI easily.
    # Better: Use key to read state at top.
    
    current_lang_sel = st.session_state.get('lang_choice_key', "English (EN)")
    st.session_state['lang'] = 'EN' if "English" in current_lang_sel else 'TH'

    # --- BRANDING (Explicit Fallback) ---
    # We create a top header row to force the logo visibility
    c_brand_a, c_brand_b = st.columns([1, 20]) # Adjusted for Semi-Wide 
    with c_brand_a:
         st.image("logo.png", width=45) # Visible Logo
    
    with c_brand_b: 
         # --- TOP TABS NAVIGATION (CFA Style) ---
         # Define Tabs (Rendered at the very top)
         tab_scan, tab_single, tab_gloss, tab_howto = st.tabs([
            get_text('nav_scanner'), 
            get_text('nav_single'), 
            get_text('nav_glossary'),
            get_text('nav_help')
         ])

    c_logo, c_lang = st.columns([8, 2])
    with c_logo:
        st.caption(get_text('footer_caption'))
        
    with c_lang:
        # Move Language Switcher to Top Right
        # KEY is vital for pre-calculation
        lang_choice = st.radio(get_text('lang_label'), ["English (EN)", "Thai (TH)"], horizontal=True, label_visibility="collapsed", key="lang_choice_key")
        # No need to manually set session_state['lang'] here, we did it at top.
    
    with tab_scan:
        page_scanner()
        
    with tab_single:
        page_single_coin()
        
    with tab_gloss:
        page_glossary()

    with tab_howto:
        page_howto()
