# Intraday Short Volatility Trading Algorithm

This is a Python-based algorithmic trading system for an Intraday Short Straddle strategy on Indian Index Options (NIFTY). It includes a simulation environment with mock market data and a live dashboard.

## Assignment Overview

The goal was to build a system that:
- Executes a Short Straddle (Sell ATM Call & Put) at 09:17 AM.
- Manages risk with a fixed capital risk per trade.
- Implements Initial Stop Loss, Target, and Trailing Stop Loss (TSL).
- Provides a Live MTM Dashboard.

## Project Structure

- `trade_algo/`
    - `config.py`: Configuration parameters (Capital, Risk, Timings, etc).
    - `strategy.py`: Core logic for Entry, Risk Management, and Exit.
    - `market_data.py`: Mock data generator simulating Spot and Option prices.
    - `broker.py`: Mock broker handling orders, positions, and P&L.
    - `utils.py`: Helper functions.
- `app.py`: Streamlit dashboard application.
- `tests/`: Unit tests for the strategy logic.

## Logic Details

### Entry
- **Time**: 09:17 AM.
- **Instrument**: ATM Call and Put (Straddle).
- **Position Sizing**: Calculated based on a fixed risk of ₹5,000 and an Initial SL of 10% of Combined Premium.
  - `Quantity = 5000 / (Combined_Premium * 0.10)` (Rounded to Lot Size).

### Exit Conditions
1.  **Stop Loss**: If Combined Premium increases by 10% from Entry.
2.  **Target**: If Combined Premium decreases by 10% from Entry.
3.  **Trailing Stop Loss (TSL)**:
    - Activated when profit reaches 2.5% (Combined Premium drops 2.5%).
    - Once activated, SL is set to `Lowest_Premium_Seen + 2.5%`.
    - This locks in profits as the trade moves in favor.
4.  **Time Exit**: Square off at 03:00 PM (15:00).

## Installation

1.  Clone the repository.
2.  Install dependencies:
    ```bash
    pip install streamlit pandas pytest
    ```

## How to Run

1.  **Run the Dashboard**:
    ```bash
    streamlit run app.py
    ```
    This will open a web interface where you can:
    - Click **Start / Reset Simulation** to begin.
    - Adjust **Simulation Speed** to speed up the day.
    - View the Live MTM Chart, Spot Price, and Trade Logs.

2.  **Run Tests**:
    ```bash
    PYTHONPATH=. pytest tests/
    ```

## Simulation Note
Since this environment does not have access to live market APIs, `MockMarketData` is used to generate realistic random-walk price data for Nifty and its Options (including Theta decay logic).
