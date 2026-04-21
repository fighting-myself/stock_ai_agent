import httpx
from utils.logger import logger
from utils.retry import stock_retry
from config.settings import settings

class EastMoneyApi:
    def __init__(self):
        self.timeout = settings.EASTMONEY_API_TIMEOUT
        self.base_url = "https://push2.eastmoney.com/api/qt/stock/get"

    @stock_retry
    async def get_realtime_price(self, code: str) -> dict:
        if code.startswith("6"):
            secid = f"1.{code}"
        else:
            secid = f"0.{code}"

        params = {
            "secid": secid,
            "fields": "f58,f43,f44,f45,f46,f47",
            "mp": "3"
        }

        async with httpx.AsyncClient(timeout=self.timeout) as client:
            resp = await client.get(self.base_url, params=params)
            resp.raise_for_status()
            data = resp.json()

            dt = data["data"]
            return {
                "name": dt.get("f58", "未知"),
                "code": code,
                "current": float(dt.get("f43", 0)),
                "close": float(dt.get("f44", 0)),
            }