from langchain_core.tools import Tool
from data.tushare_client import TushareClient
from data.calculator import StockCalculator
from data.market_intel_client import MarketIntelClient
from data.ths_ifind_client import ThsIfindClient
from tools.clock_tool import build_clock_answer


class StockTools:
    def __init__(self):
        self.ts = TushareClient()
        self.calc = StockCalculator()
        self.intel = MarketIntelClient()
        self.ths = ThsIfindClient()

    async def get_current_datetime(self, iana_timezone: str = ""):
        """返回调用瞬间的墙钟时间快照（UTC、进程本地、可选 IANA 换算）。"""
        return build_clock_answer(iana_timezone or "")

    async def get_stock_price(self, code: str):
        """获取股票实时价格"""
        data = self.ts.get_real_price(code)
        return f"股票{code} 当前价: {data['price']:.2f}"

    async def calculate_ma5(self, code: str):
        """自动获取5日K线并计算MA5"""
        closes = self.ts.get_5d_klines(code)
        ma5 = self.calc.ma5(closes)
        return f"股票{code} 5日均线 MA5 = {ma5:.2f}"

    async def get_recent_announcements(self, code: str):
        """获取 A 股公司近期公告标题列表（非结构化信息，供投资决策引用）"""
        try:
            rows = self.intel.fetch_recent_notices(code.strip(), page_size=10)
            if not rows:
                return f"股票{code} 近期未拉取到公告列表（可能无数据或接口变更）。"
            lines = [f"- {r.get('date', '')} {r.get('title', '')}" for r in rows]
            return f"股票{code} 近期公告摘要（共{len(lines)}条）：\n" + "\n".join(lines)
        except Exception as exc:
            return f"拉取公告失败: {str(exc)}"

    async def get_ths_recent_reports(self, query: str):
        """同花顺 iFinD 专题报表：近期披露类标题（自然语言列表）。query 为「代码」或「代码,天数」如 600519,30。"""
        try:
            parts = (query or "").replace("，", ",").split(",", 1)
            code = parts[0].strip()
            d = 14
            if len(parts) > 1:
                try:
                    d = int(parts[1].strip())
                except ValueError:
                    d = 14
            d = max(1, min(d, 365))
            return self.ths.report_query_titles(code, days=d)
        except Exception as exc:
            return f"同花顺专题报表拉取失败: {str(exc)}"

    async def query_ths_intel(self, question: str):
        """同花顺 iFinD 问财式智能检索：用于新闻要点、市场舆情、综合条件等自然语言提问。"""
        try:
            return self.ths.smart_stock_picking_text(question.strip())
        except Exception as exc:
            return f"同花顺智能检索失败: {str(exc)}"

    @classmethod
    def get_all_tools(cls):
        t = cls()
        return [
            Tool(
                name="get_current_datetime",
                func=lambda c: None,
                coroutine=t.get_current_datetime,
                description=(
                    "获取当前时刻的时钟快照（调用瞬间由运行环境返回，非模型记忆）。"
                    "可选传入 IANA 时区名（如 Asia/Shanghai）以换算当地墙钟；可传空字符串仅要 UTC 与系统本地。"
                    "凡用户提到「今天」「此刻」「本周」等相对时间，或涉及时效的事实推理，应先调用本工具再作答。"
                ),
            ),
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
            Tool(
                name="get_recent_announcements",
                func=lambda c: None,
                coroutine=t.get_recent_announcements,
                description="输入股票代码如600519，获取近期公司公告标题列表，用于结合基本面与舆情做决策",
            ),
            Tool(
                name="get_ths_recent_reports",
                func=lambda c: None,
                coroutine=t.get_ths_recent_reports,
                description="输入股票代码，或「代码,天数」如600519,30（默认14天）；从同花顺 iFinD 拉取近期专题报表/披露类标题文本，用于新闻与合规信息侧写",
            ),
            Tool(
                name="query_ths_intel",
                func=lambda *a, **k: None,
                coroutine=t.query_ths_intel,
                description="输入一句自然语言问题或关键词（可含代码、板块、舆情方向），通过同花顺 iFinD 智能检索返回文本片段，用于新闻流与市场情绪侧写",
            ),
        ]