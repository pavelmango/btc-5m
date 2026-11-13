"""
Taker fee calculator for binary CLOB prediction markets.
Implements the exact formula:
    fee = C * rate * p * (1 - p)
where:
    - PM US rate in range [0.0695, 0.095]
    - Kalshi rate = 0.07
    - C is scaling multiplier (default 1.0)
    - p is the execution contract price in [0.0, 1.0]
"""

class TakerFeeModel:
    def __init__(self, venue: str = "polymarket", rate: float = None, c_multiplier: float = 1.0):
        self.venue = venue.lower()
        self.c_multiplier = c_multiplier
        if rate is not None:
            self.rate = rate
        elif "poly" in self.venue:
            # Default Polymarket US within [0.0695, 0.095]
            self.rate = 0.075
        elif "kalshi" in self.venue:
            self.rate = 0.07
        else:
            self.rate = 0.075

    def fee_per_contract(self, price: float) -> float:
        """
        Calculate fee per contract share:
        fee = C * rate * p * (1 - p)
        """
        p = max(0.0, min(1.0, float(price)))
        # Variance of binary outcome
        variance = p * (1.0 - p)
        fee = self.c_multiplier * self.rate * variance
        return max(0.0, round(fee, 6))

    def calculate_total_fee(self, size: float, price: float) -> float:
        """Total fee for an executed order size at price p."""
        per_contract = self.fee_per_contract(price)
        return round(size * per_contract, 6)
