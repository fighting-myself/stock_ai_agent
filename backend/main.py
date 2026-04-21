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


def _clamp_score(score: float) -> int:
    return max(0, min(100, int(round(score))))


def _risk_level(score: int) -> str:
    if score >= 70:
        return "低风险"
    if score >= 40:
        return "中风险"
    return "高风险"


def _action_by_score(score: int, trend_signal: str, rsi14: float, pe: float):
    if score >= 70 and trend_signal in ["near_breakout_up", "range"] and rsi14 < 75:
        return "偏多", "风险可控，可考虑分批建仓"
    if score < 40 or trend_signal == "near_breakdown_down" or rsi14 > 82:
        return "偏空", "风险偏高，建议降低仓位或观望"
    if pe and pe > 60:
        return "谨慎", "估值偏高，建议等待更好性价比"
    return "中性", "指标分化，建议轻仓跟踪"


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


@app.get("/api/indicator/bollinger")
async def indicator_bollinger(code: str, days: int = 90, window: int = 20):
    df = ts_client.get_recent_daily(code=code, days=days)
    closes = [float(v) for v in df["close"].tolist()]
    bands = calculator.bollinger_bands(closes, window=window, std_factor=2.0)
    return {"code": code, "window": window, **bands}


@app.get("/api/indicator/kdj")
async def indicator_kdj(code: str, days: int = 90, period: int = 9):
    df = ts_client.get_recent_daily(code=code, days=days)
    highs = [float(v) for v in df["high"].tolist()]
    lows = [float(v) for v in df["low"].tolist()]
    closes = [float(v) for v in df["close"].tolist()]
    kdj = calculator.kdj(highs, lows, closes, period=period)
    return {"code": code, "period": period, **kdj}


@app.get("/api/risk/var")
async def risk_var(code: str, days: int = 120, confidence: float = 0.95):
    df = ts_client.get_recent_daily(code=code, days=days)
    closes = [float(v) for v in df["close"].tolist()]
    metrics = calculator.var_cvar(closes, confidence=confidence)
    return {"code": code, "days": days, "confidence": confidence, **metrics}


@app.get("/api/strategy/support-resistance")
async def strategy_support_resistance(code: str, days: int = 120, lookback: int = 20):
    df = ts_client.get_recent_daily(code=code, days=days)
    highs = [float(v) for v in df["high"].tolist()]
    lows = [float(v) for v in df["low"].tolist()]
    closes = [float(v) for v in df["close"].tolist()]
    levels = calculator.support_resistance(highs, lows, closes, lookback=lookback)
    return {"code": code, "lookback": lookback, **levels}


@app.get("/api/fundamental/valuation")
async def fundamental_valuation(code: str):
    return ts_client.get_daily_basic_latest(code=code)


@app.get("/api/workbench/overview")
async def workbench_overview(code: str, days: int = 120):
    quote = ts_client.get_quote_snapshot(code=code)
    df = ts_client.get_recent_daily(code=code, days=days)
    closes = [float(v) for v in df["close"].tolist()]
    highs = [float(v) for v in df["high"].tolist()]
    lows = [float(v) for v in df["low"].tolist()]
    technical = {
        "rsi14": calculator.rsi(closes, period=14),
        "macd": calculator.macd(closes),
        "boll": calculator.bollinger_bands(closes, window=20, std_factor=2.0),
        "kdj": calculator.kdj(highs, lows, closes, period=9),
    }
    risk = calculator.risk_metrics(closes)
    tail_risk = calculator.var_cvar(closes, confidence=0.95)
    levels = calculator.support_resistance(highs, lows, closes, lookback=20)
    valuation = ts_client.get_daily_basic_latest(code=code)

    vol_score = max(0.0, 100 - risk["volatility_annual"] * 2)
    mdd_score = max(0.0, 100 + risk["max_drawdown_pct"] * 2)  # drawdown 是负值
    var_score = max(0.0, 100 + tail_risk["var_pct"] * 5)  # var 是负值
    pe = valuation["pe"] if valuation["pe"] is not None else 30.0
    pe_score = 100.0 if pe <= 0 else max(0.0, min(100.0, 100 - pe))
    rsi_penalty = 0.0 if technical["rsi14"] <= 70 else min(30.0, (technical["rsi14"] - 70) * 2)
    raw_score = vol_score * 0.3 + mdd_score * 0.25 + var_score * 0.2 + pe_score * 0.25 - rsi_penalty
    score = _clamp_score(raw_score)
    level = _risk_level(score)
    action, comment = _action_by_score(score, levels["signal"], technical["rsi14"], pe)

    return {
        "code": code,
        "score": score,
        "risk_level": level,
        "action": action,
        "comment": comment,
        "quote": quote,
        "technical": technical,
        "risk": {**risk, **tail_risk},
        "levels": levels,
        "valuation": valuation,
    }


if __name__ == "__main__":
    logger.info("股票AI助手后端服务启动")
    run(app, host=settings.BACKEND_HOST, port=settings.BACKEND_PORT)
