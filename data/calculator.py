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

    @staticmethod
    def bollinger_bands(prices: List[float], window: int = 20, std_factor: float = 2.0):
        if len(prices) < window:
            return {"mid": 0.0, "upper": 0.0, "lower": 0.0}
        s = pd.Series(prices, dtype="float64")
        mid = s.rolling(window=window).mean().iloc[-1]
        std = s.rolling(window=window).std().iloc[-1]
        upper = mid + std_factor * std
        lower = mid - std_factor * std
        return {
            "mid": round(float(mid), 2),
            "upper": round(float(upper), 2),
            "lower": round(float(lower), 2),
        }

    @staticmethod
    def kdj(highs: List[float], lows: List[float], closes: List[float], period: int = 9):
        if len(closes) < period:
            return {"k": 0.0, "d": 0.0, "j": 0.0}
        high_s = pd.Series(highs, dtype="float64")
        low_s = pd.Series(lows, dtype="float64")
        close_s = pd.Series(closes, dtype="float64")
        low_n = low_s.rolling(period).min()
        high_n = high_s.rolling(period).max()
        rsv = (close_s - low_n) / (high_n - low_n).replace(0, pd.NA) * 100
        k = rsv.ewm(com=2, adjust=False).mean()
        d = k.ewm(com=2, adjust=False).mean()
        j = 3 * k - 2 * d
        return {
            "k": round(float(k.iloc[-1]), 2),
            "d": round(float(d.iloc[-1]), 2),
            "j": round(float(j.iloc[-1]), 2),
        }

    @staticmethod
    def var_cvar(prices: List[float], confidence: float = 0.95):
        if len(prices) < 5:
            return {"var_pct": 0.0, "cvar_pct": 0.0}
        ret = pd.Series(prices, dtype="float64").pct_change().dropna()
        alpha = 1 - confidence
        var = float(ret.quantile(alpha) * 100)
        tail = ret[ret <= ret.quantile(alpha)]
        cvar = float((tail.mean() if len(tail) > 0 else ret.quantile(alpha)) * 100)
        return {"var_pct": round(var, 2), "cvar_pct": round(cvar, 2)}

    @staticmethod
    def support_resistance(highs: List[float], lows: List[float], closes: List[float], lookback: int = 20):
        if len(closes) < lookback:
            return {"support": 0.0, "resistance": 0.0, "price": 0.0, "signal": "insufficient_data"}
        high_s = pd.Series(highs[-lookback:], dtype="float64")
        low_s = pd.Series(lows[-lookback:], dtype="float64")
        price = float(closes[-1])
        support = float(low_s.min())
        resistance = float(high_s.max())
        signal = "range"
        if price >= resistance * 0.995:
            signal = "near_breakout_up"
        elif price <= support * 1.005:
            signal = "near_breakdown_down"
        return {
            "support": round(support, 2),
            "resistance": round(resistance, 2),
            "price": round(price, 2),
            "signal": signal,
        }