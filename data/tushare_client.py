import tushare as ts
import pandas as pd
import httpx
from datetime import datetime, timedelta
from utils.logger import logger
from utils.retry import stock_retry
from config.settings import settings

class TushareClient:
    def __init__(self):
        self.pro = ts.pro_api(settings.TUSHARE_TOKEN)
        self.em_quote_url = "https://push2.eastmoney.com/api/qt/stock/get"
        self.em_kline_url = "https://push2his.eastmoney.com/api/qt/stock/kline/get"
        logger.info("Tushare 初始化成功")

    @stock_retry
    def get_real_price(self, code: str):
        """获取实时价格（简化：用当日日线）"""
        try:
            today = datetime.now().strftime("%Y%m%d")
            df = self.pro.daily(ts_code=self._to_ts_code(code), trade_date=today)
            if df.empty:
                raise Exception(f"{code} 当日无数据")
            data = df.iloc[0]
            return {
                "code": code,
                "name": "个股",
                "close": float(data.close),
                "price": float(data.close),
                "source": "tushare",
            }
        except Exception as exc:
            logger.warning(f"{code} Tushare 实时价失败，切换 Eastmoney: {str(exc)}")
            snap = self._get_eastmoney_quote_snapshot(code)
            return {
                "code": code,
                "name": snap.get("name", "个股"),
                "close": float(snap.get("prev_close", snap.get("price", 0.0))),
                "price": float(snap.get("price", 0.0)),
                "source": "eastmoney",
            }

    @stock_retry
    def get_5d_klines(self, code: str):
        """获取最近 5 日收盘价 → 用于 MA5"""
        end = datetime.now()
        start = end - timedelta(days=30)
        df = self.pro.daily(
            ts_code=self._to_ts_code(code),
            start_date=start.strftime("%Y%m%d"),
            end_date=end.strftime("%Y%m%d")
        )
        df = df.sort_values("trade_date").tail(5)
        closes = df["close"].tolist()
        closes = [float(x) for x in closes]
        logger.info(f"{code} 5日收盘价: {closes}")
        return closes

    @stock_retry
    def get_recent_daily(self, code: str, days: int = 60):
        """获取最近 N 个交易日行情（升序）"""
        try:
            end = datetime.now()
            start = end - timedelta(days=max(days * 3, 30))
            df = self.pro.daily(
                ts_code=self._to_ts_code(code),
                start_date=start.strftime("%Y%m%d"),
                end_date=end.strftime("%Y%m%d"),
            )
            if df.empty:
                raise Exception(f"{code} 最近行情为空")
            df = df.sort_values("trade_date").tail(days).copy()
            df["trade_date"] = df["trade_date"].astype(str)
            return df[["trade_date", "open", "high", "low", "close", "vol", "amount"]]
        except Exception as exc:
            logger.warning(f"{code} Tushare 日线失败，切换 Eastmoney: {str(exc)}")
            return self._get_eastmoney_daily(code=code, days=days)

    @stock_retry
    def get_quote_snapshot(self, code: str):
        """获取简化行情快照（基于最近两个交易日）"""
        try:
            df = self.get_recent_daily(code=code, days=2)
            latest = df.iloc[-1]
            prev = df.iloc[-2] if len(df) > 1 else latest
            price = float(latest["close"])
            prev_close = float(prev["close"])
            change = price - prev_close
            pct = (change / prev_close * 100) if prev_close else 0.0
            return {
                "code": code,
                "trade_date": str(latest["trade_date"]),
                "open": float(latest["open"]),
                "high": float(latest["high"]),
                "low": float(latest["low"]),
                "price": round(price, 2),
                "prev_close": round(prev_close, 2),
                "change": round(change, 2),
                "change_pct": round(pct, 2),
                "vol": float(latest["vol"]),
                "amount": float(latest["amount"]),
                "source": "tushare",
            }
        except Exception as exc:
            logger.warning(f"{code} 快照切换 Eastmoney: {str(exc)}")
            return self._get_eastmoney_quote_snapshot(code)

    @stock_retry
    def get_daily_basic_latest(self, code: str):
        """获取个股最新估值指标（PE/PB/总市值等）"""
        fallback = {
            "code": code,
            "trade_date": None,
            "pe": None,
            "pb": None,
            "ps": None,
            "total_mv": None,
            "circ_mv": None,
            "turnover_rate": None,
            "volume_ratio": None,
            "available": False,
            "reason": "daily_basic 无权限或数据不可用",
        }
        try:
            end = datetime.now()
            start = end - timedelta(days=40)
            df = self.pro.daily_basic(
                ts_code=self._to_ts_code(code),
                start_date=start.strftime("%Y%m%d"),
                end_date=end.strftime("%Y%m%d"),
                fields="ts_code,trade_date,pe,pb,ps,total_mv,circ_mv,turnover_rate,volume_ratio",
            )
            if df.empty:
                logger.warning(f"{code} daily_basic 返回空数据")
                return fallback
            df = df.sort_values("trade_date")
            row = df.iloc[-1]
            return {
                "code": code,
                "trade_date": str(row["trade_date"]),
                "pe": None if pd.isna(row["pe"]) else float(row["pe"]),
                "pb": None if pd.isna(row["pb"]) else float(row["pb"]),
                "ps": None if pd.isna(row["ps"]) else float(row["ps"]),
                "total_mv": None if pd.isna(row["total_mv"]) else float(row["total_mv"]),
                "circ_mv": None if pd.isna(row["circ_mv"]) else float(row["circ_mv"]),
                "turnover_rate": None if pd.isna(row["turnover_rate"]) else float(row["turnover_rate"]),
                "volume_ratio": None if pd.isna(row["volume_ratio"]) else float(row["volume_ratio"]),
                "available": True,
                "reason": "",
            }
        except Exception as exc:
            logger.warning(f"{code} 估值数据降级: {str(exc)}")
            em_basic = self._get_eastmoney_basic(code=code)
            if em_basic:
                return em_basic
            return fallback

    def _secid(self, code: str) -> str:
        return f"1.{code}" if code.startswith("6") else f"0.{code}"

    def _get_eastmoney_quote_snapshot(self, code: str):
        params = {
            "secid": self._secid(code),
            "fields": "f57,f58,f43,f44,f45,f46,f47,f48,f170",
        }
        with httpx.Client(timeout=settings.EASTMONEY_API_TIMEOUT) as client:
            resp = client.get(self.em_quote_url, params=params)
            resp.raise_for_status()
            payload = resp.json()
        data = payload.get("data") or {}
        price = float(data.get("f43") or 0) / 100
        prev_close = float(data.get("f44") or 0) / 100
        change_pct = float(data.get("f170") or 0) / 100
        change = price - prev_close
        return {
            "code": code,
            "name": data.get("f58", "个股"),
            "trade_date": datetime.now().strftime("%Y%m%d"),
            "open": float(data.get("f46") or 0) / 100,
            "high": float(data.get("f45") or 0) / 100,
            "low": float(data.get("f44") or 0) / 100,
            "price": round(price, 2),
            "prev_close": round(prev_close, 2),
            "change": round(change, 2),
            "change_pct": round(change_pct, 2),
            "vol": float(data.get("f47") or 0),
            "amount": float(data.get("f48") or 0),
            "source": "eastmoney",
        }

    def _get_eastmoney_daily(self, code: str, days: int = 60):
        params = {
            "secid": self._secid(code),
            "klt": "101",
            "fqt": "1",
            "beg": "0",
            "end": "20500101",
            "fields1": "f1,f2,f3,f4,f5,f6",
            "fields2": "f51,f52,f53,f54,f55,f56,f57,f58",
        }
        with httpx.Client(timeout=settings.EASTMONEY_API_TIMEOUT) as client:
            resp = client.get(self.em_kline_url, params=params)
            resp.raise_for_status()
            payload = resp.json()
        data = payload.get("data") or {}
        klines = data.get("klines") or []
        if not klines:
            raise Exception(f"{code} Eastmoney 历史K线为空")
        rows = []
        for line in klines[-days:]:
            parts = line.split(",")
            if len(parts) < 7:
                continue
            rows.append(
                {
                    "trade_date": parts[0].replace("-", ""),
                    "open": float(parts[1]),
                    "close": float(parts[2]),
                    "high": float(parts[3]),
                    "low": float(parts[4]),
                    "vol": float(parts[5]),
                    "amount": float(parts[6]),
                }
            )
        if not rows:
            raise Exception(f"{code} Eastmoney K线解析失败")
        return pd.DataFrame(rows)

    def _get_eastmoney_basic(self, code: str):
        try:
            params = {
                "secid": self._secid(code),
                "fields": "f57,f58,f164,f167,f116,f117,f168,f50",
            }
            with httpx.Client(timeout=settings.EASTMONEY_API_TIMEOUT) as client:
                resp = client.get(self.em_quote_url, params=params)
                resp.raise_for_status()
                payload = resp.json()
            data = payload.get("data") or {}
            if not data:
                return None
            return {
                "code": code,
                "trade_date": datetime.now().strftime("%Y%m%d"),
                "pe": None if data.get("f164") is None else float(data.get("f164")),
                "pb": None if data.get("f167") is None else float(data.get("f167")),
                "ps": None,
                "total_mv": None if data.get("f116") is None else float(data.get("f116")),
                "circ_mv": None if data.get("f117") is None else float(data.get("f117")),
                "turnover_rate": None if data.get("f168") is None else float(data.get("f168")),
                "volume_ratio": None if data.get("f50") is None else float(data.get("f50")),
                "available": True,
                "reason": "",
                "source": "eastmoney",
            }
        except Exception as exc:
            logger.warning(f"{code} Eastmoney 估值回退失败: {str(exc)}")
            return None

    def _to_ts_code(self, code: str):
        """600xxx → 600xxx.SH；00xxxx → 00xxxx.SZ"""
        if code.startswith("6"):
            return f"{code}.SH"
        else:
            return f"{code}.SZ"