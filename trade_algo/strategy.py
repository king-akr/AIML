import math
from .config import (
    ENTRY_TIME, EXIT_TIME, INITIAL_SL_PCT, TARGET_PCT,
    TSL_ACTIVATION_PCT, TSL_PCT, FIXED_RISK_PER_TRADE,
    LOT_SIZE, INDEX_SYMBOL
)
from .utils import is_later_or_equal, time_to_minutes

class ShortStraddleStrategy:
    def __init__(self, market_data, broker):
        self.md = market_data
        self.broker = broker

        self.status = "WAITING" # WAITING, ACTIVE, EXITED
        self.exit_reason = ""

        self.entry_strike = None
        self.quantity = 0

        self.entry_combined_premium = 0.0
        self.sl_price = 0.0
        self.target_price = 0.0

        self.lowest_premium = 0.0
        self.tsl_active = False

        self.logs = [] # List of log messages

    def log(self, message):
        timestamp = self.md.get_current_time().strftime("%H:%M:%S")
        self.logs.append(f"[{timestamp}] {message}")

    def get_symbols(self):
        if self.entry_strike:
            ce_symbol = f"{INDEX_SYMBOL}{self.entry_strike}CE"
            pe_symbol = f"{INDEX_SYMBOL}{self.entry_strike}PE"
            return ce_symbol, pe_symbol
        return None, None

    def run_tick(self):
        current_time = self.md.get_current_time().time()

        if self.status == "WAITING":
            if is_later_or_equal(current_time, ENTRY_TIME):
                self._enter_trade(current_time)

        elif self.status == "ACTIVE":
            self._monitor_trade(current_time)

            if is_later_or_equal(current_time, EXIT_TIME):
                self._exit_trade("Time Exit")

    def _enter_trade(self, current_time):
        spot = self.md.get_spot()
        self.entry_strike = self.md.get_atm_strike()

        ce_symbol, pe_symbol = self.get_symbols()

        ce_price = self.md.get_option_price(self.entry_strike, 'CE')
        pe_price = self.md.get_option_price(self.entry_strike, 'PE')

        combined_premium = ce_price + pe_price

        # Position Sizing
        # Risk = 5000
        # SL Risk = 10% of Combined Premium per unit
        risk_per_unit = combined_premium * INITIAL_SL_PCT

        if risk_per_unit > 0:
            raw_qty = FIXED_RISK_PER_TRADE / risk_per_unit
            # Round to nearest Lot Size
            self.quantity = max(LOT_SIZE, round(raw_qty / LOT_SIZE) * LOT_SIZE)
        else:
            self.quantity = LOT_SIZE # Fallback

        self.entry_combined_premium = combined_premium
        self.lowest_premium = combined_premium

        # Set Stops and Targets
        self.sl_price = round(combined_premium * (1 + INITIAL_SL_PCT), 2)
        self.target_price = round(combined_premium * (1 - TARGET_PCT), 2)

        self.log(f"Entry Triggered. Spot: {spot}, Strike: {self.entry_strike}")
        self.log(f"Selling {self.quantity} qty at Combined Premium: {combined_premium:.2f} (CE: {ce_price}, PE: {pe_price})")
        self.log(f"Initial SL: {self.sl_price:.2f}, Target: {self.target_price:.2f}")

        # Place Orders
        self.broker.place_order(ce_symbol, self.quantity, "SELL", ce_price, current_time)
        self.broker.place_order(pe_symbol, self.quantity, "SELL", pe_price, current_time)

        self.status = "ACTIVE"

    def _monitor_trade(self, current_time):
        ce_symbol, pe_symbol = self.get_symbols()

        current_ce = self.md.get_option_price(self.entry_strike, 'CE')
        current_pe = self.md.get_option_price(self.entry_strike, 'PE')

        current_combined = current_ce + current_pe

        # Update Lowest Premium seen (High Water Mark logic for short)
        if current_combined < self.lowest_premium:
            self.lowest_premium = current_combined

        # Check SL
        if current_combined >= self.sl_price:
            reason = "TSL Hit" if self.tsl_active else "Stop Loss Hit"
            self._exit_trade(reason, current_ce, current_pe)
            return

        # Check Target
        if current_combined <= self.target_price:
            self._exit_trade("Target Hit", current_ce, current_pe)
            return

        # TSL Logic
        # Activate when trade moves 2.5% in favor
        # Favor means Premium DECREASES.
        # Entry - Current >= Entry * 0.025
        profit_pct = (self.entry_combined_premium - current_combined) / self.entry_combined_premium

        if profit_pct >= TSL_ACTIVATION_PCT:
            # TSL Active
            # Trail SL: 2.5% of combined premium?
            # Let's assume it means keeping SL at Lowest + 2.5% of ENTRY (or current?).
            # "TSL: 2.5% of combined premium."
            # Let's use 2.5% of ENTRY as the fixed trail distance? Or 2.5% of Current?
            # "Trail SL only in profit direction."

            # Implementation: New SL = Lowest Premium * (1 + TSL_PCT)
            # This tightens the stop as premium drops.
            new_sl = round(self.lowest_premium * (1 + TSL_PCT), 2)

            if new_sl < self.sl_price:
                self.sl_price = new_sl
                if not self.tsl_active:
                    self.tsl_active = True
                    self.log(f"TSL Activated. SL moved to {self.sl_price:.2f}")
                # else:
                #     self.log(f"TSL Updated to {self.sl_price:.2f}")

    def _exit_trade(self, reason, ce_price=None, pe_price=None):
        if not ce_price:
            ce_price = self.md.get_option_price(self.entry_strike, 'CE')
        if not pe_price:
            pe_price = self.md.get_option_price(self.entry_strike, 'PE')

        current_time = self.md.get_current_time().time()
        ce_symbol, pe_symbol = self.get_symbols()

        self.log(f"Exit Triggered: {reason}. Prices - CE: {ce_price}, PE: {pe_price}")

        self.broker.place_order(ce_symbol, self.quantity, "BUY", ce_price, current_time)
        self.broker.place_order(pe_symbol, self.quantity, "BUY", pe_price, current_time)

        self.status = "EXITED"
        self.exit_reason = reason

    def get_status_data(self):
        ce_symbol, pe_symbol = self.get_symbols()
        current_ce = 0
        current_pe = 0
        if self.entry_strike:
            current_ce = self.md.get_option_price(self.entry_strike, 'CE')
            current_pe = self.md.get_option_price(self.entry_strike, 'PE')

        return {
            "status": self.status,
            "entry_strike": self.entry_strike,
            "current_combined": current_ce + current_pe,
            "entry_combined": self.entry_combined_premium,
            "sl_price": self.sl_price,
            "target_price": self.target_price,
            "exit_reason": self.exit_reason,
            "logs": self.logs,
            "tsl_active": self.tsl_active
        }
