from datetime import datetime, time
import math
from typing import Dict, Any, Optional
from .config import Config
from .broker_interface import BrokerInterface

class ShortStraddleStrategy:
    def __init__(self, broker: BrokerInterface):
        self.broker = broker
        self.state = "WAITING" # WAITING, ENTERED, EXITED
        self.ce_symbol = None
        self.pe_symbol = None
        self.entry_price_combined = 0.0
        self.quantity = 0

        self.sl_price = 0.0
        self.target_price = 0.0
        self.trailing_active = False

        # Logging/Dashboard data
        self.last_run_time = None
        self.pnl = 0.0
        self.current_combined_premium = 0.0
        self.message = "Strategy Initialized"

    def run(self):
        current_time_dt = self.broker.get_current_time()
        current_time = current_time_dt.time()
        self.last_run_time = current_time_dt

        if self.state == "EXITED":
            self.message = "Trades Exited for the day."
            return

        # Time Exit
        if current_time >= Config.EXIT_TIME:
            if self.state == "ENTERED":
                self.exit_positions("Time Based Exit (03:00 PM)")
            return

        # Entry Logic
        if self.state == "WAITING":
            if current_time >= Config.ENTRY_TIME:
                self.execute_entry()

        # In-Trade Logic
        elif self.state == "ENTERED":
            self.check_exit_conditions()

    def execute_entry(self):
        atm_strike = self.broker.get_atm_strike()
        self.ce_symbol = f"{Config.INDEX}{atm_strike}CE"
        self.pe_symbol = f"{Config.INDEX}{atm_strike}PE"

        ce_ltp = self.broker.get_ltp(self.ce_symbol)
        pe_ltp = self.broker.get_ltp(self.pe_symbol)

        if ce_ltp <= 0 or pe_ltp <= 0:
            self.message = "Error: Invalid premiums, skipping entry."
            return

        combined_premium = ce_ltp + pe_ltp

        # Position Sizing
        # Risk = Qty * Combined_Premium * 10%
        # Qty = Max_Risk / (Combined_Premium * 0.10)
        risk_per_share = combined_premium * Config.INITIAL_SL_PCT
        calculated_qty = Config.MAX_RISK_PER_TRADE / risk_per_share

        # Round down to nearest lot size for safety (avoid exceeding risk)
        lots = math.floor(calculated_qty / Config.LOT_SIZE)
        if lots < 1: lots = 1 # Minimum 1 lot
        self.quantity = lots * Config.LOT_SIZE

        # Execute Orders
        self.broker.place_order(self.ce_symbol, self.quantity, "SELL")
        self.broker.place_order(self.pe_symbol, self.quantity, "SELL")

        self.entry_price_combined = combined_premium
        self.state = "ENTERED"

        # Set SL and Target
        # For Short Straddle:
        # Loss if Premium INCREASES.
        # SL Price = Entry + (Entry * 10%)
        # Target Price = Entry - (Entry * 10%)
        self.sl_price = self.entry_price_combined * (1 + Config.INITIAL_SL_PCT)
        self.target_price = self.entry_price_combined * (1 - Config.TARGET_PCT)

        self.message = f"Entered Straddle at {combined_premium:.2f}. Qty: {self.quantity}. SL: {self.sl_price:.2f}"

    def check_exit_conditions(self):
        ce_ltp = self.broker.get_ltp(self.ce_symbol)
        pe_ltp = self.broker.get_ltp(self.pe_symbol)
        self.current_combined_premium = ce_ltp + pe_ltp

        # MTM Calculation
        # Profit = (Entry - Current) * Qty
        self.pnl = (self.entry_price_combined - self.current_combined_premium) * self.quantity

        # Check SL (Price went UP)
        if self.current_combined_premium >= self.sl_price:
            self.exit_positions(f"Stop Loss Hit. Curr: {self.current_combined_premium:.2f} >= SL: {self.sl_price:.2f}")
            return

        # Check Target (Price went DOWN)
        if self.current_combined_premium <= self.target_price:
            self.exit_positions(f"Target Hit. Curr: {self.current_combined_premium:.2f} <= Tgt: {self.target_price:.2f}")
            return

        # Trailing SL Logic
        self.update_trailing_sl()

    def update_trailing_sl(self):
        # Activation: Profit >= 2.5%
        # Profit Points = Entry - Current
        profit_points = self.entry_price_combined - self.current_combined_premium
        activation_points = self.entry_price_combined * Config.TRAILING_ACTIVATION_PCT

        if profit_points >= activation_points:
            self.trailing_active = True

        if self.trailing_active:
            # Trail SL at 2.5% of combined premium (Entry base or Current base? Prompt says "combined premium")
            # Interpreted as: Gap = Entry_Premium * 0.025
            # New SL = Current + Gap
            gap = self.entry_price_combined * Config.TRAILING_SL_PCT
            new_sl = self.current_combined_premium + gap

            # Since we are short, SL is above current price.
            # We want to lower the SL as price drops.
            if new_sl < self.sl_price:
                self.sl_price = new_sl
                self.message = f"Trailing SL Updated to {self.sl_price:.2f}"

    def exit_positions(self, reason):
        self.broker.place_order(self.ce_symbol, self.quantity, "BUY")
        self.broker.place_order(self.pe_symbol, self.quantity, "BUY")
        self.state = "EXITED"
        self.message = f"Exited: {reason}"

    def get_status(self) -> Dict[str, Any]:
        return {
            "state": self.state,
            "time": self.last_run_time.strftime("%H:%M:%S") if self.last_run_time else "N/A",
            "pnl": self.pnl,
            "combined_premium": self.current_combined_premium,
            "entry_price": self.entry_price_combined,
            "sl": self.sl_price,
            "target": self.target_price,
            "message": self.message,
            "positions": f"{self.ce_symbol} + {self.pe_symbol}" if self.ce_symbol else "None"
        }
