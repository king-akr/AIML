import unittest
from unittest.mock import MagicMock
from datetime import datetime, time, date
from src.strategy import ShortStraddleStrategy
from src.config import Config
from src.broker_interface import BrokerInterface

class TestShortStraddleStrategy(unittest.TestCase):
    def setUp(self):
        self.broker = MagicMock(spec=BrokerInterface)
        self.strategy = ShortStraddleStrategy(self.broker)
        # Setup default broker behavior
        self.broker.get_current_time.return_value = datetime.combine(date.today(), time(9, 15))
        self.broker.get_atm_strike.return_value = 20000
        # Default 100 per leg so combined is 200
        self.broker.get_ltp.side_effect = lambda symbol: 100.0

    def test_entry_condition(self):
        # Time 9:15 - No Entry
        self.strategy.run()
        self.assertEqual(self.strategy.state, "WAITING")

        # Time 9:17 - Entry
        self.broker.get_current_time.return_value = datetime.combine(date.today(), time(9, 17))
        self.strategy.run()
        self.assertEqual(self.strategy.state, "ENTERED")
        # Should place 2 sell orders
        self.assertEqual(self.broker.place_order.call_count, 2)

    def test_position_sizing(self):
        # Combined Premium = 100 + 100 = 200
        # Risk = 10% = 20 pts
        # Max Risk = 50,000
        # Qty = 50,000 / 20 = 2500
        # Lots = 2500 / 25 = 100 lots

        self.broker.get_current_time.return_value = datetime.combine(date.today(), time(9, 17))
        self.broker.get_ltp.side_effect = lambda s: 100.0

        self.strategy.run()

        self.assertEqual(self.strategy.quantity, 2500)

    def test_sl_execution(self):
        # Enter
        self.broker.get_current_time.return_value = datetime.combine(date.today(), time(9, 17))
        self.strategy.run()

        # Initial SL: Combined 200 * 1.10 = 220.

        # Move price to 221
        self.broker.get_current_time.return_value = datetime.combine(date.today(), time(9, 30))
        self.broker.get_ltp.side_effect = lambda s: 110.5 # Combined 221

        self.strategy.run()

        self.assertEqual(self.strategy.state, "EXITED")
        self.assertIn("Stop Loss Hit", self.strategy.message)

    def test_target_execution(self):
        # Enter
        self.broker.get_current_time.return_value = datetime.combine(date.today(), time(9, 17))
        self.strategy.run()

        # Target: Combined 200 * 0.90 = 180.

        # Move price to 179
        self.broker.get_current_time.return_value = datetime.combine(date.today(), time(9, 30))
        self.broker.get_ltp.side_effect = lambda s: 89.5 # Combined 179

        self.strategy.run()

        self.assertEqual(self.strategy.state, "EXITED")
        self.assertIn("Target Hit", self.strategy.message)

    def test_trailing_sl(self):
        # Enter at 200
        self.broker.get_current_time.return_value = datetime.combine(date.today(), time(9, 17))
        self.broker.get_ltp.side_effect = lambda s: 100.0
        self.strategy.run()

        initial_sl = 220.0
        self.assertAlmostEqual(self.strategy.sl_price, initial_sl)

        # Activation: 2.5% profit -> 200 * 0.025 = 5 pts. Price <= 195.

        # Move to 196 (Not active yet)
        self.broker.get_ltp.side_effect = lambda s: 98.0 # Combined 196
        self.strategy.run()
        self.assertFalse(self.strategy.trailing_active)
        self.assertAlmostEqual(self.strategy.sl_price, initial_sl)

        # Move to 195 (Active)
        self.broker.get_ltp.side_effect = lambda s: 97.5 # Combined 195
        self.strategy.run()
        self.assertTrue(self.strategy.trailing_active)

        # New SL = Current + (Entry * 2.5%) = 195 + 5 = 200.
        self.assertAlmostEqual(self.strategy.sl_price, 200.0)

        # Move to 190 (Profit 10 pts)
        self.broker.get_ltp.side_effect = lambda s: 95.0 # Combined 190
        self.strategy.run()

        # New SL = 190 + 5 = 195.
        self.assertAlmostEqual(self.strategy.sl_price, 195.0)

    def test_time_exit(self):
        self.broker.get_current_time.return_value = datetime.combine(date.today(), time(9, 17))
        self.strategy.run()

        self.assertEqual(self.strategy.state, "ENTERED")

        # Jump to 15:00
        self.broker.get_current_time.return_value = datetime.combine(date.today(), time(15, 0))
        self.strategy.run()

        self.assertEqual(self.strategy.state, "EXITED")
        self.assertIn("Time Based Exit", self.strategy.message)
