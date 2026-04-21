from typing import List

class StockCalculator:
    @staticmethod
    def ma5(prices: List[float]) -> float:
        if len(prices) < 5:
            return 0.0
        return round(sum(prices[-5:]) / 5, 2)

    @staticmethod
    def change_rate(current: float, prev_close: float) -> float:
        if prev_close == 0:
            return 0.0
        return round((current - prev_close) / prev_close * 100, 2)