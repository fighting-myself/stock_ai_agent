from fastapi import FastAPI
from uvicorn import run
from pydantic import BaseModel
from typing import List
import httpx

from config.settings import settings
from core.workflow import StockAgentWorkflow
from data.calculator import StockCalculator
from data.market_intel_client import MarketIntelClient
from data.ths_ifind_client import ThsIfindClient
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
intel_client = MarketIntelClient()
ths_http = ThsIfindClient()


class Position(BaseModel):
    code: str
    weight: float


class ResearchRequest(BaseModel):
    topic: str
    code: str = "600519"


class ScenarioRequest(BaseModel):
    code: str
    event: str
    horizon_days: int = 20


class RebalanceRequest(BaseModel):
    positions: List[Position]
    days: int = 120


class InvestmentPlanRequest(BaseModel):
    code: str
    days: int = 120
    style: str = "balanced"  # conservative / balanced / aggressive


class InvestmentSignalRequest(BaseModel):
    """生成自然语言投资观察（不落库；模型输出为段落文本而非结构化 JSON）。"""

    code: str
    model_name: str | None = None
    agent_type: str = "react"
    include_ths_reports: bool = False


class ThsWencaiRequest(BaseModel):
    question: str


def _mask_url(url: str) -> str:
    if not (url or "").strip():
        return ""
    try:
        from urllib.parse import urlparse

        u = urlparse(url.strip())
        if u.scheme and u.netloc:
            return f"{u.scheme}://{u.netloc}/…"
    except Exception:
        pass
    return (url or "")[:40] + ("…" if len(url or "") > 40 else "")


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


def _calc_return_pct(closes: List[float]) -> float:
    if len(closes) < 2 or closes[0] == 0:
        return 0.0
    return round((closes[-1] - closes[0]) / closes[0] * 100, 2)


def _sentiment_payload(code: str, days: int = 60):
    df = ts_client.get_recent_daily(code=code, days=days)
    closes = [float(v) for v in df["close"].tolist()]
    vols = [float(v) for v in df["vol"].tolist()]
    ret20 = _calc_return_pct(closes[-20:] if len(closes) >= 20 else closes)
    vol_ratio = (sum(vols[-5:]) / 5) / ((sum(vols[-20:]) / 20) if len(vols) >= 20 else max(sum(vols) / len(vols), 1e-6))
    score = _clamp_score(50 + ret20 * 1.2 + (vol_ratio - 1) * 20)
    label = "乐观" if score >= 65 else ("中性" if score >= 40 else "谨慎")
    return {"code": code, "sentiment_score": score, "sentiment": label, "ret20_pct": ret20, "volume_ratio_5_20": round(vol_ratio, 2)}


def _style_base_exposure(style: str) -> float:
    if style == "conservative":
        return 0.35
    if style == "aggressive":
        return 0.75
    return 0.55


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
    return {
        "status": "ok",
        "default_model": settings.DEFAULT_MODEL,
        "tushare_configured": bool(settings.TUSHARE_TOKEN.strip()),
        "vllm_ready": settings.vllm_ready,
        "ths_ifind_ready": settings.ths_ifind_ready,
    }


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


@app.get("/api/alt/polymarket")
async def polymarket_markets(keyword: str = "stock", limit: int = 10):
    """免费 Polymarket 市场检索"""
    url = "https://gamma-api.polymarket.com/markets"
    try:
        async with httpx.AsyncClient(timeout=20) as client:
            resp = await client.get(url, params={"limit": 200, "active": True, "closed": False})
            resp.raise_for_status()
            markets = resp.json()
        key = keyword.lower().strip()
        filtered = []
        for m in markets:
            q = str(m.get("question", ""))
            desc = str(m.get("description", ""))
            if key in q.lower() or key in desc.lower():
                filtered.append(
                    {
                        "question": q,
                        "category": m.get("category"),
                        "endDate": m.get("endDate"),
                        "volume": m.get("volume"),
                        "liquidity": m.get("liquidity"),
                        "url": f"https://polymarket.com/event/{m.get('slug')}" if m.get("slug") else None,
                    }
                )
            if len(filtered) >= limit:
                break
        return {"keyword": keyword, "count": len(filtered), "markets": filtered}
    except Exception as exc:
        return {"keyword": keyword, "count": 0, "markets": [], "error": str(exc)}


@app.get("/api/alert/market-volatility")
async def market_volatility_alert(code: str = "000001", days: int = 60):
    df = ts_client.get_recent_daily(code=code, days=days)
    closes = [float(v) for v in df["close"].tolist()]
    rets = []
    for i in range(1, len(closes)):
        prev = closes[i - 1]
        rets.append(0.0 if prev == 0 else (closes[i] - prev) / prev * 100)
    current = rets[-1] if rets else 0.0
    vol = calculator.risk_metrics(closes)["volatility_annual"]
    level = "green"
    msg = "波动正常"
    if abs(current) >= 2.5 or vol >= 40:
        level = "red"
        msg = "高波动预警"
    elif abs(current) >= 1.5 or vol >= 28:
        level = "yellow"
        msg = "中等波动预警"
    return {"code": code, "current_daily_change_pct": round(current, 2), "annual_volatility_pct": vol, "level": level, "message": msg}


@app.post("/api/research/deep-report")
async def deep_research_report(req: ResearchRequest):
    workflow = StockAgentWorkflow(agent_type=settings.DEFAULT_AGENT_TYPE, model_name=settings.DEFAULT_MODEL)
    prompt = (
        f"请围绕 {req.topic} 生成一份深度研报，标的代码 {req.code}。"
        "结构包含：投资逻辑、产业与竞争、财务与估值、风险点、3个情景推演、结论建议。"
        "输出尽量结构化，使用小标题与要点。"
    )
    content = await workflow.run(prompt)
    return {"topic": req.topic, "code": req.code, "report": content}


@app.post("/api/research/expert-debate")
async def expert_debate(req: ResearchRequest):
    workflow = StockAgentWorkflow(agent_type=settings.DEFAULT_AGENT_TYPE, model_name=settings.DEFAULT_MODEL)
    bull = await workflow.run(f"你是多头分析师。围绕 {req.topic} 和 {req.code}，给出3个最强看多论点。")
    bear = await workflow.run(f"你是空头分析师。围绕 {req.topic} 和 {req.code}，给出3个最强看空论点。")
    judge = await workflow.run(
        f"基于以下多空观点给出裁决和仓位建议（0-100）：\n看多:{bull}\n看空:{bear}\n请输出: 结论、建议仓位、触发止损条件。"
    )
    return {"topic": req.topic, "code": req.code, "bull": bull, "bear": bear, "judge": judge}


@app.get("/api/analysis/technical-score")
async def technical_score(code: str, days: int = 120):
    df = ts_client.get_recent_daily(code=code, days=days)
    closes = [float(v) for v in df["close"].tolist()]
    highs = [float(v) for v in df["high"].tolist()]
    lows = [float(v) for v in df["low"].tolist()]
    rsi = calculator.rsi(closes, 14)
    macd = calculator.macd(closes)["macd"]
    kdj = calculator.kdj(highs, lows, closes, 9)
    ma20 = calculator.moving_average(closes, 20)[-1] or closes[-1]
    score = 50
    score += 10 if 45 <= rsi <= 70 else -8
    score += 12 if macd > 0 else -10
    score += 8 if closes[-1] >= ma20 else -8
    score += 8 if kdj["j"] < 90 else -6
    score = _clamp_score(score)
    signal = "偏多" if score >= 65 else ("中性" if score >= 45 else "偏空")
    return {"code": code, "score": score, "signal": signal, "rsi14": rsi, "macd": macd, "kdj_j": kdj["j"], "price_vs_ma20": round(closes[-1] - ma20, 2)}


@app.post("/api/analysis/scenario-impact")
async def scenario_impact(req: ScenarioRequest):
    workflow = StockAgentWorkflow(agent_type=settings.DEFAULT_AGENT_TYPE, model_name=settings.DEFAULT_MODEL)
    prompt = (
        f"事件冲击分析：标的 {req.code}，事件 {req.event}，观察期 {req.horizon_days} 天。"
        "请输出：短期影响、中期影响、利好利空概率、关键观测指标、交易建议。"
    )
    content = await workflow.run(prompt)
    return {"code": req.code, "event": req.event, "horizon_days": req.horizon_days, "analysis": content}


@app.post("/api/portfolio/rebalance")
async def portfolio_rebalance(req: RebalanceRequest):
    if not req.positions:
        return {"error": "positions 不能为空"}
    vols = []
    for p in req.positions:
        df = ts_client.get_recent_daily(code=p.code, days=req.days)
        closes = [float(v) for v in df["close"].tolist()]
        vol = calculator.risk_metrics(closes)["volatility_annual"]
        vols.append({"code": p.code, "vol": max(vol, 0.1)})
    inv_sum = sum(1 / x["vol"] for x in vols)
    rec = []
    for x in vols:
        w = (1 / x["vol"]) / inv_sum
        rec.append({"code": x["code"], "suggested_weight": round(w, 4), "volatility_annual": x["vol"]})
    return {"days": req.days, "method": "inverse-volatility", "suggestions": rec}


@app.get("/api/analysis/sentiment-proxy")
async def sentiment_proxy(code: str, days: int = 60):
    return _sentiment_payload(code, days)


@app.get("/api/system/runtime")
async def system_runtime():
    """供前端「投研看板」展示：架构说明、数据源与推理网关就绪状态（不含密钥）。"""
    return {
        "service": "stock-ai-agent-backend",
        "stack": "FastAPI + LangGraph（多 Agent 范式）+ Streamlit 控制台",
        "deployment_note": "单仓代码库；前后端可分别容器化部署（Dockerfile 分目录），便于云环境弹性伸缩。",
        "tushare_configured": bool(settings.TUSHARE_TOKEN.strip()),
        "vllm_ready": settings.vllm_ready,
        "vllm_base_url_masked": _mask_url(settings.VLLM_BASE_URL),
        "vllm_model": settings.VLLM_MODEL or None,
        "ths_ifind_ready": settings.ths_ifind_ready,
        "default_model": settings.DEFAULT_MODEL,
        "default_agent_type": settings.DEFAULT_AGENT_TYPE,
        "agent_paradigms": ["react", "plan_execute", "reflection", "rewoo"],
        "structured_intel_sources": [
            {"id": "tushare", "label": "历史行情 / 快照", "role": "量化与技术面事实"},
            {"id": "eastmoney_ann", "label": "东方财富公告", "role": "非结构化披露"},
            {"id": "ths_ifind", "label": "同花顺 iFinD", "role": "专题报表与问财式检索（需 refresh_token）"},
        ],
    }


@app.get("/api/intel/snapshot")
async def intel_snapshot(code: str, notices_limit: int = 10, ths_days: int = 14):
    """非结构化情报快照：公告 + 可选同花顺专题报表 + 行情，供界面「情报面板」。"""
    code = code.strip()
    notices = intel_client.fetch_recent_notices(code, page_size=min(max(notices_limit, 1), 30))
    quote = ts_client.get_quote_snapshot(code)
    ths_digest = ""
    if settings.ths_ifind_ready:
        try:
            ths_digest = ths_http.report_query_titles(code, days=min(max(ths_days, 1), 365))
        except Exception as exc:
            ths_digest = f"同花顺拉取失败: {exc}"
    else:
        ths_digest = "未配置 THS_IFIND_REFRESH_TOKEN，已跳过同花顺专题报表。"
    sent = _sentiment_payload(code, 60)
    return {
        "code": code,
        "quote": quote,
        "announcements": notices,
        "ths_disclosure_digest": ths_digest,
        "volume_sentiment_proxy": sent,
    }


@app.post("/api/intel/ths-wencai")
async def intel_ths_wencai(req: ThsWencaiRequest):
    """同花顺问财式检索（需 token）；返回自然语言可读的 JSON 文本片段。"""
    if not settings.ths_ifind_ready:
        return {"ok": False, "text": "未配置 THS_IFIND_REFRESH_TOKEN，无法调用同花顺问财接口。"}
    try:
        text = ths_http.smart_stock_picking_text(req.question.strip())
        return {"ok": True, "text": text}
    except Exception as exc:
        logger.error(f"ths wencai: {exc}")
        return {"ok": False, "text": f"调用失败: {exc}"}


@app.post("/api/intel/investment-signal")
async def intel_investment_signal(req: InvestmentSignalRequest):
    """综合行情、公告、量价情绪代理及可选同花顺报表，经 LLM 输出一段自然语言投资观察（非结构化）。"""
    code = req.code.strip()
    model_name = (req.model_name or settings.DEFAULT_MODEL).strip()
    quote = ts_client.get_quote_snapshot(code)
    notices = intel_client.fetch_recent_notices(code, page_size=10)
    ann_lines = "\n".join(f"- {n.get('date', '')} {n.get('title', '')}" for n in notices) or "- （无近期公告标题）"
    sent = _sentiment_payload(code, 60)
    ths_block = ""
    sources = ["Tushare 行情", "东方财富公告标题", "量价情绪代理指标"]
    if req.include_ths_reports and settings.ths_ifind_ready:
        try:
            ths_block = ths_http.report_query_titles(code, days=14)
            sources.append("同花顺 iFinD 专题报表")
        except Exception as exc:
            ths_block = f"（同花顺专题报表不可用：{exc}）"
    elif req.include_ths_reports:
        ths_block = "（未配置同花顺 token，已跳过）"
    facts = (
        f"标的代码: {code}\n"
        f"行情快照: {quote}\n"
        f"近端公告标题:\n{ann_lines}\n"
        f"量价情绪代理: {sent}\n"
        f"同花顺专题报表摘要:\n{ths_block or '（未启用或未配置）'}\n"
    )
    prompt = (
        "你是合规的投研写作助手。请仅根据下列「事实材料」撰写一段中文投资观察结论（自然语言段落），"
        "须包含：事实归纳、主要不确定性或风险、可跟踪的后续观察点。语气克制，不得承诺收益，不得输出 JSON 或键值表。\n\n"
        f"{facts}"
    )
    workflow = StockAgentWorkflow(agent_type=req.agent_type, model_name=model_name)
    narrative = await workflow.run(prompt)
    return {
        "code": code,
        "model": model_name,
        "agent_type": req.agent_type,
        "sources_used": sources,
        "signal_narrative": narrative,
    }


@app.get("/api/analysis/ma-backtest")
async def ma_backtest(code: str, short_window: int = 5, long_window: int = 20, days: int = 180):
    if short_window >= long_window:
        return {"error": "short_window 必须小于 long_window"}
    df = ts_client.get_recent_daily(code=code, days=days)
    closes = [float(v) for v in df["close"].tolist()]
    short_ma = calculator.moving_average(closes, short_window)
    long_ma = calculator.moving_average(closes, long_window)
    position = 0
    strategy_ret = 0.0
    benchmark_ret = 0.0
    trades = 0
    for i in range(1, len(closes)):
        if short_ma[i] is not None and long_ma[i] is not None:
            prev_pos = position
            position = 1 if short_ma[i] > long_ma[i] else 0
            if position != prev_pos:
                trades += 1
        daily_ret = 0.0 if closes[i - 1] == 0 else (closes[i] - closes[i - 1]) / closes[i - 1]
        strategy_ret += daily_ret * position
        benchmark_ret += daily_ret
    return {
        "code": code,
        "short_window": short_window,
        "long_window": long_window,
        "days": days,
        "strategy_return_pct": round(strategy_ret * 100, 2),
        "benchmark_return_pct": round(benchmark_ret * 100, 2),
        "excess_return_pct": round((strategy_ret - benchmark_ret) * 100, 2),
        "trades": trades,
    }


@app.get("/api/analysis/rotation")
async def rotation_compare(codes: str, days: int = 60):
    code_list = [x.strip() for x in codes.split(",") if x.strip()]
    rows = []
    for code in code_list:
        df = ts_client.get_recent_daily(code=code, days=days)
        closes = [float(v) for v in df["close"].tolist()]
        ret = _calc_return_pct(closes)
        risk = calculator.risk_metrics(closes)
        rows.append({"code": code, "return_pct": ret, "volatility_annual": risk["volatility_annual"]})
    rows = sorted(rows, key=lambda x: x["return_pct"], reverse=True)
    return {"days": days, "ranking": rows}


@app.post("/api/workflow/investment-plan")
async def investment_plan(req: InvestmentPlanRequest):
    overview = await workbench_overview(code=req.code, days=req.days)
    tech = await technical_score(code=req.code, days=req.days)
    alert = await market_volatility_alert(code="000001", days=min(req.days, 120))

    base = _style_base_exposure(req.style)
    score_adj = (overview["score"] - 50) / 100
    risk_penalty = min(0.25, max(0.0, overview["risk"]["volatility_annual"] / 100))
    alert_penalty = 0.15 if alert["level"] == "red" else (0.08 if alert["level"] == "yellow" else 0.0)
    target_exposure = max(0.1, min(0.95, base + score_adj - risk_penalty - alert_penalty))

    action = "持有观察"
    if tech["signal"] == "偏多" and overview["action"] in ["偏多", "中性"]:
        action = "分批买入"
    elif tech["signal"] == "偏空" or overview["action"] == "偏空":
        action = "减仓防守"

    stop_loss_pct = 6 if req.style == "aggressive" else (5 if req.style == "balanced" else 4)
    take_profit_pct = 15 if req.style == "aggressive" else (12 if req.style == "balanced" else 10)

    plan = {
        "market_state": {
            "overview_score": overview["score"],
            "risk_level": overview["risk_level"],
            "alert_level": alert["level"],
            "alert_message": alert["message"],
        },
        "positioning": {
            "style": req.style,
            "target_exposure": round(target_exposure, 2),
            "cash_ratio": round(1 - target_exposure, 2),
        },
        "execution": {
            "action": action,
            "entry_rule": "分3笔执行，每次约目标仓位的 1/3",
            "stop_loss_pct": stop_loss_pct,
            "take_profit_pct": take_profit_pct,
            "review_cycle_days": 5,
        },
        "checks": [
            "若波动预警为 red，暂停加仓",
            "若价格跌破支撑位且连续2天未收回，执行减仓",
            "若技术评分连续2次低于45，降至防守仓位",
        ],
    }

    workflow = StockAgentWorkflow(agent_type=settings.DEFAULT_AGENT_TYPE, model_name=settings.DEFAULT_MODEL)
    summary_prompt = (
        f"根据以下结构化投资计划，生成简洁的执行摘要（300字内）：{plan}。"
        "要求包含：当前判断、仓位建议、风控要点。"
    )
    summary = await workflow.run(summary_prompt)

    return {
        "code": req.code,
        "days": req.days,
        "style": req.style,
        "plan": plan,
        "summary": summary,
        "inputs": {
            "overview": overview,
            "technical_score": tech,
            "volatility_alert": alert,
        },
    }


if __name__ == "__main__":
    logger.info("股票AI助手后端服务启动")
    run(app, host=settings.BACKEND_HOST, port=settings.BACKEND_PORT)
