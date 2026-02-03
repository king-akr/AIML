import pytest
from datetime import datetime
from trade_algo.strategy import ShortStraddleStrategy
from trade_algo.broker import MockBroker
from trade_algo.market_data import MockMarketData
from trade_algo.config import ENTRY_TIME, INITIAL_SL_PCT, TARGET_PCT

class ControllableMarketData(MockMarketData):
    def __init__(self):
        super().__init__()
        self.manual_time = None
        self.manual_spot = 19500
        self.manual_ce = 100
        self.manual_pe = 100

    def set_data(self, time_str, spot, ce, pe):
        self.manual_time = datetime.combine(datetime.today(), datetime.strptime(time_str, "%H:%M").time())
        self.manual_spot = spot
        self.manual_ce = ce
        self.manual_pe = pe

    def get_current_time(self):
        return self.manual_time if self.manual_time else super().get_current_time()

    def get_spot(self):
        return self.manual_spot

    def get_option_price(self, strike, option_type):
        if option_type == 'CE':
            return self.manual_ce
        return self.manual_pe

    def get_atm_strike(self):
        return round(self.manual_spot / 50) * 50

@pytest.fixture
def strategy_setup():
    md = ControllableMarketData()
    broker = MockBroker()
    strategy = ShortStraddleStrategy(md, broker)
    return strategy, md, broker

def test_entry_logic(strategy_setup):
    strategy, md, broker = strategy_setup

    # Before Entry Time
    md.set_data("09:15", 19500, 100, 100)
    strategy.run_tick()
    assert strategy.status == "WAITING"
    assert len(broker.trades) == 0

    # At Entry Time
    md.set_data(ENTRY_TIME, 19500, 100, 100) # Combined = 200
    strategy.run_tick()

    assert strategy.status == "ACTIVE"
    assert len(broker.trades) == 2 # Sell CE, Sell PE
    assert strategy.entry_combined_premium == 200
    assert strategy.sl_price == pytest.approx(200 * (1 + INITIAL_SL_PCT), 0.01)
    assert strategy.target_price == pytest.approx(200 * (1 - TARGET_PCT), 0.01)

    # Check Quantity: Risk 5000. SL Risk 10% (20 pts). Qty = 5000/20 = 250.
    # Assuming Lot Size 50.
    assert strategy.quantity == 250

def test_sl_exit(strategy_setup):
    strategy, md, broker = strategy_setup

    # Entry
    md.set_data(ENTRY_TIME, 19500, 100, 100)
    strategy.run_tick()

    # Move price up to SL (Entry 200, SL 220)
    # CE=120, PE=100 -> 220
    md.set_data("09:30", 19500, 120, 100)
    strategy.run_tick()

    assert strategy.status == "EXITED"
    assert strategy.exit_reason == "Stop Loss Hit"
    assert len(broker.trades) == 4 # 2 Entry + 2 Exit

def test_target_exit(strategy_setup):
    strategy, md, broker = strategy_setup

    # Entry
    md.set_data(ENTRY_TIME, 19500, 100, 100)
    strategy.run_tick()

    # Move price down to Target (Entry 200, Target 180)
    # CE=90, PE=90 -> 180
    md.set_data("09:30", 19500, 90, 90)
    strategy.run_tick()

    assert strategy.status == "EXITED"
    assert strategy.exit_reason == "Target Hit"

def test_tsl_logic(strategy_setup):
    strategy, md, broker = strategy_setup

    # Entry: 200. SL: 220.
    md.set_data(ENTRY_TIME, 19500, 100, 100)
    strategy.run_tick()

    # Move 2% in favor (Not activated). 200 -> 196.
    md.set_data("09:20", 19500, 98, 98) # 196
    strategy.run_tick()
    assert strategy.tsl_active is False
    assert strategy.sl_price == 220

    # Move 3% in favor (Activated). 200 -> 194. (Delta > 2.5%)
    md.set_data("09:21", 19500, 97, 97) # 194
    strategy.run_tick()
    assert strategy.tsl_active is True

    # New SL check: Lowest=194. TSL_PCT=0.025.
    # New SL = 194 * 1.025 = 198.85
    expected_sl = 194 * 1.025
    assert abs(strategy.sl_price - expected_sl) < 0.1

    # Move further down to 185 (Target 180, so not hit yet)
    md.set_data("09:25", 19500, 92.5, 92.5) # 185
    strategy.run_tick()
    # Lowest=185. New SL = 185 * 1.025 = 189.625
    expected_sl_2 = 185 * 1.025
    assert abs(strategy.sl_price - expected_sl_2) < 0.1

    # Reversal to Hit TSL (Price goes to 190)
    md.set_data("09:30", 19500, 95, 95) # 190
    strategy.run_tick()

    assert strategy.status == "EXITED"
    assert strategy.exit_reason == "TSL Hit"
