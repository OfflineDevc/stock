import streamlit as st
import yfinance as yf
import altair as alt # Visuals
import pandas as pd
import numpy as np
import time
import requests
import xml.etree.ElementTree as ET

import datetime

from deep_translator import GoogleTranslator
import google.generativeai as genai
import warnings
warnings.filterwarnings("ignore", category=FutureWarning, module="google.generativeai")
import json
import auth_mongo # MongoDB Authentication Module


# --- CONFIGURATION (Must be First) ---
st.set_page_config(
    page_title="StockDeck",
    page_icon="🏛️",
    layout="wide",
    initial_sidebar_state="collapsed"
)


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
        'execute_btn': "🚀 Execute 2-Stage Screen",
        'qscan_title': "Market Scanner",
        'home_title': "Stockdeck",
        'nav_home': "Home", 
        'home_welcome': "Welcome to Stockdeck",
        'home_intro': "Stockdeck is your AI-Powered Investment Analyser, designed to simplify professional-grade stock analysis.",
        'workflow_single': "🔍 **Single Thematic Analysis Workflow**",
        'workflow_single_desc': "For analyzing individual stocks, follow this proven path:",
        'workflow_port': "🏗️ **Portfolio Construction Workflow**",
        'workflow_port_desc': "For building and monitoring a portfolio:",
        'feat_qscan': "**1. Market Scanner (Culling)**: Filter the entire market (S&P 500 / SET 100) to find hidden gems based on Strategy (Value, Growth, Dividend).",
        'feat_qai': "**2. StockDeck AI**: An LLM optimized for detailed fundamental analysis of companies.",
        'feat_qfin': "**3. Deep Dive (Financials)**: Check the raw financial numbers, analyst targets, and institutional holdings manually.",
        'feat_qwealth': "**Portfolio Architect**: Design a personalized portfolio based on your life goals using AI.",
        'feat_qhealth': "**HealthDeck (Doctor)**: Perform a detailed portfolio check-up using AI to analyze risks, compare with Mega Trends, and find hidden weaknesses.",
        'scan_limit': "Scan Limit",
        'results_header': "🏆 Top Picks (Deep Analyzed)",
        'stage1_msg': "📡 Stage 1: Fetching Universe...",
        'stage2_msg': "✅ Stage 1 Complete. Analyzing Top Candidates...",
        'no_data': "❌ No stocks matched your STRICT criteria.",
        'deep_dive_title': "Deep Dive (Finance)",
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
        
        'menu_health': "HealthDeck",
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
        'port_title': "StockDeck Wealth",
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
        'nav_scanner': "Scanner",
        'nav_ai': "StockDeck AI",
        'nav_single': "Deep Dive",
        'nav_portfolio': "StockDeck Wealth",
        'nav_health': "HealthDeck",
        'nav_glossary': "Glossary",
        'footer_caption': "Professional Stock Analytics Platform",
        'health_check_title': "HealthDeck",
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
        
        # --- AIFOLIO KEYS ---
        'aifolio_title': "StockDeck Wealth",
        'ai_form_header': "📝 Investor Profile Interview",
        'f_target': "Target Amount",
        'f_horizon': "Time Horizon (Years)", 
        'f_objective': "Primary Objective",
        'f_capital': "Initial Capital",
        'f_dca': "Monthly Contribution (DCA)",
        'f_risk': "Max Risk Tolerance (Drawdown %)",
        'f_exp': "Investment Experience",
        'f_liquid': "Do you have an Emergency Fund?",
        'f_constraint': "Constraints / Special Preferences",
        'gen_plan_btn': "💡 Generate AI Investment Plan",
        'ai_thinking': "🧠 AI Fund Manager is devising your strategy... (Chain of Thought)",
        'alloc_header': "📊 Recommended Allocation",

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
        
        'execute_btn': "🚀 เริ่มสแกนหุ้น (2 ขั้นตอน)",
        'qscan_title': "Market Scanner (สแกนหุ้น)",
        'home_title': "Stockdeck",
        'nav_home': "หน้าแรก",
        'home_welcome': "ยินดีต้อนรับสู่ Stockdeck",
        'home_intro': "Stockdeck คือผู้ช่วยการลงทุนพลัง AI ที่ออกแบบมาเพื่อยกระดับการวิเคราะห์หุ้นระดับมืออาชีพให้เป็นเรื่องง่าย",
        'workflow_single': "🔍 **ขั้นตอนการวิเคราะห์หุ้นรายตัว**",
        'workflow_single_desc': "เพื่อให้ได้ผลลัพธ์ที่ดีที่สุด แนะนำให้ใช้งานตามลำดับนี้:",
        'workflow_port': "🏗️ **ขั้นตอนการจัดพอร์ต**",
        'workflow_port_desc': "สำหรับผู้ที่ต้องการสร้างพอร์ตการลงทุน:",
        'feat_qscan': "**1. Market Scanner (Culling)**: กรองหุ้นทั้งตลาด (S&P 500 / SET 100) เพื่อหาหุ้นช้างเผือกตามกลยุทธ์ที่คุณชอบ (Value, Growth, Dividend)",
        'feat_qai': "**2. StockDeck AI**: เป็น LLM ที่ผ่านการ optimized สำหรับการวิเคราะห์ข้อมูลเชิงปัจจัยพื้นฐานบริษัทอย่างละเอียด",
        'feat_qfin': "**3. Deep Dive (Financials)**: เจาะดูตัวเลขทางการเงินย้อนหลัง ความเห็นนักวิเคราะห์ และรายชื่อกองทุนที่ถือหุ้นด้วยตาคุณเอง",
        'feat_qwealth': "**StockDeck Wealth**: ออกแบบพอร์ตโฟลิโอส่วนตัวตามเป้าหมายชีวิตของคุณด้วยสมองกล AI",
        'feat_qhealth': "**HealthDeck (Doctor)**: ตรวจสุขภาพพอร์ตโฟลิโอของคุณอย่างละเอียด โดยใช้ AI วิเคราะห์ความเสี่ยงรายตัว เทียบกับ Mega Trend และค้นหาจุดอ่อนที่อาจซ่อนอยู่ในพอร์ตของคุณ",
        'scan_limit': "จำกัดจำนวนสแกน", 
        'results_header': "🏆 หุ้นเด่น (วิเคราะห์เจาะลึก)",
        'stage1_msg': "📡 ขั้นแรก: ดึงข้อมูลหุ้น...",
        'stage2_msg': "✅ ขั้นแรกเสร็จสิ้น กำลังวิเคราะห์เจาะลึก...",
        'no_data': "❌ ไม่พบหุ้นที่ผ่านเกณฑ์ Strict ของคุณ",
        'deep_dive_title': "Deep Dive (Finance)",
        'glossary_title': "📚 คลังความรู้การลงทุน",
        'search_ticker': "พิมพ์ชื่อหุ้น (เช่น AAPL, PTT.BK)",
        'analyze_btn': "วิเคราะห์หุ้นนี้",
        'about_title': "ℹ️ เกี่ยวกับโปรเจกต์นี้",
        'about_desc': "โปรแกรมนี้ ถูกจัดทำโดย นาย กัญจน์ พูนเกษตรวัฒนา โปรเจคนี้ถูกพัฒนาเพื่อการใช้งานส่วนตัวจากการเจอ pain point ที่ว่าการหาข้อมูลมันยุ่งยากมากๆ และ การที่จะนั่งวิเคราะห์หุ้นทุกๆตัวใช้เวลานานเกินไป และ เว็ปที่ทำคล้ายๆแบบนี้ก็เสียเงินแพงเกินใช่เหตุ จึงดึงข้อมูลมาจาก yahoo finance เพื่อคัดหุ้นจากข้อมูลพื้นฐานอย่างรวดเร็ว สิ่งที่กำลังพัฒนาอยู่ตอนนี้คือเรื่องของ ปัญญาประดิษฐ์ที่นำมาวิเคราะห์เรื่องปัจจัยพื้นฐานอีกที และ ทำให้เราเข้าใจสิ่งที่เราจะลงทุนก่อน โดยอิงจาก Invest on what you know และจะมีการตรวจเช็คสภาพรถเสมอ ในหุ้นในพอร์ตฟอลิโอ",
        
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
        
        'menu_health': "HealthDeck",
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
        'port_title': "StockDeck Wealth",
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
        'nav_scanner': "Scanner",
        'nav_ai': "StockDeck AI",
        'nav_single': "Deep Dive",
        'nav_portfolio': "StockDeck Wealth",
        'nav_health': "HealthDeck",
        'nav_glossary': "คลังคำศัพท์",
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

        # --- AIFOLIO KEYS ---
        'aifolio_title': "StockDeck Wealth",
        'ai_form_header': "📝 แบบสอบถามวัดระดับการลงทุน",
        'f_target': "เป้าหมายการเงิน (บาท)",
        'f_horizon': "ระยะเวลาลงทุน (ปี)", 
        'f_objective': "วัตถุประสงค์ (เช่น เกษียณ, ทุนการศึกษา)",
        'f_capital': "เงินตั้งต้น (บาท)",
        'f_dca': "เงินเติมรายเดือน (DCA)",
        'f_risk': "รับการขาดทุนสูงสุดได้กี่ % (Drawdown)",
        'f_exp': "ประสบการณ์การลงทุน",
        'f_liquid': "มีเงินสำรองฉุกเฉินแยกต่างหากแล้ว?",
        'f_constraint': "ข้อจำกัด / สินทรัพย์ที่ชอบหรือห้ามลงทุน",
        'gen_plan_btn': "💡 สร้างแผนการลงทุนด้วย AI",
        'ai_thinking': "🧠 ผู้จัดการกองทุน AI กำลังวิเคราะห์ข้อมูลของคุณ...",
        'alloc_header': "📊 สัดส่วนพอร์ตที่แนะนำ",

    }
}

def get_text(key):
    lang = st.session_state.get('lang', 'EN')
    return TRANS[lang].get(key, key)

# --- MARKET & GURU DATA ---

@st.cache_data(ttl=3600, show_spinner=False)
def fetch_market_indicators():
    """
    Fetches market proxies and calculates CNN-style scores.
    """
    indicators = {}
    try:
        # 1. Fear (VIX) -> Proxy for Fear & Greed Index
        # CNN F&G: 0 (Terror) to 100 (Euphoria)
        # VIX: 10 (Calm) to 80 (Crash)
        # Mapping: VIX 10 -> Score 90, VIX 50 -> Score 10
        vix = yf.Ticker("^VIX")
        vix_info = vix.fast_info
        vix_val = vix_info.last_price
        indicators['VIX'] = vix_val
        
        # Calculate Proxy Score (0-100)
        # Rule of thumb: VIX 12 is Greed, VIX 30 is Fear
        # Linear: Score = 100 - ( (VIX-10)/(35-10) * 100 )
        score = 100 - ((vix_val - 12) / (35 - 12) * 100)
        score = max(0, min(100, score)) # Clamp
        indicators['FG_Score'] = int(score)
        
        # 2. Market Trend (S&P 500)
        spx = yf.Ticker("^GSPC")
        hist = spx.history(period="1y")
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
    
    # --- ROW 1: FEAR & GREED + BUFFETT ---
    c1, c2 = st.columns([1, 1])
    
    with c1:
        score = data.get('FG_Score', 50)
        vix = data.get('VIX', 0)
        
        # Determine State
        if score <= 25: state = get_text('state_extreme_fear')
        elif score <= 45: state = get_text('state_fear')
        elif score <= 55: state = get_text('state_neutral')
        elif score <= 75: state = get_text('state_greed')
        else: state = get_text('state_extreme_greed')
        
        st.metric(get_text('fear_greed_title'), f"{score}/100", state)
        st.progress(score / 100)
        st.caption(get_text('vix_caption').format(vix=vix))

    with c2:
        # Buffett Indicator (Static / Reference)
        # Data from User: Sep 30, 2025 -> 230%
        st.metric(get_text('buffett_title'), "230%", get_text('buffett_val_desc'), delta_color="inverse")
        st.caption(get_text('buffett_caption'))
        st.info(get_text('buffett_status'))

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
    page_title=get_text('StockDeck'),
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

# --- HELPER: RETRY LOGIC (Rate Limits) ---
def retry_api_call(func, retries=3, delay=2):
    """
    Retries a function call if it hits rate limits (429).
    """
    last_exception = None
    for i in range(retries):
        try:
            return func()
        except Exception as e:
            last_exception = e
            error_str = str(e).lower()
            if "429" in error_str or "too many requests" in error_str or "rate limit" in error_str:
                sleep_time = delay * (2 ** i) # Exponential Backoff: 2s, 4s, 8s
                print(f"⚠️ Rate Limit Hit. Retrying in {sleep_time}s...")
                time.sleep(sleep_time)
                continue
            else:
                raise e # Not a rate limit error, raise immediately
    raise last_exception

# --- Stage 1: Fast Scan (Basic Metrics) ---
def scan_market_basic(tickers, progress_bar, status_text, debug_container=None):
    data_list = []
    total = len(tickers)
    
    status_text.text("Stage 1: Analyzing stocks individually (Better Reliability)...")


    total = len(tickers)
    
    for i, ticker in enumerate(tickers):
        # Update UI every 5 items to reduce lag overhead
        # Update UI every 5 items to reduce lag overhead
        if i % 3 == 0: 
            progress = (i + 1) / total
            progress_bar.progress(progress)
        # Rate Limiting Prevention (Aggressive for Cloud)
        time.sleep(0.01) # User Feedback: "Waiting time". We add caching + slight delay to handle rate limits.

        try:
            # Fix: Only replace dot with dash for US tickers
            if ".BK" in ticker: formatted_ticker = ticker
            else: formatted_ticker = ticker.replace('.', '-')
                
            # OPTIMIZATION: Use Cached Info
            info = fetch_cached_info(formatted_ticker)
            
            # Create yf.Ticker object for later use (e.g., financials)
            stock = yf.Ticker(formatted_ticker)

            # DEBUG: Inspect "Info" for problematic tickers
            if (ticker in ['AAPL', 'NVDA', 'GOOGL', 'META', 'TSLA'] or '__error__' in info) and debug_container:
                debug_container.write(f"--- DEBUG: {ticker} ---")
                if '__error__' in info:
                    debug_container.error(f"⚠️ Fetch Error: {info['__error__']}")
                else:
                    debug_container.json(info) # Use JSON for better readability
            
            # DEBUG: Log first item to see what's happening on Cloud
            if i == 0 and debug_container:
                pass # Clean logs
            
            # Price from Bulk or Info
            price = info.get('regularMarketPrice') or info.get('currentPrice')

            
            if price is None:
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
                        inc = fetch_cached_financials(formatted_ticker) # Use cached financials
                        bal = stock.quarterly_balance_sheet # Quarterly balance sheet is not cached yet
                        
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
                    if div_yield is not None: 
                        div_yield *= 100.0
                if op_margin is None:
                    op_margin = safe_float(info.get('operatingMargins'))
                    if op_margin is not None: op_margin *= 100
                
                rev_growth = safe_float(info.get('revenueGrowth'))
                if rev_growth is not None: rev_growth *= 100
                
                data_list.append({
                    'Symbol': formatted_ticker,
                    'Company': info.get('shortName') or info.get('longName') or formatted_ticker,
                    'Sector': info.get('sector') or info.get('industry') or "Unknown",
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
                    'EPS_TTM': eps, # Added for Valuation Models
                    'YF_Obj': stock 
                })
        except Exception:
            continue
            
    return pd.DataFrame(data_list)

# --- Stage 2: Financial Analysis (Historical) ---
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
    c_title, c_link = st.columns([3, 1])
    with c_title:
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

    run_scan = st.button(get_text('execute_btn'), use_container_width=True, type="primary")

    if run_scan:
        # --- QUOTA CHECK ---
        user_id = st.session_state.get('username')
        allowed, msg, count, limit = auth_mongo.check_quota(user_id, 'scanner')
        
        if not allowed:
            st.error(msg)
            return

        # Increment Usage AFTER successful check (or after successful run? Let's debit on click for now to suppress spam)
        auth_mongo.increment_quota(user_id, 'scanner')
        st.toast(f"Usage: {count+1}/{limit}", icon="🎫")

        # --- EXECUTE SCAN ---
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
                
                # --- BACKFILL MERGE (Restored) ---
                if 'Derived_PEG' in final_df.columns:
                     final_df['PEG'] = final_df['PEG'].fillna(final_df['Derived_PEG'])
                
                if 'Derived_FV' in final_df.columns:
                     final_df['Fair_Value'] = final_df['Fair_Value'].fillna(final_df['Derived_FV'])
                     # Recalculate Margin of Safety
                     final_df['Margin_Safety'] = final_df.apply(
                        lambda r: ((r['Fair_Value'] - r['Price']) / r['Fair_Value'] * 100) 
                        if (pd.notnull(r['Fair_Value']) and r['Fair_Value'] != 0) else 0, axis=1
                     )
                
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
            display_df = final_df.drop(columns=['YF_Obj'], errors='ignore')
        else:
            display_df = final_df

        st.dataframe(display_df, column_order=final_cols, column_config=col_config, hide_index=True, width="stretch")
        
        # Cloud Warning Check
        if 'Fit_Score' in final_df.columns and (final_df['Fit_Score'] == 0).all():
            st.warning("⚠️ **Data Recovery Mode Active**: Advanced metrics (P/E, ROE) were manually calculated due to Cloud restrictions.")
        else:
            if final_df.shape[0] > 0 and 'YF_Obj' not in final_df.columns:
                 if final_df['PE'].isna().sum() > len(final_df) * 0.5:
                      st.warning("⚠️ **Cloud Data Limitation**: Some advanced metrics might be missing.")
        
        with st.expander("📋 View Stage 1 Data (All Scanned Stocks)"):
            dump_df = df.drop(columns=['YF_Obj'], errors='ignore')
            
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

        # --- Manual Financial Analysis Section ---
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


def calculate_dcf(fcf, growth_rate, discount_rate, terminal_growth, years=5):
    """
    Calculates intrinsic value using DCF model.
    Returns dictionary with details for visualization.
    """
    future_fcf = []
    discounted_fcf = []
    
    current_fcf = fcf
    
def calculate_dcf(current_fcf, growth_rate, discount_rate, terminal_growth=0.025, years=5, exit_multiple=None):
    """
    Calculates intrinsic value per share using DCF.
    Supports either Gordon Growth Method (default) or Exit Multiple Method.
    """
    future_fcf = []
    discounted_fcf = []
    
    # 1. Projected FCF
    for i in range(1, years + 1):
        # Decay growth for long periods (Simple decay: after 5 years, drop to half)
        g = growth_rate
        if i > 5: g = growth_rate * 0.75 
        
        next_fcf = current_fcf * (1 + g)
        future_fcf.append(next_fcf)
        
        # Discount it
        df = next_fcf / ((1 + discount_rate) ** i)
        discounted_fcf.append(df)
        
        current_fcf = next_fcf
        
    # 2. Terminal Value
    if not future_fcf: return {'value': 0}
    last_fcf = future_fcf[-1]
    
    if exit_multiple is not None:
        # Exit Multiple Method (Common for Tech/Growth)
        # TV = EBITDA_n * Multiple (Here we use FCF/EPS as proxy for simple inputs)
        terminal_val = last_fcf * exit_multiple
    else:
        # Gordon Growth Method
        # Formula: (FCF_n * (1 + g)) / (WACC - g)
        
        # Safety: If discount rate <= terminal growth, formula breaks. 
        if discount_rate <= terminal_growth:
            denom = 0.005 
        else:
            denom = discount_rate - terminal_growth
            
        terminal_val = (last_fcf * (1 + terminal_growth)) / denom
    
    # Discount TV
    discounted_tv = terminal_val / ((1 + discount_rate) ** years)
    
    total_value = sum(discounted_fcf) + discounted_tv
    
    return {
        'value': total_value,
        'projected_fcf': future_fcf,
        'terminal_value': terminal_val,
        'discounted_tv': discounted_tv
    }

# ---------------------------------------------------------
# PAGES: Single Stock & Glossary
# ---------------------------------------------------------

def page_single_stock():
    st.markdown(f"<h1 style='text-align: center;'>{get_text('deep_dive_title')}</h1>", unsafe_allow_html=True)


    ticker = st.text_input(get_text('search_ticker'))
    
    # Initialize df to prevent UnboundLocalError
    df = pd.DataFrame() # Empty default
    
    # Define Mocks at top scope for re-use in persisted blocks
    class MockProgress:
        def progress(self, x): pass
    class MockStatus:
        def caption(self, x): pass
        def empty(self): pass

    # State Persistence Logic
    run_deep_dive = st.button(get_text('analyze_btn'))
    if run_deep_dive and ticker:
        # --- QUOTA CHECK ---
        user_id = st.session_state.get('username')
        allowed, msg, count, limit = auth_mongo.check_quota(user_id, 'deep_dive')
        if not allowed:
            st.error(msg)
        else:
            auth_mongo.increment_quota(user_id, 'deep_dive')
            st.toast(f"Usage: {count+1}/{limit}", icon="🎫")

            with st.spinner(f"Analyzing {ticker}..."):
                new_df = scan_market_basic([ticker], MockProgress(), st.empty())
                if not new_df.empty:
                    new_df['Lynch_Category'] = new_df.apply(classify_lynch, axis=1) # Apply Lynch Logic locally
                st.session_state['single_stock_cache'] = new_df
            
    # Display Logic (Wrapper to maintain indentation of subsequent block)
    # We use st.container() to provide the indentation level previously held by 'with st.spinner'
    if 'single_stock_cache' in st.session_state:
        with st.container():
            df = st.session_state['single_stock_cache']
            # Safety: Ensure Lynch col exists for old cache
            if not df.empty and 'Lynch_Category' not in df.columns:
                 df['Lynch_Category'] = df.apply(classify_lynch, axis=1)
            
            if not df.empty:
                row = df.iloc[0].copy()
                row = df.iloc[0].copy()
                price = row['Price']
                # Setup Currency Fmt (Moved Up)
                currency_fmt = "฿" if ".BK" in row['Symbol'] else "$"
                
                # --- HEADER INFORMATION (Restored) ---
                # User Request: Sector, Lynch Type with Explanation
                
                c_head_1, c_head_2, c_head_3 = st.columns(3)
                
                with c_head_1:
                    st.metric("Price", f"{currency_fmt[0]}{price:.2f}")
                
                with c_head_2:
                    sector_val = row.get('Sector', 'Unknown')
                    st.caption(f"SECTOR {get_text('sector_tooltip')}") # Custom tooltip logic below? No, st.caption doesn't support help natively well in all versions.
                    # Use st.help or just inline text? 
                    # Request: "Explain what it is". 
                    st.markdown(f"**{sector_val}**", help=get_text('sector_desc'))
                    
                with c_head_3:
                    lynch_val = row.get('Lynch_Category', 'Unknown')
                    st.caption(f"TYPE {get_text('lynch_tooltip')}")
                    st.markdown(f"**{lynch_val}**", help=get_text('lynch_desc'))
                    
                st.divider()
                
                # Setup Currency Fmt
                # Setup Currency Fmt (Duplicate Removed)
                # currency_fmt = "฿" if ".BK" in row['Symbol'] else "$"
                
                # --- PROFESSIONAL VALUATION ENGINE (Range Based) ---
                # We need TWO scenarios for each model: Base (High) and Conservative (Low)
                
                # Helper to display a standardized Valuation Card with INTERACTIVE INPUTS
                # We use St.container() trick to render inputs "visually below" but execute them "logically first"
                # so the calculation updates immediately in the same run.
                def val_card_interactive(title, current_price, model_defaults):
                    # 1. Create Layout Containers
                    c_header = st.container() # Visually Top (Results)
                    st.divider()
                    c_inputs = st.container() # Visually Bottom (Inputs)
                    
                    # 2. Render Inputs FIRST (to capture state)
                    base_val = model_defaults.get('base', 0)
                    
                    with c_inputs:
                        # --- ROW 2: Base Metric | Growth Rate | Growth Years ---
                        c_r2_1, c_r2_2, c_r2_3 = st.columns(3)
                        
                        # Base Metric (Static for now, but could be editable)
                        label_base = title # Pass Full Title as Label
                        if "FCF" in title: label_base = f"FCF/SHARE {model_defaults.get('suffix', '')}"
                        elif "EPS" in title: label_base = "EPS (TTM)"
                        
                        with c_r2_1:
                            st.caption(label_base)
                            st.info(f"**{currency_fmt[0]}{base_val:.2f}**")
                            
                        # Growth Rate (Interactive)
                        unique_key = f"{row['Symbol']}_{title}_growth"
                        default_g = float(model_defaults.get('g_high', 0.15)) * 100
                        with c_r2_2:
                            st.caption("GROWTH RATE (%)")
                            new_g_percent = st.number_input("Growth", value=default_g, step=1.0, key=unique_key, label_visibility="collapsed")
                            new_g = new_g_percent / 100.0
                            
                        # Years (Interactive)
                        unique_key_y = f"{row['Symbol']}_{title}_years"
                        default_y = int(model_defaults.get('years', 10))
                        with c_r2_3:
                            st.caption("GROWTH YEARS")
                            new_years = st.number_input("Years", value=default_y, step=1, key=unique_key_y, label_visibility="collapsed")

                        # --- ROW 3: Discount | Exit | Type ---
                        c_r3_1, c_r3_2, c_r3_3 = st.columns(3)
                        
                        # Discount Rate (Interactive)
                        unique_key_w = f"{row['Symbol']}_{title}_wacc"
                        default_w = float(model_defaults.get('wacc', 0.08)) * 100
                        with c_r3_1:
                            st.caption("DISCOUNT RATE (%)")
                            new_wacc_percent = st.number_input("WACC", value=default_w, step=0.5, key=unique_key_w, label_visibility="collapsed")
                            new_wacc = new_wacc_percent / 100.0
                            
                        # Exit Multiple (Interactive)
                        unique_key_e = f"{row['Symbol']}_{title}_exit"
                        default_e = float(model_defaults.get('exit_high', 20.0))
                        with c_r3_2:
                            st.caption("EXIT MULTIPLE (x)")
                            new_exit = st.number_input("Exit", value=default_e, step=0.5, key=unique_key_e, label_visibility="collapsed")
                            
                        # Exit Type
                        with c_r3_3:
                            st.caption("EXIT MULTIPLE TYPE")
                            st.write("**EV/EBITDA Avg**")
                    
                    # 3. Calculate Results using NEW Inputs
                    # We maintain the "Range" concept by auto-calculating a Low case relative to the User's Input
                    # Low Case: Growth - 5%, Exit * 0.75
                    
                    # High Case (User Input)
                    res_high = calculate_dcf(base_val, new_g, new_wacc, years=new_years, exit_multiple=new_exit)
                    val_high = res_high['value']
                    
                    # Low Case (Derived Conservative)
                    # new_g_low = max(new_g - 0.05, 0.03)
                    # new_exit_low = new_exit * 0.75
                    # Let's make "Low" slightly smarter or just relative
                    # Actually, user wants to see the Range based on Inputs. 
                    # If user edits the "Input", does it mean "High Case Input"? 
                    # Yes, typically "Base" or "Optimistic" input.
                    # We show range:
                    g_low_calc = max(new_g - 0.05, 0.03)
                    exit_low_calc = new_exit * 0.75
                    
                    res_low = calculate_dcf(base_val, g_low_calc, new_wacc, years=new_years, exit_multiple=exit_low_calc)
                    val_low = res_low['value']

                    # 4. Render Results in Header Container
                    with c_header:
                        # --- ROW 1: Fair Value Range | Last Close | MoS ---
                        c1, c2, c3 = st.columns([1.5, 1, 1.2]) 
                        
                        # 1. Fair Value Range
                        # Calculate Range String based on NEW values
                        with c1:
                            val_str = f"{currency_fmt[0]}{val_high:.2f}"
                            if val_low > 0 and val_low != val_high:
                                val_str = f"{currency_fmt[0]}{val_low:.2f} - {currency_fmt[0]}{val_high:.2f}"
                            st.caption("FAIR VALUE PRICE")
                            st.markdown(f"#### {val_str}")
                        
                        # 2. Last Close
                        with c2:
                            st.caption("LAST CLOSE PRICE")
                            st.markdown(f"#### {currency_fmt[0]}{current_price:.2f}")
                            
                        # 3. Margin of Safety (Recalculated)
                        with c3:
                            mos_base = (val_high - current_price)/val_high * 100 if (val_high and val_high > 0) else 0
                            mos_low_val = (val_low - current_price)/val_low * 100 if (val_low and val_low > 0) else 0
                            
                            mos_str = f"{mos_base:.1f}%"
                            color = "green" if mos_base > 0 else "red"
                            bg_color = "rgba(0,128,0,0.1)" if mos_base > 0 else "rgba(255,0,0,0.1)"
                             
                            if val_low != val_high:
                                mos_str = f"{mos_low_val:.1f}% - {mos_base:.1f}%"
                                if mos_low_val < 0 and mos_base > 0: color = "orange"; bg_color = "rgba(255,165,0,0.1)"
                                elif mos_base < 0: color = "red"; bg_color = "rgba(255,0,0,0.1)"
                            
                            st.caption("MGN OF SAFETY")
                            st.markdown(f"<span style='color:{color}; background-color:{bg_color}; padding: 2px 6px; border-radius: 4px; font-weight:bold'>{mos_str}</span>", unsafe_allow_html=True)

                    return val_high # Return the calculated High Value for global context if needed

                # --- 1. DATA PREP ---
                val_models = {} # Store results for header selection
                
                # Global Params
                is_tech = "Technology" in row.get('Sector','') or "Communication" in row.get('Sector','')
                stock_obj = row['YF_Obj']
                
                # SAFE INFO FETCH
                s_info = safe_get_info(stock_obj)
                shares = s_info.get('sharesOutstanding')
                mkt_cap_val = row.get('Market_Cap', 0) or 0
                price_val = row.get('Price', 1) or 1
                if not shares: shares = mkt_cap_val / price_val # Fallback
                
                cashflow = stock_obj.cashflow
                
                # WACC
                # WACC
                beta = s_info.get('beta', 1.0)
                if not beta: beta = 1.0
                
                # Default Logic
                wacc = 0.04 + (beta * 0.055) if is_tech else 0.04 + (beta * 0.06)
                if wacc < 0.06: wacc = 0.06
                
                # Tech/Growth Specific Override (User Request: "7% Enough")
                # This aligns with the NVDA reference 7%
                if is_tech: 
                    wacc = 0.07 # Fixed 7% for Tech/Growth per request
                
                # Growth Assumptions
                # Growth Assumptions
                raw_g = row.get('EPS_Growth')
                if raw_g is None: raw_g = 0.10 # Explicit default if None
                
                if raw_g > 0.25: raw_g = 0.25 # Cap initial
                if raw_g < 0.05: raw_g = 0.05 
                
                # Scenarios
                # Growth: High = raw_g, Low = raw_g * 0.75 (or -5%?)
                g_high = raw_g
                g_low = max(raw_g - 0.05, 0.03)
                
                # Exit Multiple: High = 25 (Tech), 15 (Stnd) | Low = 0.75 * High
                exit_high = 25.0 if is_tech else 15.0
                exit_low = exit_high * 0.75
                
                years_proj = 10
                
                with st.expander("💎 Intrinsic Value Range (Professional Analysis)", expanded=True):
                    # We no longer need columns here because the Card itself will use columns internally 
                    # for the grid layout. We stack them vertically: FCF Card then EPS Card.
                    
                    # --- MODEL 1: FCF ---
                    fcf_base = 0
                    try:
                        # --- TTM FCF LOGIC (GuruFocus Alignment) ---
                        # Method: Sum(Last 4 Qtrs OCF) + Sum(Last 4 Qtrs CapEx) / Shares
                        fcf_label_suffix = "(FY)"
                        
                        # Fetch Quarterly Cashflow
                        q_cashflow = stock_obj.quarterly_cashflow
                        
                        ttm_ocf = 0
                        ttm_capex = 0
                        found_ttm = False
                        
                        if not q_cashflow.empty:
                            try:
                                # OCF
                                q_ocf = None
                                for k in ['Operating Cash Flow', 'Total Cash From Operating Activities']:
                                    if k in q_cashflow.index: q_ocf = q_cashflow.loc[k].iloc[:4]; break # Take recent 4
                                
                                # CapEx
                                q_capex = None
                                for k in ['Capital Expenditure', 'Capital Expenditures', 'Purchase Of PPE']:
                                    if k in q_cashflow.index: q_capex = q_cashflow.loc[k].iloc[:4]; break
                                
                                if q_ocf is not None and q_capex is not None and len(q_ocf) >= 4:
                                    q_ocf = pd.to_numeric(q_ocf, errors='coerce').fillna(0)
                                    q_capex = pd.to_numeric(q_capex, errors='coerce').fillna(0)
                                    
                                    ttm_ocf = q_ocf.sum()
                                    ttm_capex = q_capex.sum()
                                    ttm_fcf = ttm_ocf + ttm_capex
                                    fcf_base = ttm_fcf / shares if (shares and shares > 0) else 0
                                    found_ttm = True
                                    fcf_label_suffix = "(TTM)"
                            except: pass

                        # Fallback to Annual if TTM failed
                        if not found_ttm:
                             fcf_series = None
                             if not cashflow.empty and shares:
                                  ocf, capex = None, None
                                  for k in ['Operating Cash Flow', 'Total Cash From Operating Activities']:
                                      if k in cashflow.index: ocf = cashflow.loc[k]; break
                                  for k in ['Capital Expenditure', 'Capital Expenditures', 'Purchase Of PPE']:
                                      if k in cashflow.index: capex = cashflow.loc[k]; break
                                      
                                  if ocf is not None and capex is not None:
                                       ocf = pd.to_numeric(ocf, errors='coerce')
                                       capex = pd.to_numeric(capex, errors='coerce')
                                       fcf_series = (ocf + capex).dropna()
                                       
                             if fcf_series is not None and not fcf_series.empty:
                                  # Use Latest Year for Annual Fallback (GuruFocus uses latest Full Year if no TTM)
                                  # Or Average? GuruFocus uses "FCF per share for the trailing twelve months".
                                  # If we can't get TTM, Latest FY is best proxy.
                                  avg_fcf = fcf_series.iloc[0] # Latest
                                  fcf_base = avg_fcf / shares
                             elif 'Free Cash Flow' in cashflow.index:
                                  fcf_series = cashflow.loc['Free Cash Flow'].dropna()
                                  if not fcf_series.empty: fcf_base = fcf_series.iloc[0] / shares

                        if fcf_base and fcf_base > 0:
                            # CALL INTERACTIVE CARD
                            # Note: We pass the calculated defaults. The card will either use them (first run) or use widget state (reruns).
                            # We don't need to manually calc val_high/low here anymore, the card does it.
                            
                            high_val = val_card_interactive("NVDA Intrinsic Value Range (FCF)", price, {
                                'base': fcf_base, 
                                'g_high': g_high, 
                                'exit_high': exit_high, 
                                'wacc': wacc, 
                                'years': years_proj,
                                'suffix': fcf_label_suffix
                            })
                            
                            val_models['FCF'] = high_val # Store the interactive result
                        else:
                            st.warning("FCF Data Unavailable for FCF Valuation Model")
                    except Exception as e: st.error(f"FCF Model Error: {e}")

                    st.markdown("") # Spacer between cards

                    # --- MODEL 2: EPS ---
                    eps_base = row.get('EPS_TTM', 0)
                    if eps_base and eps_base > 0:
                        high_val_eps = val_card_interactive("NVDA Intrinsic Value Range w/EPS", price, {
                                'base': eps_base, 
                                'g_high': g_high, 
                                'exit_high': exit_high, 
                                'wacc': wacc, 
                                'years': years_proj
                        })
                        val_models['EPS'] = high_val_eps
                    else:
                        st.warning("Positive EPS Required for EPS Valuation Model")

                # Pick "Best Fit" based on Sector to update Header
                # Tech -> EPS, Others -> FCF (if available)
                best_val = 0
                best_method = "Fair Value"
                
                if "Technology" in row.get('Sector', '') or "Communication" in row.get('Sector', ''):
                    if 'EPS' in val_models: best_val = val_models['EPS']; best_method = "Fair Value (EPS)"
                else:
                    if 'FCF' in val_models: best_val = val_models['FCF']; best_method = "Fair Value (FCF)"
                    elif 'EPS' in val_models: best_val = val_models['EPS']; best_method = "Fair Value" # Fallback

                # Top Header Update Logic (Re-calc header metric)
                # Note: We already rendered header way above. 
                # Ideally we should move header rendering BELOW this calculation.
                # But since Streamlit renders logically top-down, we might need a placeholder or just accept 'best_fit' from simplified logic above?
                # Actually, let's keep the simplified logic above for header (it was decent) 
                # OR we refactor the whole function to calc first.
                # Refactoring calc first is safer but bigger diff. 
                # Let's insert this Detailed Block and keep the header as "Estimated".
                # The header logic was "Advanced DCF (EPS)" which matches our High Case EPS. So it aligns.

                
                # Fetch deeper data for context
                deep_metrics = analyze_history_deep(df, MockProgress(), st.empty())
                if not deep_metrics.empty:
                    deep_row = deep_metrics.iloc[0]
                    # Merge manually for display
                    for k, v in deep_row.items(): row[k] = v

                    # --- BACKFILL COALESCE (Restored) ---
                    if (pd.isna(row.get('PEG')) or row.get('PEG') is None) and row.get('Derived_PEG'):
                        row['PEG'] = row['Derived_PEG']
                    
                    if (pd.isna(row.get('Fair_Value')) or row.get('Fair_Value') is None) and row.get('Derived_FV'):
                        row['Fair_Value'] = row['Derived_FV']
                        if row.get('Price') and row.get('Fair_Value') is not None and row['Fair_Value'] != 0:
                             row['Margin_Safety'] = ((row['Fair_Value'] - row['Price']) / row['Fair_Value']) * 100
                    
                    # Strategy Scores
                    st.markdown("### 🎯 Strategy Fit Scorecard")
                    
                    # 1. GARP Score
                    c_s1, c_s2, c_s3, c_s4 = st.columns(4) # Convert to 4 cols now
                    
                    score, details = calculate_fit_score(row, [('PEG', 1.2, '<'), ('EPS_Growth', 0.15, '>'), ('ROE', 15.0, '>')])
                    c_s1.metric(get_text('score_garp'), f"{score}/100")
                    # if details != "✅ Perfect Match": c_s1.caption(details)

                    # 2. Value Score
                    score, details = calculate_fit_score(row, [('PE', 15.0, '<'), ('PB', 1.5, '<'), ('Debt_Equity', 50.0, '<')])
                    c_s2.metric(get_text('score_value'), f"{score}/100")
                    # if details != "✅ Perfect Match": c_s2.caption(details)
                    
                    # 3. Dividend Score
                    score, details = calculate_fit_score(row, [('Div_Yield', 4.0, '>'), ('Op_Margin', 10.0, '>')])
                    c_s3.metric(get_text('score_div'), f"{score}/100")
                    # if details != get_text('perfect_match'): c_s3.caption(details)

                    # 4. Multibagger Score
                    score, details = calculate_fit_score(row, [('Rev_Growth', 30.0, '>'), ('EPS_Growth', 20.0, '>'), ('PEG', 2.0, '<')])
                    c_s4.metric(get_text('score_multi'), f"{score}/100")

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
                
                st.markdown("---")
                st.subheader(get_text('health_check_title'))
                col1, col2 = st.columns(2)
                
                with col1:
                    st.markdown(f"**{get_text('val_label')}**")
                    st.write(f"- P/E: **{row.get('PE') if row.get('PE') is not None else 0:.1f}**")
                    st.write(f"- PEG: **{row.get('PEG') if row.get('PEG') is not None else 0:.2f}**")
                    st.write(f"- P/B: **{row.get('PB') if row.get('PB') is not None else 0:.2f}**")
                    st.write(f"- Fair Value: **{row.get('Fair_Value') if row.get('Fair_Value') is not None else 0:.2f}**")
                
                with col2:
                    st.markdown(f"**{get_text('qual_label')}**")
                    st.write(f"- ROE: **{row.get('ROE') if row.get('ROE') is not None else 0:.1f}%**")
                    st.write(f"- Margin: **{row.get('Op_Margin') if row.get('Op_Margin') is not None else 0:.1f}%**")
                    st.write(f"- Debt/Equity: **{row.get('Debt_Equity') if row.get('Debt_Equity') is not None else 0:.0f}%**")
                    st.write(f"- Dividend: **{row.get('Div_Yield') if row.get('Div_Yield') is not None else 0:.2f}%**")
                
                # --- GURU & ANALYST DATA ---
                st.markdown("---")
                st.subheader(get_text('guru_intel_title'))
                
                tab_guru, tab_rec = st.tabs([get_text('tab_holders'), get_text('tab_recs')])
                
                with tab_guru:
                    try:
                        holders = stock_obj.institutional_holders
                        if holders is not None and not holders.empty:
                            st.dataframe(holders, hide_index=True, use_container_width=True)
                            st.caption(get_text('holders_desc'))
                        else:
                            st.info(get_text('no_holders'))
                    except: st.error(get_text('err_holders'))
                    
                with tab_rec:
                    try:
                        recs = stock_obj.recommendations
                        if recs is not None and not recs.empty:
                            # Show latest recommendations summary
                            # yfinance often returns a long history, let's show summary or recent
                            st.dataframe(recs.tail(10), use_container_width=True)
                        
                        # Analyst Targets
                        tgt_mean = row.get('Target_Price')
                        if tgt_mean:
                            st.metric(get_text('consensus_target'), f"{tgt_mean}", f"{get_text('vs_current')}: {price}")
                        else:
                            st.info(get_text('no_target'))
                            
                    except: st.error(get_text('err_recs'))

                # Show Chart
                st.markdown(get_text('price_trend_title'))
                stock = row['YF_Obj']
                hist = stock.history(period="5y")
                if not hist.empty:
                    st.line_chart(hist['Close'])


            else:
                st.error(get_text('err_fetch'))






# ---------------------------------------------------------
# AI ANALYSIS PAGE
# ---------------------------------------------------------
# ---------------------------------------------------------
# AI ANALYSIS PAGE
# ---------------------------------------------------------
# --- HELPER: FALLBACK NEWS ---
def fetch_google_news(ticker):
    """Fetch news from Google RSS if Yahoo fails."""
    try:
        # Clean ticker for search
        query = ticker.replace('.BK', ' Thailand Stock')
        url = f"https://news.google.com/rss/search?q={query}&hl=en-TH&gl=TH&ceid=TH:en"
        
        headers = {'User-Agent': 'Mozilla/5.0'}
        response = requests.get(url, headers=headers, timeout=5)
        
        root = ET.fromstring(response.content)
        news_items = []
        for item in root.findall('.//item')[:5]:
            title = item.find('title').text
            pub_date = item.find('pubDate').text
            news_items.append(f"- {title} ({pub_date}) [Source: Google News]")
            
        return "\\n".join(news_items)
    except Exception as e:
        return f"Error fetching fallback news: {str(e)}"
 
def page_ai_analysis():
    st.markdown(f"<h1 style='text-align: center;'>AI Analysis</h1>", unsafe_allow_html=True)

    
    st.info("Powered by **Gemini 3.0 Flash**. This module provides a 360-degree investment research report with **Real-time Data Context**.")

    # API Key Handling (Secure)
    if 'GEMINI_API_KEY' in st.secrets:
        api_key = st.secrets['GEMINI_API_KEY']
    else:
        st.error("🚨 Missing API Key. Please add `GEMINI_API_KEY` to `.streamlit/secrets.toml`.")
        return

    if api_key == "PASTE_YOUR_NEW_API_KEY_HERE":
        st.error("⚠️ Please update `.streamlit/secrets.toml` with your actual Google Gemini API Key.")
        return 
    
    # Input Ticker
    col_input, col_btn = st.columns([3, 1])
    with col_input:
        ticker = st.text_input("Enter Specfic Stock Ticker (e.g., DELTA.BK, NVDA, PTT.BK)", value="DELTA.BK")
    
    with col_btn:
        st.write("") # Spacer
        st.write("")
        analyze_click = st.button("✨ Analyze with AI", type="primary", use_container_width=True)

    if analyze_click and ticker:
        # --- QUOTA CHECK ---
        user_id = st.session_state.get('username')
        allowed, msg, count, limit = auth_mongo.check_quota(user_id, 'ai_analysis')
        if not allowed:
            st.error(msg)
            return
        
        auth_mongo.increment_quota(user_id, 'ai_analysis')
        st.toast(f"Usage: {count+1}/{limit}", icon="🎫")

        try:
            # 1. FETCH LIVE DATA
            with st.spinner(f"📡 Fetching Live Data for {ticker}..."):
                # Clean Ticker
                if ".BK" in ticker: formatted_ticker = ticker
                else: formatted_ticker = ticker.replace('.', '-')
                
                stock = yf.Ticker(formatted_ticker)
                
                # Fetch Info (with Retry)
                try:
                    info = retry_api_call(lambda: stock.info)
                    if info is None: info = {} # Safeguard against None
                except: info = {}
                
                # Fetch News (with Retry)
                try:
                    news = retry_api_call(lambda: stock.news[:3] if stock.news else [])
                except: news = []
                
                if news:
                    news_items = []
                    for n in news:
                        if isinstance(n, dict): # Check if item is dict
                            ts = n.get('providerPublishTime', 0)
                            date_str = datetime.datetime.fromtimestamp(ts).strftime('%Y-%m-%d') if ts > 0 else "Date N/A"
                            news_items.append(f"- {n.get('title')} ({n.get('publisher')}) [{date_str}]")
                    news_text = "\n".join(news_items) if news_items else "No News Found"
                else:
                    # FALLBACK
                    news_text = fetch_google_news(formatted_ticker)
                
                # Fetch Recent History (30 Days) (with Retry)
                try:
                    hist = retry_api_call(lambda: stock.history(period="1mo"))
                    hist_text = hist.tail(10).to_csv() if not hist.empty else "No Data"
                except: 
                    hist_text = "No Price History Data"
                
                # Fetch Richer Data
                long_summary = info.get('longBusinessSummary', 'No Business Summary Available')
                sector = info.get('sector', 'Unknown')
                industry = info.get('industry', 'Unknown')
                
                # Financials (Last 2 Years)
                try: 
                    financials = stock.financials.iloc[:, :2].to_string() 
                except: financials = "No Financial Data"
                
                # Balance Sheet (Last 1 Year - key columns)
                try:
                    bs = stock.balance_sheet.iloc[:, :1].to_string()
                except: bs = "No Balance Sheet Data"
                
                # Shareholders
                try:
                    holders = stock.major_holders.to_string()
                except: holders = "No Shareholder Data"
                
                # Management / Officers
                officers_data = "No Officer Data"
                try:
                    officers_list = info.get('companyOfficers', [])
                    if officers_list:
                         officers_data = "\n".join([f"- {o.get('name')} ({o.get('title')})" for o in officers_list[:5]])
                except: pass

                # Context String
                context_data = f"""
                [REAL-TIME CONTEXT DATA FROM YAHOO FINANCE]
                Current Price: {info.get('currentPrice')} {info.get('currency')}
                Market Cap: {info.get('marketCap')}
                PE Ratio: {info.get('trailingPE')}
                Target Price: {info.get('targetMeanPrice')}
                Sector: {sector} | Industry: {industry}
                
                [BUSINESS SUMMARY]
                {long_summary}
                
                [LATEST NEWS]
                {news_text}
                
                [FINANCIALS (Annual)]
                {financials}
                
                [BALANCE SHEET (Latest)]
                {bs}
                
                [MAJOR HOLDERS]
                {holders}
                
                [MANAGEMENT & OFFICERS]
                {officers_data}
                
                [RECENT PRICE ACTION (Last 10 Days)]
                {hist_text}
                
                [END CONTEXT]
                """

            # 2. AI ANALYSIS    
            genai.configure(api_key=api_key)
            model_name = "models/gemini-3-flash-preview"
            model = genai.GenerativeModel(model_name)
            
            # Construct Prompt with Context
            prompt = f"""
            Act as a Senior Equity Analyst and Rating Agency (like Moody's) but with the mindset of a **Skeptical Hedge Fund Short Seller**.
            
            Your goal is NOT to flatter the company. Your goal is to **Stress Test** the investment thesis.
            You must be BRUTALLY HONEST, UNBIASED, and DIRECT.
            
            **INPUT CONTEXT:**
            {context_data}

            **GLOBAL MACRO & STRATEGIC FRAMEWORK (Must Factor into Grading):**
            1. **Dimension 1: Mega Trend Alignment:** Sunset vs Sunrise Industry? (e.g. AI/Healthcare = Sunrise). Disruption Check.
            2. **Dimension 2: Missing Growth Driver:** Old S-Curve (Exhausted) vs New S-Curve. New Revenue stream > 5%.
            3. **Dimension 3: Market Opportunity & Moat:** Red Ocean (Price War) vs Blue Ocean (Pricing Power). TAM Saturation.
            4. **Dimension 4: Country/Macro Context:** Economic Engine, Demographics, Fund Flow (especially for .BK stocks).

            **Core Instructions:**
            1. **Persona:** Adopt a "Devil's Advocate" view. Why might this stock FAIL? What are the hidden risks?
            2. **Chain of Thought:** Think step-by-step. First analyze the financials, then the business model, then the management, and finally synthesize everything into a grade.
            3. **Analyze Deeply:** Look at the business model, moat, and financial health structure based on the provided context AND the Global Macro Framework above.
            4. **CEO & Management Focus:** specifically analyze the **CEO** (Who are they? Pros/Cons). If CEO data is missing in the context, **USE YOUR KNOWLEDGE** to identify the current CEO.
            5. **Detailed Business Model:** Explain heavily what they do. Do not summarize in 1 line. Write 2-3 paragraphs.
            6. **Product Portfolio:** Analyze key products/services. What are they? How are they performing? What is the future outlook?
            7. **Customer Ecosystem:** Identify key customer groups (Who buys?). How important is this company to them? (Critical supplier or easily replaceable?).
            8. **Industry Landscape:** Analyze the industry structure, growth drivers, outlook, and market share.
            9. **SWOT Analysis:** Conduct a detailed SWOT Analysis. Focus on **THREATS** and **WEAKNESSES**.
            10. **Strategic Positioning:** Analyze the stock using the 4 Dimensions of the Global Macro Framework.
            11. **Assign a Grade (A-F):** Be strict. An 'A' is reserved for World-Class Monopolies only. 'C' is Average. 'F' is Dangerous.
            12. **NO HALLUCINATION:** Do NOT invent data EXCEPT for the CEO if missing. For other fields, state "No Data" if unsure.
            13. **Output:** Strictly in valid JSON format. Use Thai language for content values.

            **JSON Schema:**

            {{
              "stock_identity": {{
                "symbol": "String",
                "company_name": "String",
                "business_nature": "String"
              }},
              "fundamental_grading_report": {{
                "overall_grade": "String (A / B+ / B / C / D / F)",
                "score_summary": "String (Short justification: Why did it get this grade?)",
                "key_strengths": [
                    "String",
                    "String"
                ],
                "key_weaknesses": [
                    "String",
                    "String"
                ]
              }},
              "strategic_positioning": {{
                 "mega_trend": "String (Sunrise/Sunset analysis)",
                 "growth_driver": "String (S-Curve analysis)",
                 "moat_opportunity": "String (Red/Blue Ocean)",
                 "macro_context": "String (Country/Economic context)"
              }},
              "business_deep_dive": {{
                "what_they_do": "String (Very Detailed 2-3 paragraphs explanation of business model)",
                "revenue_sources": "String (Detailed breakdown)",
                "customer_ecosystem": {{
                    "key_customers": ["String (Customer Group 1)", "String (Group 2)"],
                    "dependence_level": "String (High/Low & Explanation of Importance to Customers)"
                }},
                "product_portfolio": [
                    {{
                        "name": "String (Product Name)",
                        "description": "String (What is it?)",
                        "current_performance": "String (Is it selling well? Cash cow?)",
                        "future_outlook": "String (Growth potential/Next gen version)"
                    }},
                    {{
                        "name": "String (Product Name)",
                        "description": "String (What is it?)",
                        "current_performance": "String",
                         "future_outlook": "String"
                    }}
                ],
                "pricing_power": "String (High/Low - Maker or Taker)"
              }},
              "industry_overview": {{
                "industry_landscape": "String (Fragmented/Consolidated, Key Players)",
                "sector_outlook": "String (Growing, Stagnant, Disrupted?)",
                "growth_drivers": ["String (Driver 1)", "String (Driver 2)"],
                "market_share_analysis": "String (Estimated share, Gaining or Losing?)"
              }},
              "swot_analysis": {{
                "strengths": ["String", "String"],
                "weaknesses": ["String", "String"],
                "opportunities": ["String", "String"],
                "threats": ["String", "String"]
              }},
              "management_analysis": {{
                "ceo_name": "String (Name of CEO)",
                "ceo_capability_finding": "String (Pros/Cons of this leader)",
                "management_integrity": "String (Transparency/Governance)",
                "strategy_vision": "String"
              }},
              "moat_analysis": {{
                "moat_level": "String (Wide / Narrow / None)",
                "moat_source": "String",
                "moat_durability": "String (Long-term sustainability)"
              }},
              "financial_structure_health": {{
                "balance_sheet_status": "String (Strong/Weak - Debt level)",
                "cash_flow_status": "String (Cash Rich or Cash Burn)",
                "profitability_trend": "String (Margin expansion or compression)"
              }},
              "competitive_landscape": {{
                "direct_competitors": [
                    "String",
                    "String"
                ],
                "market_position_rank": "String",
                "competition_intensity": "String"
              }},
              "long_term_outlook": {{
                "bull_case": "String",
                "bear_case": "String"
              }}
            }}
            """

            
            with st.spinner("🤖 AI is analyzing... (This may take 10-20 seconds)"):
                try:
                    generation_config = genai.types.GenerationConfig(
                        temperature=0.1,
                        top_p=0.95,
                        top_k=40,
                        max_output_tokens=8192,
                    )
                    
                    response = retry_api_call(lambda: model.generate_content(prompt, generation_config=generation_config))
                    # Try to parse JSON from text (handle potential markdown ticks)
                    text_out = response.text
                    clean_json = text_out.replace("```json", "").replace("```", "").strip()
                    data = json.loads(clean_json)
                    
                    st.success(f"Analysis Complete for {data['stock_identity']['symbol']}")
                    
                    # --- RENDER UI CARDS ---
                    
                    # 1. Header Card
                    with st.container():
                        c1, c2 = st.columns([1, 4])
                        
                        # Grade Circle (Simulated)
                        grade = data['fundamental_grading_report']['overall_grade']
                        color_map = {'A': 'green', 'B': 'teal', 'C': 'orange', 'D': 'red', 'F': 'red'}
                        grade_color = color_map.get(grade[0], 'blue')
                        
                        with c1:
                            st.markdown(f"<h1 style='text-align: center; color: {grade_color}; font-size: 60px;'>{grade}</h1>", unsafe_allow_html=True)
                            st.caption("Fundamental Grade")
                            
                        with c2:
                            st.subheader(f"{data['stock_identity']['company_name']} ({data['stock_identity']['symbol']})")
                            st.write(f"**Business:** {data['stock_identity']['business_nature']}")
                            st.info(f"**Verdict:** {data['fundamental_grading_report']['score_summary']}")
                    
                    st.divider()
                    
                    # 2. Key Grades Details
                    k1, k2 = st.columns(2)
                    with k1:
                        st.subheader("✅ Key Strengths")
                        for s in data['fundamental_grading_report']['key_strengths']:
                            st.success(f"- {s}")
                            
                    with k2:
                        st.subheader("⚠️ Key Risks")
                        for w in data['fundamental_grading_report']['key_weaknesses']:
                            st.error(f"- {w}")

                    st.divider()

                    st.divider()

                    st.divider()
                    st.divider()

                    # 3. Financial Analysis Tabs
                    t_swot, t_strat, t_future, t_bus, t_ind, t_mgmt, t_fin, t_comp = st.tabs(["🛡️ SWOT", "🧠 Strategy", "🚀 Growth & Future", "🏭 Business", "🌏 Industry", "🧠 Mgmt (CEO)", "💰 Financials", "⚔️ Competition"])
                    
                    with t_strat:
                        strat = data.get('strategic_positioning', {})
                        st.subheader("🌐 Global Macro & Strategic Fit")
                        
                        c_strat1, c_strat2 = st.columns(2)
                        with c_strat1:
                            st.info(f"**🌊 Mega Trend:** {strat.get('mega_trend', 'N/A')}")
                            st.info(f"**🚀 Growth Driver:** {strat.get('growth_driver', 'N/A')}")
                        with c_strat2:
                            st.success(f"**🏰 Moat:** {strat.get('moat_opportunity', 'N/A')}")
                            st.warning(f"**🌍 Macro:** {strat.get('macro_context', 'N/A')}")

                    
                    with t_swot:
                        swot = data.get('swot_analysis', {})
                        c_s, c_w = st.columns(2)
                        with c_s:
                            st.subheader("💪 Strengths")
                            for s in swot.get('strengths', []): st.success(f"- {s}")
                            st.subheader("⚠️ Weaknesses")
                            for w in swot.get('weaknesses', []): st.error(f"- {w}")
                        with c_w:
                            st.subheader("🌟 Opportunities")
                            for o in swot.get('opportunities', []): st.info(f"- {o}")
                            st.subheader("⚡ Threats")
                            for t in swot.get('threats', []): st.warning(f"- {t}")

                    with t_future:
                        # Now integrated into Business Financial Analysis or specific Product Tab, but let's keep Future Radar for products
                        bus = data.get('business_deep_dive', {})
                        products = bus.get('product_portfolio', [])
                        
                        st.subheader("🚀 Product & Service Portfolio")
                        for p in products:
                            with st.expander(f"📦 {p.get('name', 'Product')}", expanded=True):
                                st.markdown(f"**Description:** {p.get('description', '-')}")
                                c1, c2 = st.columns(2)
                                c1.info(f"**Current:** {p.get('current_performance', '-')}")
                                c2.success(f"**Future:** {p.get('future_outlook', '-')}")

                    with t_bus:
                        bus = data['business_deep_dive']
                        cust = bus.get('customer_ecosystem', {})
                        
                        st.subheader("🏢 Business Model")
                        st.markdown(bus['what_they_do'])  # Markdown handles long text wrapping better
                        
                        st.divider()
                        
                        c_rev, c_cust = st.columns(2)
                        with c_rev:
                             st.write(f"**💰 Revenue Sources:** {bus['revenue_sources']}")
                             st.markdown(f"**🏷️ Pricing Power:** {bus['pricing_power']}")
                        
                        with c_cust:
                             st.subheader("👥 Customer Ecosystem")
                             st.info(f"**Dependence Level:** {cust.get('dependence_level', '-')}")
                             if 'key_customers' in cust:
                                 for c in cust['key_customers']:
                                     st.write(f"👤 {c}")

                        st.markdown("---")
                        st.subheader("🔭 Outlook")
                        c_bull, c_bear = st.columns(2)
                        with c_bull: 
                            st.success(f"**Bull Case:** {data['long_term_outlook']['bull_case']}")
                        with c_bear:
                            st.error(f"**Bear Case:** {data['long_term_outlook']['bear_case']}")

                    with t_ind:
                        ind = data.get('industry_overview', {})
                        st.subheader("🌏 Industry Landscape")
                        st.markdown(ind.get('industry_landscape', '-'))
                        
                        st.markdown("### 🔮 Sector Outlook")
                        st.info(ind.get('sector_outlook', '-'))
                        
                        c_d, c_m = st.columns(2)
                        with c_d:
                            st.subheader("🚀 Growth Drivers")
                            for d in ind.get('growth_drivers', []):
                                st.success(f"📈 {d}")
                        with c_m:
                            st.subheader("🍰 Market Share")
                            st.markdown(ind.get('market_share_analysis', '-'))

                    with t_mgmt:
                        mgmt = data['management_analysis']
                        st.subheader(f"CEO: {mgmt['ceo_name']}")
                        st.info(f"**Capability:** {mgmt['ceo_capability_finding']}")
                        st.write(f"**Integrity:** {mgmt['management_integrity']}")
                        st.write(f"**Vision:** {mgmt['strategy_vision']}")
                        
                        st.divider()
                        moat = data['moat_analysis']
                        st.metric("Moat Level", moat['moat_level'])
                        st.write(f"**Source:** {moat['moat_source']}")
                        st.caption(f"Durability: {moat['moat_durability']}")

                    with t_fin:
                        fin = data['financial_structure_health']
                        st.info(f"**Balance Sheet:** {fin['balance_sheet_status']}")
                        st.info(f"**Cash Flow:** {fin['cash_flow_status']}")
                        st.info(f"**Profitability:** {fin['profitability_trend']}")
                        
                    with t_comp:
                        comp = data['competitive_landscape']
                        st.subheader("Market Position")
                        st.write(comp['market_position_rank'])
                        
                        st.subheader("Intensity")
                        st.markdown(comp['competition_intensity']) # Markdown wraps long text
                        
                        st.write("**Direct Competitors:**")
                        st.write(", ".join(comp['direct_competitors']))
                    
                    st.divider()
                    

                    

                        


                except json.JSONDecodeError:
                    st.error("Error parsing AI response. The model might have failed to return valid JSON.")
                    with st.expander("Raw Output"):
                        st.code(response.text)
                except Exception as e:
                    st.error(f"An error occurred: {str(e)}")
                    st.error("Make sure your API Key is valid and supports the selected model.")
        except Exception as e:
            st.error(f"Configuration Error: {str(e)}")


def page_glossary():
    st.markdown(f"<h1 style='text-align: center;'>{get_text('glossary_title')}</h1>", unsafe_allow_html=True)
    lang = st.session_state.get('lang', 'EN')

    tab1, tab2, tab3 = st.tabs([get_text('tab_settings'), get_text('tab_metrics'), get_text('tab_lynch')])

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



def page_home():
    left_co, cent_co,last_co = st.columns(3)
    with cent_co:
        st.image("stockdeck.png")


    st.subheader(get_text('home_welcome'))
    st.info(get_text('home_intro'))
    
    st.markdown("---")
    
    # Workflow 1: Single Stock
    st.markdown(get_text('workflow_single'))
    st.caption(get_text('workflow_single_desc'))
    
    c1, c2, c3 = st.columns(3)
    with c1:
        st.success(get_text('feat_qscan'))
    with c2:
        st.warning(get_text('feat_qai'))
    with c3:
        st.error(get_text('feat_qfin'))
        
    st.markdown("---")
    
    # Workflow 2: Portfolio
    st.markdown(get_text('workflow_port'))
    st.caption(get_text('workflow_port_desc'))
    
    c4, c5 = st.columns(2)
    with c4:
        st.success(get_text('feat_qwealth'))
    with c5:
        st.info(get_text('feat_qhealth'))
    
    st.markdown("---")
    st.info(get_text('about_desc'))


def page_scanner():
    st.markdown(f"<h1 style='text-align: center;'>{get_text('qscan_title')}</h1>", unsafe_allow_html=True)

    # NEW: Market Dashboard
    render_market_dashboard()


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
             val_pe = st.slider(get_text('max_pe'), 5.0, 500.0, float(t_pe))
             val_peg = st.slider(get_text('max_peg'), 0.1, 10.0, float(t_peg))
             val_evebitda = st.slider(get_text('max_evebitda'), 1.0, 50.0, float(t_evebitda))
             
        with c_prof:
             st.markdown(f"**{get_text('prof_header')}**")
             prof_roe = st.slider(get_text('min_roe'), 0, 50, int(t_roe*100)) / 100
             prof_margin = st.slider(get_text('min_margin'), 0, 50, int(t_margin*100)) / 100
             prof_div = st.slider(get_text('min_div'), 0, 15, int(t_div*100)) / 100
             if strategy == "Speculative Growth" or strategy == "Multibagger (High Risk)":
                 growth_min = st.slider(get_text('min_rev_growth'), 0, 100, int(t_rev_growth))
        
        with c_risk:
             st.markdown(f"**{get_text('risk_header')}**")
             risk_de = st.slider(get_text('max_de'), 0, 500, int(t_de), step=10)
             
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
    debug_container = st.expander(get_text('debug_logs'), expanded=False)

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
            
            # --- STAGE 2: Financial Analysis ---
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
            "Fit_Score": st.column_config.ProgressColumn(get_text('score_label'), format="%d", min_value=0, max_value=100),
            "Symbol": get_text('ticker_label'), 
            "Price": st.column_config.NumberColumn(get_text('price_label'), format=currency_fmt),
            "Fair_Value": st.column_config.NumberColumn("Fair Value", format=currency_fmt),
            "Margin_Safety": st.column_config.NumberColumn("Safety", format="%.1f%%"),
            "Rev_Growth": st.column_config.NumberColumn(get_text('rev_cagr_label'), format="%.1f%%"),
            "Div_Yield": st.column_config.NumberColumn(get_text('yield_label'), format="%.2f%%"),
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
        st.markdown(get_text('historical_chart_title'))
        if 'Symbol' in final_df.columns:
             sel = st.selectbox(get_text('select_stock_view'), final_df['Symbol'].unique())
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
    st.markdown(f"<h1 style='text-align: center;'>{get_text('aifolio_title')}</h1>", unsafe_allow_html=True)

    st.markdown("---")

    # --- INPUT FORM ---
    with st.form("aifolio_form"):
        st.subheader(get_text('ai_form_header'))
        
        c1, c2 = st.columns(2)
        with c1:
            target = st.number_input(get_text('f_target'), min_value=0, value=1000000, step=100000)
            horizon = st.number_input(get_text('f_horizon'), min_value=1, value=10, step=1)
            objective = st.text_input(get_text('f_objective'), value="Retirement / Wealth Accumulation")
            capital = st.number_input(get_text('f_capital'), min_value=0, value=100000, step=10000)
            dca = st.number_input(get_text('f_dca'), min_value=0, value=5000, step=1000)
            
        with c2:
            risk_tol = st.slider(get_text('f_risk'), 0, 100, 20, help="If the port drops this much, I will start to panic.")
            experience = st.selectbox(get_text('f_exp'), ["Beginner (0-2 Years)", "Intermediate (2-5 Years)", "Advanced (5+ Years)", "Pro"])
            liquid = st.radio(get_text('f_liquid'), ["Yes, I'm safe.", "No, this is all I have."])
            constraints = st.text_area(get_text('f_constraint'), placeholder="e.g. No Crypto, Focus on US Tech, ESG only...", height=100)
        
        submitted = st.form_submit_button(get_text('gen_plan_btn'), type="primary", use_container_width=True)

    # --- AI GENERATION LOGIC ---
    if submitted:
        # --- QUOTA CHECK ---
        user_id = st.session_state.get('username')
        allowed, msg, count, limit = auth_mongo.check_quota(user_id, 'wealth')
        if not allowed:
            st.error(msg)
            return
        
        auth_mongo.increment_quota(user_id, 'wealth')
        st.toast(f"Usage: {count+1}/{limit}", icon="🎫")

        # Secure API Key Check
        if 'GEMINI_API_KEY' not in st.secrets:
             st.error("🚨 Missing API Key in `.streamlit/secrets.toml`")
             return
             
        api_key = st.secrets['GEMINI_API_KEY']
        genai.configure(api_key=api_key)
        
        status_box = st.status(get_text('ai_thinking'), expanded=True)
        
        try:
            model = genai.GenerativeModel("models/gemini-3-flash-preview")
            
            # Construct Prompt
            prompt = f"""
            Act as a World-Class Asset Manager (like Ray Dalio or Warren Buffett).
            Your client has provided the following profile:
            
            - **Goal**: Target {target:.2f} in {horizon} Years.
            - **Objective**: {objective}
            - **Current Capital**: {capital:.2f}
            - **Monthly DCA**: {dca:.2f}
            - **Risk Tolerance (Max Drawdown)**: -{risk_tol}%
            - **Experience**: {experience}
            - **Liquidity Status**: {liquid}
            - **Constraints/Preferences**: {constraints}
            
            **INVESTMENT FRAMEWORK (Must Guide Selection):**
            1. **Mega Trend**: Prioritize "Sunrise" industries (AI, Healthcare, Green Energy) over "Sunset" ones (unless Deep Value).
            2. **Growth Driver**: Look for companies with a "New S-Curve" or new revenue engines.
            3. **Moat**: Prefer "Blue Ocean" or strong pricing power.
            4. **Macro**: Consider the economic cycle (Inflation/Rates). 

            **TASK:**
            1. Analyze this profile using "Chain of Thought" reasoning.
            2. Design a portfolio allocation (Stocks/Asset Classes) regarding the Framework above.
            3. Select specific TICKERS (US or Thai mostly, unless specified otherwise). IMPORTANT: For Thai stocks, YOU MUST append ".BK" (e.g., PTT.BK, CPALL.BK, ADVANC.BK). For US stocks, use standard tickers (e.g. AAPL, TSLA). 
            4. Provide specific advice.

            **OUTPUT FORMAT:**
            Strictly JSON. No Markdown Code blocks.
            
            {{
              "analysis": {{
                "risk_profile_assessment": "String",
                "strategy_name": "String (e.g. Aggressive Growth)",
                "expected_return_cagr": "String (estimated %)",
                "advice_summary": "String (2-3 paragraphs of professional advice)"
              }},
              "portfolio": [
                {{ "ticker": "SPY", "name": "S&P 500 ETF", "asset_class": "Equity", "weight_percent": 40, "rationale": "Core Foundation (Mega Trend: US Econ)" }},
                {{ "ticker": "AAPL", "name": "Apple Inc.", "asset_class": "Equity", "weight_percent": 10, "rationale": "Growth Kicker (New S-Curve: Services)" }}
                ... (Sum of weight_percent MUST be 100)
              ]
            }}
            
             Response Language: {st.session_state.get('lang', 'EN')} (Thai if TH selected, English if EN selected).
            """
            
            
            generation_config = genai.types.GenerationConfig(
                temperature=0.2, # Slightly higher for creativity in advice
                top_p=0.95,
                top_k=40,
                max_output_tokens=8192,
            )

            response = model.generate_content(prompt, generation_config=generation_config)
            clean_json = response.text.replace("```json", "").replace("```", "").strip()
            plan = json.loads(clean_json)
            
            status_box.update(label="✅ Analysis Complete!", state="complete")
            
            # --- AUTO SAVE PORTFOLIO ---
            user_id = st.session_state.get('username')
            if user_id:
                auth_mongo.save_portfolio(user_id, plan)
                st.toast("Portfolio Saved to Profile!", icon="💾")

            
            # --- RENDER RESULTS ---
            ana = plan['analysis']
            st.header(f"🎯 Strategy: {ana['strategy_name']}")
            
            # 1. Analysis Block
            with st.container():
                k1, k2, k3 = st.columns(3)
                k1.info(f"**Risk Profile**: {ana['risk_profile_assessment']}")
                k2.success(f"**Est. CAGR**: {ana.get('expected_return_cagr', 'N/A')}")
                k3.warning(f"**Max Drawdown Limit**: -{risk_tol}%")
                
                st.write(f"### 💡 Professional Advice")
                st.write(ana['advice_summary'])
                
            st.markdown("---")
            
            # 2. Allocation
            st.subheader(get_text('alloc_header'))
            
            df_port = pd.DataFrame(plan['portfolio'])
            
            c_chart, c_table = st.columns([1, 1])
            
            with c_chart:
                # Altair Donut
                base = alt.Chart(df_port).encode(theta=alt.Theta("weight_percent", stack=True))
                pie = base.mark_arc(outerRadius=120, innerRadius=60).encode(
                    color=alt.Color("asset_class"),
                    order=alt.Order("weight_percent", sort="descending"),
                    tooltip=["ticker", "name", "weight_percent", "asset_class"]
                )
                text = base.mark_text(radius=140).encode(
                    text=alt.Text("weight_percent", format=".1f"),
                    order=alt.Order("weight_percent", sort="descending"), 
                    color=alt.value("white")  
                )
                st.altair_chart(pie + text, use_container_width=True)
                
            with c_table:
                st.dataframe(
                    df_port[['ticker', 'name', 'weight_percent', 'rationale']],
                    column_config={
                        "weight_percent": st.column_config.NumberColumn("Weight %", format="%.1f%%"),
                        "rationale": st.column_config.TextColumn("Why?", width="medium")
                    },
                    hide_index=True,
                    use_container_width=True
                )
                
            # Disclaimer
            st.caption("⚠️ **Disclaimer**: This portfolio is generated by AI for educational purposes only. It does not constitute financial advice. Please do your own research before investing.")

        except Exception as e:
            status_box.update(label="❌ Error generating plan", state="error")
            st.error(f"AI Error: {str(e)}")










 
def page_health():
    st.markdown(f"<h1 style='text-align: center;'>{get_text('health_check_title')}</h1>", unsafe_allow_html=True)
    st.markdown("---")

    # --- 1. INPUT SECTION ---
    st.subheader("1. 📋 Portfolio Input")
    st.info("Enter your portfolio details below for a comprehensive AI Health Check.")

    # Initialize data if not needed
    if 'health_data' not in st.session_state:
        st.session_state['health_data'] = pd.DataFrame(
            [{"Symbol": "AAPL", "AvailVol": 100, "Avg": 150.0, "Market": 175.0, "U.PL": 16.6}],
            columns=["Symbol", "AvailVol", "Avg", "Market", "U.PL"]
        )

    edited_df = st.data_editor(
        st.session_state['health_data'],
        num_rows="dynamic",
        use_container_width=True,
        key="health_editor",
        column_config={
            "Symbol": st.column_config.TextColumn("Symbol (Ticker)", help="Stock Symbol (e.g. AAPL, PTT.BK)", required=True),
            "AvailVol": st.column_config.NumberColumn("Vol", min_value=1, format="%d", default=100),
            "Avg": st.column_config.NumberColumn("Avg Cost", min_value=0.0, format="%.2f", default=0.0),
            "Market": st.column_config.NumberColumn("Market Price", min_value=0.0, format="%.2f", default=0.0),
            "U.PL": st.column_config.NumberColumn("% Unrealized P/L", format="%.2f%%", disabled=True)
        }
    )

    # --- Auto-Calculate %U.PL and Update State ---
    needs_rerun = False
    
    if not edited_df.empty:
        # Cast to numeric safely (handle strings/None from new rows)
        for col in ['Avg', 'Market']:
            edited_df[col] = pd.to_numeric(edited_df[col], errors='coerce').fillna(0.0)
            
        # Calculate U.PL
        # Logic: (Market - Avg) / Avg * 100. If Avg is 0, result is 0.
        def calc_upl(row):
            if row['Avg'] > 0:
                return ((row['Market'] - row['Avg']) / row['Avg']) * 100
            return 0.0

        new_upl = edited_df.apply(calc_upl, axis=1)
        
        # Compare with existing U.PL (handle potential NaNs in existing)
        current_upl = pd.to_numeric(edited_df['U.PL'], errors='coerce').fillna(0.0)
        
        if not current_upl.equals(new_upl):
            # Check deviation
            diff = (current_upl - new_upl).abs()
            if (diff > 0.05).any(): # 0.05% tolerance
                edited_df['U.PL'] = new_upl
                st.session_state['health_data'] = edited_df
                needs_rerun = True

    if needs_rerun:
        st.rerun()

    # --- 2. EXECUTION ---
    c_btn, c_lang = st.columns([3, 1])
    with c_lang:
        health_lang = st.radio("Response Language", ["English", "Thai"], horizontal=True, label_visibility="collapsed")
        
        # --- LOAD HISTORY BUTTON ---
        user_id = st.session_state.get('username')
        if user_id:
            with st.popover("📂 Load Saved Portfolio"):
                saved_ports = auth_mongo.get_user_portfolios(user_id)
                if not saved_ports:
                    st.info("No saved portfolios.")
                else:
                    for p in saved_ports:
                        if st.button(f"{p['name']} ({len(p.get('data',{}).get('portfolio',[]))} stocks)", key=p['_id']):
                            # Convert JSON portfolio to DF structure for HealthDeck
                            # HealthDeck expects: Ticker, Avg (Price), Market (Price), Qty (optional, implied 1?)
                            # Saved portfolio: ticker, name, weight_percent... no entry price/market price usually?
                            # Wait, AIfolio generates 'Allocation', not a real position with cost basis.
                            # So we can only prepopulate 'Ticker' and 'Market Price' (current). 'Avg Price' will be 0.
                            
                            new_data = []
                            for asset in p.get('data', {}).get('portfolio', []):
                                if asset.get('asset_class') == 'Equity': # Only stocks
                                    new_data.append({
                                        'Ticker': asset['ticker'],
                                        'Avg': 0.0, # Unknown
                                        'Market': 0.0, # Unknown, user fill, or we fetch live? Let's leave 0
                                        'U.PL': 0.0,
                                        'Weight': asset['weight_percent']
                                    })
                            
                            st.session_state['health_data'] = pd.DataFrame(new_data)
                            st.rerun()

    with c_btn:
        run_btn = st.button("🏥 Run Health Check (AI)", type="primary", use_container_width=True)

    if run_btn:
        # --- QUOTA CHECK ---
        user_id = st.session_state.get('username')
        allowed, msg, count, limit = auth_mongo.check_quota(user_id, 'health')
        if not allowed:
            st.error(msg)
            return
        
        auth_mongo.increment_quota(user_id, 'health')
        st.toast(f"Usage: {count+1}/{limit}", icon="🎫")
        if edited_df.empty:
            st.error("Please add at least one stock.")
            return

        # Secure API Key Check
        if 'GEMINI_API_KEY' not in st.secrets:
             st.error("🚨 Missing API Key in `.streamlit/secrets.toml`")
             return
             
        api_key = st.secrets['GEMINI_API_KEY']
        genai.configure(api_key=api_key)
        
        status_box = st.status("🧠 " + get_text('ai_thinking'), expanded=True)
        
        try:
            model = genai.GenerativeModel("models/gemini-3-flash-preview") # optimized for speed/cost, or use pro if needed
            
            # Construct Prompt
            portfolio_str = edited_df.to_json(orient="records")
            
            prompt = f"""
            Act as a Global Macro Strategist and Fundamental Investor (Chain of Thought Analysis).
            
            Analyze the following portfolio for "Health Assessment" based on the future 10-20 year outlook.
            Be brutally honest, unbiased, and direct. Do not flatter.

            **PORTFOLIO DATA:**
            {portfolio_str}

            **ANALYSIS FRAMEWORK (Must Apply to EACH Stock):**

            1. **Dimension 1: Mega Trend Alignment (Swimming with or against the tide?)**
               - **Sunset vs Sunrise**: Will demand decrease or increase? (e.g. Fossil Fuels = Sunset, AI/Healthcare = Sunrise).
               - **Disruption Check**: Will AI/Robot/Blockchain kill this business or boost it?
               - *Red Flag*: Fighting the trend.

            2. **Dimension 2: Missing Growth Driver (Engine Status)**
               - **Old S-Curve vs New S-Curve**: Is the old growth engine exhausted? (e.g. saturated expansion).
               - **New Revenue %**: Is there a new significant revenue stream (>5%) or just cost-cutting?
               - *Red Flag*: Stagnant revenue + focus only on cost cutting.

            3. **Dimension 3: Market Opportunity & Moat**
               - **Red vs Blue Ocean**: Price war (Commoditized) or Pricing Power (Brand/Tech)?
               - **TAM (Total Addressable Market)**: Is market share already maxed out (70-80%)?
            
            4. **Country/Macro Context (If applicable, e.g. for .BK stocks check Thailand context):**
               - **Economic Engine**: Old Economy (Low Growth, Cyclical) vs New Economy (High Growth).
               - **Demographic Destiny**: Aging Society (De-rating P/E) vs Young Society (Premium P/E).
               - **Zombie Index Check**: Has the country index EPS grown in 5 years?
               - **Fund Flow**: Currency stability and Foreign flow outlook.

            **TASK:**
            1. Analyze every stock using the framework above.
            2. Assign a **Portfolio Health Score** (0-100).
            3. Provide a **Verdict** for EACH stock: "SELL", "HOLD", or "ACCUMULATE".
               - Suggest if they should convert to Cash to reinvest in better markets.
            
            **OUTPUT FORMAT:**
            Strictly JSON.
            {{
                "portfolio_score": 75,
                "portfolio_summary": "Overall assessment of the portfolio...",
                "stocks": [
                    {{
                        "symbol": "AAPL",
                        "mega_trend": "Sunrise (AI/Services)...",
                        "growth_driver": "New S-Curve in Services/Wearables...",
                        "moat_opportunity": "Blue Ocean in ecosystem...",
                        "macro_context": "US Economy strong...",
                        "verdict": "HOLD",
                        "action_reason": "Strong moat but high valuation..."
                    }},
                    ...
                ]
            }}
            Response Language: {health_lang}
            """
            
            
            generation_config = genai.types.GenerationConfig(
                temperature=0.1,
                top_p=0.95,
                top_k=40,
                max_output_tokens=8192,
            )
            
            response = model.generate_content(prompt, generation_config=generation_config)
            clean_json = response.text.replace("```json", "").replace("```", "").strip()
            result = json.loads(clean_json)
            
            status_box.update(label="✅ Diagnosis Complete!", state="complete")
            
            # --- AUTO SAVE HEALTH CHECK ---
            user_id = st.session_state.get('username')
            if user_id:
                # We save the raw input DF (structure) + the AI Analysis text/score
                auth_mongo.save_health_check(user_id, edited_df, result.get('diagnosis_summary', 'No Summary'), result.get('portfolio_gpa', 'N/A'))
                st.toast("Health Check Saved to Profile!", icon="💾")

            
            # --- 3. RENDER RESULTS ---
            
            # Score
            score = result.get('portfolio_score', 0)
            st.metric("Portfolio Health Score", f"{score}/100")
            st.progress(score / 100)
            
            st.write(f"### 📝 {get_text('backtest_summary')}")
            st.info(result.get('portfolio_summary', ''))
            
            st.markdown("---")
            st.subheader("🔬 Indivdual Stock Diagnosis")
            
            for item in result.get('stocks', []):
                with st.expander(f"**{item['symbol']}** - {item['verdict']}", expanded=True):
                    c1, c2 = st.columns([1, 2])
                    with c1:
                        if item['verdict'] == "SELL":
                            st.error(f"**VERDICT: {item['verdict']}**")
                        elif item['verdict'] == "ACCUMULATE":
                            st.success(f"**VERDICT: {item['verdict']}**")
                        else:
                            st.warning(f"**VERDICT: {item['verdict']}**")
                            
                        st.write(f"**Reason:** {item['action_reason']}")
                        
                    with c2:
                        st.write(f"**🌊 Mega Trend:** {item['mega_trend']}")
                        st.write(f"**🚀 Growth Driver:** {item['growth_driver']}")
                        st.write(f"**🏰 Moat/Market:** {item['moat_opportunity']}")
                        st.write(f"**🌍 Macro:** {item['macro_context']}")

        except Exception as e:
            status_box.update(label="❌ Error", state="error")
            st.error(f"Analysis Failed: {str(e)}")


# ---------------------------------------------------------
# ---------------------------------------------------------
# ---------------------------------------------------------
# PAGE: PROFILES
# ---------------------------------------------------------
def page_profile():
    st.markdown("## 👤 My Profile")
    
    # --- HEADER ---
    c1, c2 = st.columns([1, 4])
    with c1:
        # Placeholder Avatar
        st.write("")
        st.markdown("<div style='text-align:center; font_size: 60px;'>👤</div>", unsafe_allow_html=True) 
    with c2:
        st.write(f"### {st.session_state.get('user_name', 'User')}")
        st.caption(f"Member Tier: **{st.session_state.get('tier','standard').upper()}**")
        if st.button("🚪 Logout", key="profile_logout"):
            st.session_state.clear()
            st.rerun()

    st.markdown("---")

    tab_hist, tab_acc = st.tabs(["📜 History", "⚙️ Account Settings"])

    # --- HISTORY TAB ---
    with tab_hist:
        h_tab1, h_tab2 = st.tabs(["Wealth Portfolios", "Health Reports"])
        
        # 1. Wealth History
        with h_tab1:
            st.subheader("Saved AI Portfolios")
            user_id = st.session_state.get('username')
            if user_id:
                ports = auth_mongo.get_user_portfolios(user_id)
                if not ports:
                    st.info("No saved portfolios yet.")
                else:
                    for p in ports:
                        with st.expander(f"📁 {p['name']} ({p['created_at'].strftime('%Y-%m-%d %H:%M')})"):
                            # Simple View
                            st.json(p.get('data', {}).get('analysis', {}).get('advice_summary', 'No summary'))
                            st.write("**Allocations:**")
                            st.dataframe(pd.DataFrame(p.get('data', {}).get('portfolio', [])))

        # 2. Health History
        with h_tab2:
            st.subheader("Past Health Checks")
            if user_id:
                checks = auth_mongo.get_health_history(user_id)
                if not checks:
                    st.info("No health checks run yet.")
                else:
                    for c in checks:
                        gpa_color = "red"
                        if str(c.get('gpa')).startswith("A"): gpa_color = "green"
                        elif str(c.get('gpa')).startswith("B"): gpa_color = "orange"
                        
                        with st.expander(f"🩺 {c['name']} - GPA: :{gpa_color}[{c.get('gpa')}]"):
                            st.write(c.get('analysis'))
                            st.caption("Input Data:")
                            st.dataframe(pd.DataFrame(c.get('portfolio_json')))

    # --- SETTINGS TAB ---
    with tab_acc:
        st.subheader("Change Password")
        with st.form("pwd_change_form"):
            curr_pass = st.text_input("Current Password", type="password")
            new_pass1 = st.text_input("New Password", type="password")
            new_pass2 = st.text_input("Confirm New Password", type="password")
            
            if st.form_submit_button("Update Password"):
                if new_pass1 != new_pass2:
                    st.error("New passwords do not match.")
                else:
                    success, msg = auth_mongo.change_password(st.session_state.get('username'), curr_pass, new_pass1)
                    if success: st.success(msg)
                    else: st.error(msg)

if __name__ == "__main__":
    inject_custom_css() 
    
    # Init Auth State
    if 'authenticated' not in st.session_state:
        st.session_state['authenticated'] = False
        st.session_state['tier'] = 'standard'
        
    if 'tier' not in st.session_state:
        st.session_state['tier'] = 'standard'
    
    # --- LANGUAGE SETUP (Public) ---
    if 'lang_choice_key' in st.session_state:
        pass 
    current_lang_sel = st.session_state.get('lang_choice_key', "English (EN)")
    st.session_state['lang'] = 'EN' if "English" in current_lang_sel else 'TH'

    # --- TABS (Public Navigation) ---
    tab_names = [
        get_text('nav_home'),
        get_text('nav_scanner') + (f" 🔒" if not st.session_state['authenticated'] else ""),
        get_text('nav_ai') + (f" 🔒" if not st.session_state['authenticated'] else ""),
        get_text('nav_single') + (f" 🔒" if not st.session_state['authenticated'] else ""),
        get_text('aifolio_title') + (f" 🔒" if not st.session_state['authenticated'] else ""),
        get_text('nav_health') + (f" 🔒" if not st.session_state['authenticated'] else ""),
        get_text('nav_glossary')
    ]
    
    # Add Profile Tab if Authenticated
    if st.session_state['authenticated']:
        tab_names.append("👤 Profile")
    
    tabs = st.tabs(tab_names) 

    # --- TOP BAR ---
    c_logo, c_lang = st.columns([8, 2])
    with c_logo:
        pass # Clean look
    with c_lang:
        lang_choice = st.radio(get_text('lang_label'), ["English (EN)", "Thai (TH)"], horizontal=True, label_visibility="collapsed", key="lang_choice_key")

    # --- SIDEBAR (Login Only) ---
    with st.sidebar:
        st.divider()
        if not st.session_state['authenticated']:
            st.info("Member Login")
            with st.form("sidebar_login"):
                username = st.text_input("Username")
                password = st.text_input("Password", type="password")
                if st.form_submit_button("Log In"):
                    success, name, tier = auth_mongo.check_login(username, password)
                    if success:
                        st.session_state['authenticated'] = True
                        st.session_state['user_name'] = name
                        st.session_state['username'] = username # Store ID for DB calls
                        st.session_state['tier'] = tier
                        st.success("Login Success!")
                        st.rerun()
                    else:
                        st.error("Invalid Credentials")
            
            with st.expander("New User? Sign Up"):
                with st.form("sidebar_signup"):
                    new_user = st.text_input("Username")
                    new_name = st.text_input("Display Name")
                    new_pass = st.text_input("Password", type="password")
                    if st.form_submit_button("Sign Up"):
                        success, msg = auth_mongo.sign_up(new_user, new_pass, new_name)
                        if success: st.success(msg)
                        else: st.error(msg)
        else:
            # Minimized Sidebar for Logged In Users
            st.success(f"Logged in as {st.session_state.get('user_name')}")
            st.caption(f"Tier: {st.session_state.get('tier', 'Standard').upper()}")
            st.info("Go to 'Profile' tab for settings & history.")

        st.divider()
        st.caption("🔧 System Tools")
        if st.button("🗑️ Clear Cache", use_container_width=True):
            st.cache_data.clear()
            st.session_state.clear()
            st.rerun()

    # --- HELPER: LOCKED OVERLAY ---
    def render_locked_overlay(feature_name):
        st.warning(f"🔒 **Login Required** to access {feature_name}")
        st.info("Please Log In or Sign Up in the Sidebar to unlock professional tools.")
        st.markdown("---")
        st.markdown("<div style='filter: blur(4px); pointer-events: none; opacity: 0.4;'>", unsafe_allow_html=True)
        return True

    # --- PAGES ---
    
    # Map tabs to content
    with tabs[0]: page_home()
    
    with tabs[1]:
        if not st.session_state['authenticated']:
            render_locked_overlay("Scanner")
            page_scanner()
            st.markdown("</div>", unsafe_allow_html=True)
        else: page_scanner()

    with tabs[2]:
        if not st.session_state['authenticated']:
             render_locked_overlay("AI Analysis")
             st.markdown("</div>", unsafe_allow_html=True)
        else: page_ai_analysis()
             
    with tabs[3]:
        if not st.session_state['authenticated']:
            render_locked_overlay("Deep Dive")
            page_single_stock()
            st.markdown("</div>", unsafe_allow_html=True)
        else: page_single_stock()

    with tabs[4]:
        if not st.session_state['authenticated']:
            render_locked_overlay("Wealth")
            st.markdown("</div>", unsafe_allow_html=True)
        else: page_portfolio()
            
    with tabs[5]:
        if not st.session_state['authenticated']:
             render_locked_overlay("HealthDeck")
             st.markdown("</div>", unsafe_allow_html=True)
        else: page_health()
            
    with tabs[6]:
        page_glossary()

    # Profile Tab (Index 7)
    if st.session_state['authenticated'] and len(tabs) > 7:
        with tabs[7]:
            page_profile()

        
