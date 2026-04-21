from typing import List
import pandas as pd

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

    @staticmethod
    def moving_average(prices: List[float], window: int) -> List[float]:
        s = pd.Series(prices, dtype="float64")
        ma = s.rolling(window=window).mean().round(4)
        return [None if pd.isna(v) else float(v) for v in ma.tolist()]

    @staticmethod
    def rsi(prices: List[float], period: int = 14) -> float:
        if len(prices) <= period:
            return 0.0
        s = pd.Series(prices, dtype="float64")
        delta = s.diff()
        gain = delta.clip(lower=0)
        loss = -delta.clip(upper=0)
        avg_gain = gain.rolling(window=period).mean()
        avg_loss = loss.rolling(window=period).mean()
        rs = avg_gain / avg_loss.replace(0, pd.NA)
        rsi = 100 - (100 / (1 + rs))
        val = rsi.iloc[-1]
        return 0.0 if pd.isna(val) else round(float(val), 2)

    @staticmethod
    def macd(prices: List[float]):
        s = pd.Series(prices, dtype="float64")
        ema12 = s.ewm(span=12, adjust=False).mean()
        ema26 = s.ewm(span=26, adjust=False).mean()
        dif = ema12 - ema26
        dea = dif.ewm(span=9, adjust=False).mean()
        macd_hist = (dif - dea) * 2
        return {
            "dif": round(float(dif.iloc[-1]), 4),
            "dea": round(float(dea.iloc[-1]), 4),
            "macd": round(float(macd_hist.iloc[-1]), 4),
        }

    @staticmethod
    def risk_metrics(prices: List[float], annualization: int = 252):
        if len(prices) < 3:
            return {"volatility_annual": 0.0, "max_drawdown_pct": 0.0}
        s = pd.Series(prices, dtype="float64")
        ret = s.pct_change().dropna()
        vol = float(ret.std() * (annualization ** 0.5) * 100)
        running_max = s.cummax()
        drawdown = (s / running_max - 1) * 100
        mdd = float(drawdown.min())
        return {
            "volatility_annual": round(vol, 2),
            "max_drawdown_pct": round(mdd, 2),
        }