from fastapi import FastAPI
from uvicorn import run
from pydantic import BaseModel
from typing import List

from config.settings import settings
from core.workflow import StockAgentWorkflow
from data.calculator import StockCalculator
from data.tushare_client import TushareClient
from utils.logger import logger
from utils.response import ApiResponse, error_response, success_response

app = FastAPI(
    title="股票AI智能助手",
    description="LangGraph + 4种Agent范式 + 多模型对比",
    version="1.0.0",
)
ts_client = TushareClient()
calculator = StockCalculator()


class Position(BaseModel):
    code: str
    weight: float


@app.post("/api/agent/analyze", response_model=ApiResponse)
async def analyze_stock(
    query: str,
    agent_type: str = settings.DEFAULT_AGENT_TYPE,
    model_name: str = settings.DEFAULT_MODEL,
):
    try:
        workflow = StockAgentWorkflow(agent_type=agent_type, model_name=model_name)
        result = await workflow.run(query)
        return success_response(data=result, agent_type=agent_type, model=model_name)
    except Exception as exc:
        logger.error(f"分析执行失败: {str(exc)}")
        return error_response(message=str(exc))


@app.get("/health")
async def health():
    return {"status": "ok", "model": settings.DEFAULT_MODEL}


@app.get("/api/market/quote")
async def market_quote(code: str):
    return ts_client.get_quote_snapshot(code)


@app.get("/api/market/history")
async def market_history(code: str, days: int = 60):
    df = ts_client.get_recent_daily(code=code, days=days)
    closes = [float(v) for v in df["close"].tolist()]
    ma5 = calculator.moving_average(closes, 5)
    ma20 = calculator.moving_average(closes, 20)
    records = []
    for i, row in enumerate(df.to_dict(orient="records")):
        records.append(
            {
                "trade_date": row["trade_date"],
                "close": float(row["close"]),
                "ma5": ma5[i],
                "ma20": ma20[i],
            }
        )
    return {"code": code, "days": days, "history": records}


@app.get("/api/indicator/technical")
async def technical_indicator(code: str, days: int = 120):
    df = ts_client.get_recent_daily(code=code, days=days)
    closes = [float(v) for v in df["close"].tolist()]
    return {
        "code": code,
        "rsi14": calculator.rsi(closes, period=14),
        "macd": calculator.macd(closes),
    }


@app.get("/api/risk/summary")
async def risk_summary(code: str, days: int = 120):
    df = ts_client.get_recent_daily(code=code, days=days)
    closes = [float(v) for v in df["close"].tolist()]
    risk = calculator.risk_metrics(closes)
    return {"code": code, "days": days, **risk}


@app.post("/api/portfolio/analyze")
async def portfolio_analyze(positions: List[Position], days: int = 120):
    if not positions:
        return {"error": "positions 不能为空"}
    total_weight = sum(p.weight for p in positions)
    if total_weight <= 0:
        return {"error": "weight 合计必须大于 0"}
    norm_positions = [
        {"code": p.code, "weight": p.weight / total_weight}
        for p in positions
    ]
    result = []
    portfolio_vol = 0.0
    portfolio_mdd = 0.0
    for pos in norm_positions:
        df = ts_client.get_recent_daily(code=pos["code"], days=days)
        closes = [float(v) for v in df["close"].tolist()]
        risk = calculator.risk_metrics(closes)
        weighted_vol = risk["volatility_annual"] * pos["weight"]
        weighted_mdd = risk["max_drawdown_pct"] * pos["weight"]
        portfolio_vol += weighted_vol
        portfolio_mdd += weighted_mdd
        result.append(
            {
                "code": pos["code"],
                "weight": round(pos["weight"], 4),
                "volatility_annual": risk["volatility_annual"],
                "max_drawdown_pct": risk["max_drawdown_pct"],
                "weighted_volatility": round(weighted_vol, 2),
                "weighted_drawdown": round(weighted_mdd, 2),
            }
        )
    return {
        "days": days,
        "positions": result,
        "portfolio_volatility_annual": round(portfolio_vol, 2),
        "portfolio_drawdown_score": round(portfolio_mdd, 2),
    }


if __name__ == "__main__":
    logger.info("股票AI助手后端服务启动")
    run(app, host=settings.BACKEND_HOST, port=settings.BACKEND_PORT)
