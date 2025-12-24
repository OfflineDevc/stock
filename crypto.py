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
def fetch_cached_financials(ticker):
    """Cache the financials fetch."""
    try:
        return yf.Ticker(ticker).financials
    except: return pd.DataFrame()


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
        'execute_btn': "🚀 Execute Crypash Scan",
        'main_title': "Crypash",
        'scan_limit': "Scan Limit",
        'results_header': "🏆 Top Coins (Cycle & On-Chain Analysis)",
        'stage1_msg': "📡 Stage 1: Fetching Universe...",
        'stage2_msg': "✅ Stage 1 Complete. Analyzing Top Candidates...",
        'no_data': "❌ No stocks matched your STRICT criteria.",
        'deep_dive_title': "🔍Deep Dive Kub",
        'glossary_title': "📚 Investment Glossary",
        'search_ticker': "Enter Stock Ticker (e.g. AAPL, PTT.BK)",
        'analyze_btn': "Analyze Stock",
        'about_title': "ℹ️ About This Project",
        'about_desc': "This program was created by Mr. Kun Poonkasetvatana. It was developed to solve the pain point that finding data is difficult, analyzing every stock takes too long, and similar tools are unreasonably expensive. Fetches data from Yahoo Finance to screen quickly. Currently developing AI to analyze fundamentals further, obeying 'Invest on what you know' and regular portfolio health checks.",
        
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
        'menu_ai': "Crypto AI Analysis",
        'under_dev': "🚧 Feature Under Development 🚧",
        'dev_soon': "Check back soon for AI-powered diagnostics!",
        'dev_dl': "Coming soon: Deep Learning On-Chain Analysis.",
        'biz_summary': "📝 **Project Summary**",
        'lynch_type': "Lynch Type",
        'score_garp': "GARP Score",
        'score_value': "Deep Value Score",
        'score_div': "Dividend Score",
        'score_multi': "🚀 Multibagger Score",

        # --- NEW DASHBOARD & UI ---
        'market_sentiment_title': "### 🧭 Market Sentiment (CNN-Style Proxy)",
        'fear_greed_title': "Fear & Greed Index (Proxy)",
        'vix_caption': "Driven by VIX: {vix:.2f} (Lower VIX = Higher Greed)",
        'state_extreme_fear': "🥶 Extreme Fear",
        'state_fear': "😨 Fear",
        'state_neutral': "😐 Neutral",
        'state_greed': "😎 Greed",
        'state_extreme_greed': "🤑 Extreme Greed",
        'buffett_title': "Buffett Indicator (Q3 2025)",
        'buffett_caption': "Ratio of Total US Stock Market ($70.68T) to GDP ($30.77T).",
        'buffett_status': "Status: 2.4 Std Dev above historical average.",
        'buffett_val_desc': "Strongly Overvalued",
        'faq_title': "📚 Definition & Methodology (FAQs)",
        'max_pe': "Max P/E Ratio",
        'max_peg': "Max PEG Ratio",
        'max_evebitda': "Max EV/EBITDA",
        'min_roe': "Min ROE %",
        'min_margin': "Min Op Margin %",
        'min_div': "Min Dividend Yield %",
        'min_rev_growth': "Min Revenue Growth %",
        'max_de': "Max Debt/Equity %",
        'debug_logs': "🛠️ Debug Logs (Open if No Data)",
        'port_title': "Portfoliokub",
        'ai_analysis_header': "🧠 AI Analysis Result ({risk})",
        'gen_success': "✅ Generated Professional Portfolio: {n} Stocks",
        'avg_pe_label': "Avg P/E (Equity)",
        'equity_yield_label': "Equity Yield",
        'quality_roe_label': "Quality (ROE)",
        
        # Tooltips
        'lynch_tooltip': "",
        'lynch_desc': "Peter Lynch Categories:\n- Fast Grower: Earnings >20%\n- Asset Play: Asset Rich (P/B < 1)\n- Turnaround: Recovering\n- Cyclical: Economy tied\n- Slow Grower: Dividend payers",
        'sector_tooltip': "",
        'sector_desc': "Industry Group (e.g. Tech, Energy). Important for relative valuation.",
        'backtest_title': "🕑 Historical Backtest & Simulation",
        'backtest_desc': "See how this portfolio would have performed in the past vs S&P 500.",
        'backtest_config': "⚙️ Backtest Configuration",
        'invest_mode': "Investment Mode",
        'time_period': "Time Period",
        'invest_amount': "Investment Amount",
        'run_backtest_btn': "🚀 Run Backtest",
        'historical_chart_title': "### 🔬 Interactive Historical Charts",
        'select_stock_view': "Select Stock to View:",
        'nav_scanner': "Market Scanner",
        'nav_portfolio': "Auto Portfolio",
        'nav_single': "Single Stock Analysis",
        'nav_health': "Portfolio Health",
        'nav_ai': "AI Insight",
        'nav_glossary': "Glossary",
        'nav_help': "How to Use",
        'footer_caption': "Professional Stock Analytics Platform",
        'health_check_title': "🔍 Financial Health Check",
        'val_label': "Valuation",
        'qual_label': "Quality",
        'guru_intel_title': "🧠 Guru & Analyst Intel",
        'tab_holders': "🏛️ Institutional Holders (Guru Proxy)",
        'tab_recs': "🗣️ Analyst Recommendations",
        'holders_desc': "Top funds and institutions holding this stock.",
        'no_holders': "No institutional holding data available.",
        'err_holders': "Could not fetch institutional data.",
        'consensus_target': "Consensus Target Price",
        'vs_current': "vs Current",
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
        'bucket_equity': "Equities (Stock)",
        'bucket_long_bonds': "Long Bonds",
        'bucket_interm_bonds': "Interm Bonds",
        'bucket_gold': "Gold",
        'bucket_commodity': "Commodities",
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
        
        # Tooltips
        'lynch_tooltip': "ℹ️",
        'lynch_desc': "ประเภทหุ้นตาม Peter Lynch:\n- Fast Grower: โตเร็ว (กำไร >20%)\n- Asset Play: หุ้นสินทรัพย์เยอะ (P/B < 1)\n- Turnaround: หุ้นพลิกฟื้น\n- Cyclical: หุ้นวัฏจักร\n- Slow Grower: หุ้นปันผล",
        'sector_tooltip': "ℹ️",
        'sector_desc': "กลุ่มอุตสาหกรรม (เช่น เทคโนโลยี, พลังงาน) ช่วยให้เปรียบเทียบ P/E ได้ถูกต้อง",
        
        'execute_btn': "🚀 เริ่มสแกนเหรียญ (On-Chain Analysis)",
        'main_title': "Crypash",
        'scan_limit': "จำกัดจำนวนสแกน", 
        'results_header': "🏆 หุ้นเด่น (วิเคราะห์เจาะลึก)",
        'stage1_msg': "📡 ขั้นแรก: ดึงข้อมูลหุ้น...",
        'stage2_msg': "✅ ขั้นแรกเสร็จสิ้น กำลังวิเคราะห์เจาะลึก...",
        'no_data': "❌ ไม่พบหุ้นที่ผ่านเกณฑ์ Strict ของคุณ",
        'deep_dive_title': "ดีบไดป์คับ",
        'glossary_title': "📚 คลังความรู้การลงทุน",
        'search_ticker': "พิมพ์ชื่อหุ้น (เช่น AAPL, PTT.BK)",
        'analyze_btn': "วิเคราะห์หุ้นนี้",
        'about_title': "ℹ️ เกี่ยวกับโปรเจกต์นี้",
        'about_desc': "โปรแกรม Crypash แฝดพี่ของ Stockub พัฒนาเพื่อชาวดอยคริปโตโดยเฉพาะ เน้นวิเคราะห์วัฏจักร (Cycle), เงินไหลเข้าออก (Fund Flow), และความโลภของตลาด (Sentiment) เพื่อหาจุดซื้อที่ปลอดภัยที่สุด ไม่ใช่แค่ดูเส้นกราฟ แต่ดู 'ข้อมูลบนเชน' (On-Chain) ที่เจ้ามือซ่อนไม่ได้",
        
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

        # --- NEW DASHBOARD & UI ---
        'market_sentiment_title': "### 🧭 สภาวะตลาด (Market Sentiment)",
        'fear_greed_title': "ดัชนี Fear & Greed (Proxy)",
        'vix_caption': "คำนวณจาก VIX: {vix:.2f} (ยิ่ง VIX ต่ำ = ตลาดพึงพอใจ/โลภ)",
        'state_extreme_fear': "🥶 กลัวสุดขีด (Extreme Fear)",
        'state_fear': "😨 กลัว (Fear)",
        'state_neutral': "😐 ปกติ (Neutral)",
        'state_greed': "😎 โลภ (Greed)",
        'state_extreme_greed': "🤑 โลภสุดขีด (Extreme Greed)",
        'buffett_title': "ดัชนีบัฟเฟตต์ (Buffett Indicator - Q3 2025)",
        'buffett_caption': "สัดส่วนมูลค่าตลาดหุ้น US ($70.68T) ต่อ GDP ($30.77T)",
        'buffett_status': "สถานะ: สูงกว่าค่าเฉลี่ย 2.4 Standard Deviation",
        'buffett_val_desc': "แพงมาก (Strongly Overvalued)",
        'faq_title': "📚 คำนิยามและระเบียบวิธี (FAQs)",
        'max_pe': "ค่า P/E สูงสุดที่ยอมรับได้",
        'max_peg': "ค่า PEG สูงสุดที่ยอมรับได้",
        'max_evebitda': "ค่า EV/EBITDA สูงสุด",
        'min_roe': "ค่า ROE ขั้นต่ำ %",
        'min_margin': "กำไรจากการดำเนินงานขั้นต่ำ %",
        'min_div': "อัตราปันผลขั้นต่ำ %",
        'min_rev_growth': "การเติบโตรายได้ขั้นต่ำ %",
        'max_de': "หนี้สินต่อทุนสูงสุด (D/E) %",
        'debug_logs': "🛠️ บันทึกการตรวจสอบ (Debug Logs)",
        'port_title': "พอร์ตฟอลิโอคับ",
        'ai_analysis_header': "🧠 ผลการวิเคราะห์ด้วย AI ({risk})",
        'gen_success': "✅ สร้างพอร์ตการลงทุนสำเร็จ: {n} หุ้น",
        'avg_pe_label': "P/E เฉลี่ย (เฉพาะหุ้น)",
        'equity_yield_label': "ปันผลเฉลี่ย",
        'quality_roe_label': "คุณภาพ (ROE เฉลี่ย)",
        'backtest_title': "🕑 การทดสอบย้อนหลัง (Historical Backtest)",
        'backtest_desc': "ดูผลตอบแทนในอดีตของพอร์ตนี้เปรียบเทียบกับดัชนี S&P 500",
        'backtest_config': "⚙️ ตั้งค่าการทดสอบย้อนหลัง",
        'invest_mode': "รูปแบบการลงทุน",
        'time_period': "ช่วงเวลา",
        'invest_amount': "จำนวนเงินลงทุน",
        'run_backtest_btn': "🚀 เริ่มทดสอบย้อนหลัง",
        'historical_chart_title': "### 🔬 กราฟราคาย้อนหลัง",
        'select_stock_view': "เลือกหุ้นเพื่อดูรายละเอียด:",
        'nav_scanner': "สแกนหุ้นดาวเด่น",
        'nav_portfolio': "พอร์ตอัตโนมัติ",
        'nav_single': "วิเคราะห์รายตัว",
        'nav_health': "สุขภาพพอร์ต",
        'nav_ai': "วิเคราะห์ AI",
        'nav_glossary': "คลังคำศัพท์",
        'nav_help': "วิธีใช้งาน",
        'footer_caption': "แพลตฟอร์มวิเคราะห์หุ้นระดับมืออาชีพ",
        'health_check_title': "🔍 ตรวจสุขภาพทางการเงิน",
        'val_label': "ความถูกแพง (Valuation)",
        'qual_label': "คุณภาพธุรกิจ (Quality)",
        'guru_intel_title': "🧠 ข้อมูลจากเซียนและนักวิเคราะห์",
        'tab_holders': "🏛️ ผู้ถือหุ้นสถาบัน (Guru Proxy)",
        'tab_recs': "🗣️ คำแนะนำจากนักวิเคราะห์",
        'holders_desc': "กองทุนและสถาบันชั้นนำที่ถือหุ้นตัวนี้",
        'no_holders': "ไม่พบข้อมูลการถือหุ้นของสถาบัน",
        'err_holders': "ไม่สามารถดึงข้อมูลผู้ถือหุ้นสถาบันได้",
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
        'tab_lynch': "🧠 ประเภทหุ้นตาม Peter Lynch",
        
        'port_alloc_title': "🌍 สัดส่วนการลงทุน (Allocation)",
        'port_alloc_caption': "แสดงสัดส่วนตามรายตัวและกลุ่มสินทรัพย์",
        'type_alloc_title': "สัดส่วนตามประเภทหุ้น",
        'equity_only': "เฉพาะหุ้น",
        'asset_class_label': "ประเภทสินทรัพย์",
        'sector_label_short': "อุตสาหกรรม",
        'weight_label': "น้ำหนัก %",
        'ticker_label': "ชื่อหุ้น",
        'price_label': "ราคา",
        'score_label': "คะแนน",
        'rev_cagr_label': "โตรายได้",
        'ni_cagr_label': "โตกำไร",
        'yield_label': "ปันผล",
        'why_mcap_title': "**ทำไมต้องจัดน้ำหนักตามมูลค่าตลาด (Market Cap Weighting)?**",
        'why_mcap_desc': "- **มาตรฐานสากล**: ดัชนีหลักอย่าง S&P 500 และ Nasdaq 100 ใช้ระบบนี้\n- **ความมั่นคง**: ให้เงินทำงานในบริษัทที่ใหญ่และมั่นคงกว่าในสัดส่วนที่สูงกว่า\n- **ปรับตัวอัตโนมัติ**: เมื่อบริษัทเติบโตขึ้น สัดส่วนในพอร์ตก็จะเพิ่มขึ้นเองตามธรรมชาติ",
        'how_works_title': "**หลักการทำงานของระบบ:**",
        'how_works_desc': "1. เราคัดเลือกหุ้น 20 อันดับแรกที่ได้คะแนน **Strategy Score** สูงสุด\n2. จัดสรรเงินลงทุนตาม **ขนาดของบริษัท (Market Cap)**",
        'bucket_equity': "หุ้นสามัญ (Equities)",
        'bucket_long_bonds': "พันธบัตรระยะยาว",
        'bucket_interm_bonds': "พันธบัตรระยะกลาง",
        'bucket_gold': "ทองคำ",
        'bucket_commodity': "สินค้าโภคภัณฑ์",
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
        tab_fg, tab_buff = st.tabs([get_text('fear_greed_title'), get_text('buffett_title')])
        
        with tab_fg:
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
            
        with tab_buff:
            st.markdown("""
            **What is the Buffett Indicator?**  
            The ratio of the total United States stock market valuation to GDP. Warren Buffett called it *"probably the best single measure of where valuations stand at any given moment."*

            $$ \\text{Buffett Indicator} = \\frac{\\text{Total US Stock Market Value}}{\\text{Gross Domestic Product (GDP)}} $$

            **Current Values (As of Sep 30, 2025):**  
            - **Total Market**: $70.68 Trillion  
            - **GDP**: $30.77 Trillion  
            - **Ratio**: **230%** (Strongly Overvalued)

            **Interpretation:**  
            - **75-90%**: Fair Valued  
            - **> 120%**: Overvalued  
            - **> 200%**: Bubble / Strongly Overvalued 🚨
            """)



# ---------------------------------------------------------
# 1. Page Configuration
# ---------------------------------------------------------
st.set_page_config(
    page_title="Crypash - Crypto AI Analysis",
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
        'XTZ-USD', 'KCS-USD', 'CHZ-USD', 'GALA-USD', 'KLAY-USD', 'RUNE-USD', 'CRV-USD'
    ]

    # 2. Layer 1s
    l1 = [
        'BTC-USD', 'ETH-USD', 'SOL-USD', 'ADA-USD', 'AVAX-USD', 'TRX-USD', 'DOT-USD', 
        'ATOM-USD', 'NEAR-USD', 'ALGO-USD', 'FTM-USD', 'SUI-USD', 'SEI-USD'
    ]

    # 3. DeFi
    defi = [
        'UNI-USD', 'LINK-USD', 'LDO-USD', 'MKR-USD', 'AAVE-USD', 'CRV-USD', 'SNX-USD', 
        'COMP-USD', '1INCH-USD', 'SUSHI-USD', 'RPL-USD', 'DYDX-USD', 'GMX-USD'
    ]

    # 4. Meme
    meme = [
        'DOGE-USD', 'SHIB-USD', 'PEPE-USD', 'FLOKI-USD', 'BONK-USD', 'WIF-USD', 'MEME-USD'
    ]

    # 5. AI & Big Data
    ai_coins = [
        'RNDR-USD', 'FET-USD', 'AGIX-USD', 'OCEAN-USD', 'AKT-USD', 'TAO-USD'
    ]

    if category == 'Layer 1': return l1
    if category == 'DeFi': return defi
    if category == 'Meme': return meme
    if category == 'AI & Big Data': return ai_coins
    
    # Default to Top 50
    return top_50


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
            
            narrative = classify_narrative(ticker)
            
            # 5. Price Change
            price = closes.iloc[-1]
            chg_7d = (price - closes.iloc[-8]) / closes.iloc[-8] * 100 if len(closes) > 7 else 0
            chg_30d = (price - closes.iloc[-31]) / closes.iloc[-31] * 100 if len(closes) > 31 else 0
            
            data_list.append({
                'Symbol': ticker,
                'Narrative': narrative,
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
            fin = stock.financials
            if not fin.empty:
                fin = fin.T.sort_index()
                
                years = len(fin)

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
                    if start_rev > 0 and end_rev > 0:
                        val = (end_rev / start_rev) ** (1/(years-1)) - 1
                        cagr_rev = val * 100
                except: pass
                
                try:
                    start_ni = fin['Net Income'].iloc[0]
                    end_ni = fin['Net Income'].iloc[-1]
                    if start_ni > 0 and end_ni > 0:
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

def calculate_crypto_score(row):
    """
    Scoring based on Cycle Position & Momentum (0-100).
    Higher Score = Better 'Buy' Zone (contrarian) or Strong Momentum depending on strat.
    Let's build a 'Cycle Score': High Score = Undervalued (Safety).
    """
    score = 50
    
    # MVRV Logic: Lower is better for Buying
    z = row.get('MVRV_Z', 0)
    if z < 0: score += 30 # Buy Zone
    elif z < 1: score += 10
    elif z > 3: score -= 30 # Sell Zone
    elif z > 2: score -= 10
    
    # RSI Logic: Lower is better for Buying Dip
    rsi = row.get('RSI', 50)
    if rsi < 30: score += 20
    elif rsi > 70: score -= 20
    
    # Volatility Check (Penalty if too high for conservative inv)
    # But in crypto, Vol is normal. 
    
    return max(0, min(100, score))

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
             st.subheader("1. Crypto Universe")
             market_choice = st.selectbox("Select Category", ["Top 50", "Layer 1", "DeFi", "Meme", "AI & Big Data"])
             num_stocks = st.slider(get_text('scan_limit'), 10, 100, 50)
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
            tickers = get_crypto_universe(market_choice)
            tickers = tickers[:num_stocks]
        
        st.info(f"Stage 1: Scanning {len(tickers)} stocks...")
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
        
        st.markdown(f"### {get_text('results_header')}")
        
        # Color Styling for Cycle State
        def color_cycle(val):
            if "Accumulation" in val: return "background-color: #d4edda; color: #155724; font-weight: bold"
            if "Euphoria" in val: return "background-color: #f8d7da; color: #721c24; font-weight: bold"
            if "Greed" in val: return "background-color: #fff3cd; color: #856404"
            return ""

        # Columns to display
        display_cols = ['Symbol', 'Narrative', 'Price', 'Cycle_State', 'MVRV_Z', 'RSI', 'Vol_30D', '7D', '30D']
        
        st.dataframe(
            df[display_cols].style.applymap(color_cycle, subset=['Cycle_State'])
            .format({
                'Price': '${:,.2f}',
                'MVRV_Z': '{:.2f}',
                'RSI': '{:.1f}',
                'Vol_30D': '{:.1f}%',
                '7D': '{:+.1f}%',
                '30D': '{:+.1f}%'
            }),
            column_config={
                "MVRV_Z": st.column_config.NumberColumn("On-Chain Z-Score", help="< 0 is Buy, > 3 is Sell"),
                "RSI": st.column_config.ProgressColumn("Momentum (RSI)", min_value=0, max_value=100, format="%.0f"),
                "Cycle_State": "Cycle Evaluation"
            },
            hide_index=True,
            width=None # Full width
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

        # Cache Clearing for Debugging
        if st.checkbox("Show Advanced Options"):
            if st.button("🗑️ Clear Data Cache"):
                st.cache_data.clear()
                st.success("Cache Cleared! Rerun the scan.")

        else:
            st.error(get_text('no_data'))
            st.session_state['scan_results'] = None
            st.session_state['deep_results'] = None

    else:
        st.info("Define parameters and start the Two-Stage Screening.")


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

# ---------------------------------------------------------
# PAGES: Single Stock & Glossary
# ---------------------------------------------------------


def page_single_coin():
    st.title(get_text('deep_dive_title'))
    ticker = st.text_input(get_text('search_ticker'), value="BTC-USD")
    
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
                
                # 3. Header
                st.markdown(f"## {ticker} {narrative}")
                c1, c2, c3, c4 = st.columns(4)
                c1.metric("Price", f"${current_price:,.2f}", f"{(current_price/hist['Close'].iloc[-2]-1)*100:.2f}%")
                c2.metric("ATH (Cycle High)", f"${ath:,.2f}", f"{drawdown*100:.1f}% From Top")
                c3.metric("MVRV Z-Score", f"{mvrv_z:.2f}", "Overvalued" if mvrv_z > 3 else "Undervalued")
                c4.metric("Cycle Risk Gauge", f"{risk_score*100:.0f}/100", "Extreme Risk" if risk_score > 0.8 else "Safe Zone")

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
                         st.metric("Power Law Support (Floor)", f"${fair_val:,.0f}", f"Deviation: {(current_price/fair_val-1)*100:.1f}%")
                         if current_price < fair_val:
                             st.success("PRICE BELOW POWER LAW! HISTORIC BUY ZONE.")
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
         tab_scan, tab_single, tab_gloss = st.tabs([
            get_text('nav_scanner'), 
            get_text('nav_single'), 
            get_text('nav_glossary')
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
