from abc import ABC, abstractmethod
from datetime import datetime
from typing import Dict, List, Any

class BrokerInterface(ABC):
    @abstractmethod
    def get_current_time(self) -> datetime:
        pass

    @abstractmethod
    def get_ltp(self, symbol: str) -> float:
        pass

    @abstractmethod
    def place_order(self, symbol: str, quantity: int, side: str, order_type: str = "MARKET") -> Dict[str, Any]:
        """
        side: 'BUY' or 'SELL'
        Returns order details dict
        """
        pass

    @abstractmethod
    def get_positions(self) -> List[Dict[str, Any]]:
        pass

    @abstractmethod
    def get_atm_strike(self) -> int:
        """Returns the current ATM strike for the index"""
        pass
