from langchain_core.tools import Tool
from data.tushare_client import TushareClient
from data.calculator import StockCalculator

class StockTools:
    def __init__(self):
        self.ts = TushareClient()
        self.calc = StockCalculator()

    async def get_stock_price(self, code: str):
        """获取股票实时价格"""
        data = self.ts.get_real_price(code)
        return f"股票{code} 当前价: {data['price']:.2f}"

    async def calculate_ma5(self, code: str):
        """自动获取5日K线并计算MA5"""
        closes = self.ts.get_5d_klines(code)
        ma5 = self.calc.ma5(closes)
        return f"股票{code} 5日均线 MA5 = {ma5:.2f}"

    @classmethod
    def get_all_tools(cls):
        t = cls()
        return [
            Tool(
                name="get_stock_price",
                func=lambda c: None,
                coroutine=t.get_stock_price,
                description="输入股票代码如 600519，获取实时价格"
            ),
            Tool(
                name="calculate_ma5",
                func=lambda c: None,
                coroutine=t.calculate_ma5,
                description="输入股票代码，自动获取K线并计算5日均线 MA5"
            ),
        ]