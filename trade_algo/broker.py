from .config import TOTAL_CAPITAL

class MockBroker:
    def __init__(self):
        self.capital = TOTAL_CAPITAL
        self.positions = {} # {symbol: quantity} (+ for Buy, - for Sell)
        self.average_prices = {} # {symbol: avg_price}
        self.trades = []
        self.realized_pnl = 0.0

    def place_order(self, symbol: str, quantity: int, action: str, price: float, time):
        """
        Executes an order.
        action: 'BUY' or 'SELL'
        """
        signed_qty = quantity if action == 'BUY' else -quantity
        cost = signed_qty * price

        # Update Capital (Cash Flow)
        # Sell: Receive cash (Credit). Buy: Pay cash (Debit).
        # We assume margin is managed separately or we just track cash flow for PnL.
        # But for MTM, we usually track PnL = (Exit - Entry) * Qty.

        # Let's track Positions
        current_qty = self.positions.get(symbol, 0)
        current_avg = self.average_prices.get(symbol, 0.0)

        # Trade Log
        trade_record = {
            'time': time,
            'symbol': symbol,
            'action': action,
            'quantity': quantity,
            'price': price,
            'value': abs(cost)
        }
        self.trades.append(trade_record)

        # PnL Calculation for Closing/Reducing positions
        if (current_qty > 0 and signed_qty < 0) or (current_qty < 0 and signed_qty > 0):
            # Closing portion
            close_qty = min(abs(current_qty), abs(signed_qty))
            # PnL on this portion
            # If Long (current > 0), Sell (signed < 0): PnL = (Price - Avg) * CloseQty
            # If Short (current < 0), Buy (signed > 0): PnL = (Avg - Price) * CloseQty

            pnl = 0
            if current_qty > 0: # Long closing
                pnl = (price - current_avg) * close_qty
            else: # Short covering
                pnl = (current_avg - price) * close_qty

            self.realized_pnl += pnl

            # Update Position
            new_qty = current_qty + signed_qty
            self.positions[symbol] = new_qty

            if new_qty == 0:
                del self.positions[symbol]
                del self.average_prices[symbol]
            # If position reversed, handle that (simplification: assume we close then open new, but here we just update net)
            # Complex logic omitted for simplicity. Assuming we either open or close fully usually.

        else:
            # Increasing position
            total_qty = current_qty + signed_qty
            # Weighted average price
            # new_avg = (old_qty * old_avg + new_qty * new_price) / total_qty
            # For Short: quantities are negative.
            total_val = (current_qty * current_avg) + (signed_qty * price)
            new_avg = total_val / total_qty if total_qty != 0 else 0

            self.positions[symbol] = total_qty
            self.average_prices[symbol] = new_avg

    def get_positions(self):
        return self.positions

    def get_realized_pnl(self):
        return self.realized_pnl

    def get_unrealized_mtm(self, current_prices: dict):
        """
        current_prices: {symbol: price}
        """
        mtm = 0.0
        for symbol, qty in self.positions.items():
            if symbol in current_prices:
                current_price = current_prices[symbol]
                avg_price = self.average_prices[symbol]

                if qty > 0: # Long
                    mtm += (current_price - avg_price) * qty
                else: # Short
                    mtm += (avg_price - current_price) * abs(qty)
        return mtm

    def get_total_pnl(self, current_prices: dict):
        return self.realized_pnl + self.get_unrealized_mtm(current_prices)

    def get_trades(self):
        return self.trades
