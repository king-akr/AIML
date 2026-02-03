import random
import math
from datetime import datetime, timedelta, time
from .config import START_TIME
from .utils import parse_time

class MockMarketData:
    def __init__(self, initial_spot=19500):
        self.spot = initial_spot
        self.current_time = datetime.combine(datetime.today(), parse_time(START_TIME))
        self.start_time = self.current_time
        # Volatility parameters
        self.volatility = 2.0  # Random walk step size std dev
        self.trend = 0.0

    def update(self):
        """Advances time by 1 minute and updates spot price."""
        self.current_time += timedelta(minutes=1)

        # Random walk with slight mean reversion or trend can be added
        noise = random.gauss(0, self.volatility)
        self.spot += noise + self.trend

    def get_current_time(self) -> datetime:
        return self.current_time

    def get_spot(self) -> float:
        return self.spot

    def get_option_price(self, strike: float, option_type: str) -> float:
        """
        Calculates a simulated option price.
        option_type: 'CE' or 'PE'
        """
        time_elapsed_minutes = (self.current_time - self.start_time).total_seconds() / 60
        total_day_minutes = 375 # 09:15 to 15:30 is 6h 15m = 375m

        # Theta Decay: Time Value decreases as day progresses
        # Start with 100 TV, decay to 0 by end of day (simplified)
        initial_tv = 100
        decay_factor = max(0, 1 - (time_elapsed_minutes / (total_day_minutes * 1.5)))
        # *1.5 to not decay to zero exactly at 3:30 for safety

        current_peak_tv = initial_tv * decay_factor

        # Time Value decays as we move away from strike (Smile/Tent)
        # Using a gaussian-like decay for TV based on distance
        distance = abs(self.spot - strike)
        tv = current_peak_tv * math.exp(-0.01 * distance)

        intrinsic = 0.0
        if option_type == 'CE':
            intrinsic = max(0.0, self.spot - strike)
        elif option_type == 'PE':
            intrinsic = max(0.0, strike - self.spot)

        price = intrinsic + tv

        # Add some random noise to option price specifically
        price += random.gauss(0, 0.5)

        return max(0.05, round(price, 2))

    def get_atm_strike(self) -> float:
        """Returns the ATM strike (rounded to nearest 50)."""
        return round(self.spot / 50) * 50
