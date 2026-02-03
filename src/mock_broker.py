import random
from datetime import datetime, timedelta
from typing import Dict, List, Any
from .broker_interface import BrokerInterface
from .config import Config

class MockBroker(BrokerInterface):
    def __init__(self):
        # Set date to today
        today = datetime.now().date()
        self.current_time = datetime.combine(today, Config.MARKET_START_TIME)

        self.spot_price = 20000.0
        self.orders = []
        self.positions = {} # Symbol -> Quantity

        # Simulation parameters
        self.volatility = 2.0 # Points per tick

        # To make prices consistent, we need to cache LTP if called multiple times in same tick
        self._price_cache = {}

    def get_current_time(self) -> datetime:
        return self.current_time

    def advance_time(self, seconds: int = 1):
        self.current_time += timedelta(seconds=seconds)
        self._update_market_data()
        self._price_cache = {} # Clear cache on new tick

    def _update_market_data(self):
        # Random Walk for Spot
        change = random.uniform(-self.volatility, self.volatility)
        self.spot_price += change

    def get_atm_strike(self) -> int:
        return round(self.spot_price / 50) * 50

    def get_ltp(self, symbol: str) -> float:
        if symbol in self._price_cache:
            return self._price_cache[symbol]

        price = 0.0
        if symbol == Config.INDEX:
            price = self.spot_price
        elif "CE" in symbol or "PE" in symbol:
            # Parse symbol e.g. NIFTY20000CE
            # Find the number part
            import re
            match = re.search(r'(\d+)', symbol)
            if match:
                strike = int(match.group(1))
                is_ce = "CE" in symbol

                time_value = 100.0 # Base time value
                intrinsic = 0.0
                if is_ce:
                    intrinsic = max(0, self.spot_price - strike)
                else:
                    intrinsic = max(0, strike - self.spot_price)

                # Add some randomness to option pricing relative to spot
                noise = random.uniform(-2, 2)
                price = intrinsic + time_value + noise

        self._price_cache[symbol] = price
        return price

    def place_order(self, symbol: str, quantity: int, side: str, order_type: str = "MARKET") -> Dict[str, Any]:
        price = self.get_ltp(symbol)

        # Slippage simulation (random small pct)
        slippage = random.uniform(-0.5, 0.5)
        final_price = price + slippage

        order = {
            "id": len(self.orders) + 1,
            "symbol": symbol,
            "quantity": quantity,
            "side": side,
            "price": final_price,
            "order_type": order_type,
            "time": self.current_time,
            "status": "EXECUTED"
        }
        self.orders.append(order)

        # Update positions
        current_qty = self.positions.get(symbol, 0)
        if side == "BUY":
            current_qty += quantity
        elif side == "SELL":
            current_qty -= quantity
        self.positions[symbol] = current_qty

        return order

    def get_positions(self) -> List[Dict[str, Any]]:
        pos_list = []
        for sym, qty in self.positions.items():
            if qty != 0:
                ltp = self.get_ltp(sym)
                pos_list.append({
                    "symbol": sym,
                    "quantity": qty,
                    "ltp": ltp
                })
        return pos_list
