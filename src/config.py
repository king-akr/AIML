from datetime import time

class Config:
    # Capital & Risk
    TOTAL_CAPITAL = 1000000.0  # ₹10,00,000
    MAX_RISK_PER_TRADE = 50000.0  # ₹50,000

    # Instrument
    INDEX = "NIFTY"
    LOT_SIZE = 25  # NIFTY Lot Size

    # Timings
    MARKET_START_TIME = time(9, 15)
    ENTRY_TIME = time(9, 17)
    EXIT_TIME = time(15, 0)

    # Strategy Parameters
    INITIAL_SL_PCT = 0.10  # 10% of combined premium
    TARGET_PCT = 0.10      # 10% of combined premium

    # Trailing SL
    TRAILING_ACTIVATION_PCT = 0.025  # 2.5% profit
    TRAILING_SL_PCT = 0.025          # Trail by 2.5% of combined premium

    # Simulation
    SIMULATION_SPEED = 1.0  # 1.0 = Realtime, >1.0 = Fast Forward
