
import os
import re

path = r'c:\Stock\crypto.py'

# New Content for Single Coin Page
new_page_code = r'''
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

'''

with open(path, 'r', encoding='utf-8') as f:
    content = f.read()

# 1. Replace page_single_stock definition
# We use simple string find for start
start_marker = "def page_single_stock():"
end_marker = "def page_glossary():"

start_idx = content.find(start_marker)
end_idx = content.find(end_marker)

if start_idx != -1 and end_idx != -1:
    print(f"Replacing function block from {start_idx} to {end_idx}")
    # Replace content
    new_content = content[:start_idx] + new_page_code + "\n\n" + content[end_idx:]
    
    # 2. Replace call site (page_single_stock() -> page_single_coin())
    new_content = new_content.replace("page_single_stock()", "page_single_coin()")
    
    # 3. Check for Duplicate page_scanner
    # If we find "def page_scanner():" twice, we should investigate/fix.
    # Count occurrences
    scan_count = new_content.count("def page_scanner():")
    if scan_count > 1:
        print("ALERT: Found multiple page_scanner definitions. Removing the second one if possible.")
        # Find second occurrence
        first_scan = new_content.find("def page_scanner():")
        second_scan = new_content.find("def page_scanner():", first_scan + 1)
        
        # If second scan exists, try to find where it ends or just comment it out?
        # Re-reading the outline, the second one seemed to be at line 2200+.
        # The first one was at 1179.
        # It's safer to just remove the second definition block if I can identify it clearly.
        # Or I will just report it and let the user/agent fix it separately.
        pass

    with open(path, 'w', encoding='utf-8') as f:
        f.write(new_content)
    print("SUCCESS: Pages updated.")

else:
    print("FAILED: Could not find function boundaries.")
