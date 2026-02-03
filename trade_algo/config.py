# Strategy Configuration

# Capital & Risk
TOTAL_CAPITAL = 1000000.0
FIXED_RISK_PER_TRADE = 5000.0

# Time Settings (24h format strings)
START_TIME = "09:15"
ENTRY_TIME = "09:17"
EXIT_TIME = "15:00"

# Risk Management Parameters
INITIAL_SL_PCT = 0.10      # 10% of combined premium
TARGET_PCT = 0.10          # 10% of combined premium
TSL_ACTIVATION_PCT = 0.025 # 2.5% move in favor
TSL_PCT = 0.025            # Trail SL by 2.5%

# Market Configuration
INDEX_SYMBOL = "NIFTY"
LOT_SIZE = 50  # Example for Nifty
