import streamlit as st
import time
import pandas as pd
from trade_algo.market_data import MockMarketData
from trade_algo.broker import MockBroker
from trade_algo.strategy import ShortStraddleStrategy
from trade_algo.config import TOTAL_CAPITAL

st.set_page_config(page_title="Intraday Algo Dashboard", layout="wide")

st.title("Intraday Short Volatility Algo")

# Initialize Session State
if 'market_data' not in st.session_state:
    st.session_state.market_data = None
if 'broker' not in st.session_state:
    st.session_state.broker = None
if 'strategy' not in st.session_state:
    st.session_state.strategy = None
if 'mtm_history' not in st.session_state:
    st.session_state.mtm_history = []
if 'running' not in st.session_state:
    st.session_state.running = False

def init_system():
    st.session_state.market_data = MockMarketData()
    st.session_state.broker = MockBroker()
    st.session_state.strategy = ShortStraddleStrategy(st.session_state.market_data, st.session_state.broker)
    st.session_state.mtm_history = []
    st.session_state.running = True

# Sidebar
with st.sidebar:
    st.header("Controls")
    if st.button("Start / Reset Simulation"):
        init_system()

    speed = st.slider("Simulation Speed (Delay in sec)", 0.0, 1.0, 0.1)

# Main Dashboard
col1, col2, col3, col4 = st.columns(4)
placeholder_spot = col1.empty()
placeholder_pnl = col2.empty()
placeholder_status = col3.empty()
placeholder_premium = col4.empty()

chart_placeholder = st.empty()
log_placeholder = st.empty()

if st.session_state.running:
    md = st.session_state.market_data
    broker = st.session_state.broker
    strategy = st.session_state.strategy

    # Simulation Loop
    while st.session_state.running:
        # Update System
        md.update()
        strategy.run_tick()

        # Get Data
        current_time = md.get_current_time().strftime("%H:%M")
        spot = md.get_spot()
        status_data = strategy.get_status_data()

        # Calculate PnL (Realized + MTM)
        current_prices = {}
        if status_data['entry_strike']:
             ce_sym, pe_sym = strategy.get_symbols()
             current_prices[ce_sym] = md.get_option_price(status_data['entry_strike'], 'CE')
             current_prices[pe_sym] = md.get_option_price(status_data['entry_strike'], 'PE')

        total_pnl = broker.get_total_pnl(current_prices)
        st.session_state.mtm_history.append({"Time": current_time, "PnL": total_pnl})

        # Update Metrics
        placeholder_spot.metric("Time / Spot", f"{current_time}", f"{spot:.2f}")
        placeholder_pnl.metric("Total P&L", f"{total_pnl:.2f}")
        placeholder_status.metric("Status", status_data['status'], status_data.get('exit_reason', ''))

        comb_prem = status_data.get('current_combined', 0)
        entry_prem = status_data.get('entry_combined', 0)
        delta_prem = comb_prem - entry_prem if entry_prem else 0
        placeholder_premium.metric("Combined Premium", f"{comb_prem:.2f}", f"{delta_prem:.2f}" if entry_prem else "")

        # Update Chart
        df = pd.DataFrame(st.session_state.mtm_history)
        if not df.empty:
            chart_placeholder.line_chart(df.set_index("Time")['PnL'])

        # Update Logs
        if strategy.logs:
            # Using text_area in a loop can cause ID conflicts. Using code block for logs.
            log_content = "\n".join(reversed(strategy.logs))
            log_placeholder.text(log_content)

        # Stop if Exited or End of Day
        if status_data['status'] == "EXITED":
            st.session_state.running = False
            st.success(f"Simulation Ended. Reason: {status_data['exit_reason']}")
            break

        time.sleep(speed)
