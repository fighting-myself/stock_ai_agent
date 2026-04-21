import tushare as ts
import pandas as pd
from datetime import datetime, timedelta
from utils.logger import logger
from utils.retry import stock_retry
from config.settings import settings

class TushareClient:
    def __init__(self):
        self.pro = ts.pro_api(settings.TUSHARE_TOKEN)
        logger.info("Tushare 初始化成功")

    @stock_retry
    def get_real_price(self, code: str):
        """获取实时价格（简化：用当日日线）"""
        today = datetime.now().strftime("%Y%m%d")
        df = self.pro.daily(ts_code=self._to_ts_code(code), trade_date=today)
        if df.empty:
            logger.error(f"{code} 当日无数据")
            raise Exception("获取实时价格失败")
        data = df.iloc[0]
        return {
            "code": code,
            "name": "个股",
            "close": float(data.close),
            "price": float(data.close),
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

    def _to_ts_code(self, code: str):
        """600xxx → 600xxx.SH；00xxxx → 00xxxx.SZ"""
        if code.startswith("6"):
            return f"{code}.SH"
        else:
            return f"{code}.SZ"