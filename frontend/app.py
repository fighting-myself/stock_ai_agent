import os

import httpx
import pandas as pd
import streamlit as st

BACKEND_URL = os.getenv("BACKEND_URL", "http://localhost:8001")


def safe_get_json(url: str, params=None, timeout: int = 60):
    try:
        resp = httpx.get(url, params=params, timeout=timeout)
        resp.raise_for_status()
        return resp.json(), None
    except Exception as exc:
        return None, str(exc)


def safe_post_json(url: str, params=None, payload=None, timeout: int = 60):
    try:
        resp = httpx.post(url, params=params, json=payload, timeout=timeout)
        resp.raise_for_status()
        return resp.json(), None
    except Exception as exc:
        return None, str(exc)


def metric_row(items):
    cols = st.columns(len(items))
    for c, item in zip(cols, items):
        c.metric(item["label"], item["value"], item.get("delta"))


st.set_page_config(page_title="企业投研分析平台", layout="wide")
st.markdown(
    """
    <style>
    .block-container {padding-top: 1.2rem;}
    div[data-testid="stMetric"] {
        background: #f8fafc;
        border: 1px solid #e2e8f0;
        border-radius: 12px;
        padding: 8px 12px;
    }
    div[data-testid="stMetric"] * {
        color: #0f172a !important;
    }
    </style>
    """,
    unsafe_allow_html=True,
)

st.title("企业级投研分析平台")
st.caption("多数据源 · 多因子分析 · 策略工作流 · 风控执行")

with st.sidebar:
    st.subheader("系统配置")
    backend_url = BACKEND_URL
    agent_type = st.selectbox("Agent范式", ["react", "plan_execute", "reflection", "rewoo"])
    model_name = st.selectbox(
        "模型",
        ["qwen3-vl-plus", "doubao", "deepseek-chat", "minimax-chat", "gpt-3.5-turbo"],
    )
    if st.button("健康检查", use_container_width=True):
        health, err = safe_get_json(f"{backend_url}/health", timeout=10)
        if err:
            st.error(err)
        else:
            st.success(f"服务正常: {health}")

main_tab, market_tab, risk_tab, strategy_tab = st.tabs(
    ["智能分析", "市场与技术", "风险与组合", "高级策略"]
)

with main_tab:
    st.subheader("AI 智能体问答")
    query = st.text_area("输入问题", "分析股票600519，获取当前价格并计算5日均线", height=110)
    if st.button("执行智能分析", type="primary"):
        data, err = safe_post_json(
            f"{backend_url}/api/agent/analyze",
            params={"query": query, "agent_type": agent_type, "model_name": model_name},
            timeout=120,
        )
        if err:
            st.error(err)
        elif data.get("success"):
            st.success("执行完成")
            st.write(data["data"])
            st.caption(f"Agent: {data.get('agent_type')} | Model: {data.get('model')}")
        else:
            st.error(data.get("error", "未知错误"))

    st.divider()
    st.subheader("量化驾驶舱总览")
    c1, c2 = st.columns([1, 1])
    code = c1.text_input("股票代码", "600519", key="overview_code")
    days = c2.slider("回看天数", 60, 300, 120, key="overview_days")
    if st.button("生成总览", key="overview_btn"):
        data, err = safe_get_json(f"{backend_url}/api/workbench/overview", params={"code": code, "days": days}, timeout=120)
        if err:
            st.error(err)
        else:
            metric_row(
                [
                    {"label": "综合评分", "value": data["score"]},
                    {"label": "风险等级", "value": data["risk_level"]},
                    {"label": "建议动作", "value": data["action"]},
                    {"label": "最新价", "value": data["quote"]["price"], "delta": f'{data["quote"]["change_pct"]}%'},
                ]
            )
            st.info(data.get("comment", ""))
            st.dataframe(
                pd.DataFrame(
                    [
                        {"指标": "RSI14", "值": data["technical"]["rsi14"]},
                        {"指标": "MACD", "值": data["technical"]["macd"]["macd"]},
                        {"指标": "VaR", "值": data["risk"]["var_pct"]},
                        {"指标": "CVaR", "值": data["risk"]["cvar_pct"]},
                        {"指标": "支撑位", "值": data["levels"]["support"]},
                        {"指标": "阻力位", "值": data["levels"]["resistance"]},
                    ]
                ),
                use_container_width=True,
            )

with market_tab:
    t1, t2, t3 = st.tabs(["行情快照", "历史走势", "技术指标"])
    with t1:
        code = st.text_input("股票代码", "600519", key="quote_code")
        if st.button("查询快照", key="quote_btn"):
            data, err = safe_get_json(f"{backend_url}/api/market/quote", params={"code": code})
            if err:
                st.error(err)
            else:
                metric_row(
                    [
                        {"label": "最新价", "value": data["price"], "delta": f'{data["change_pct"]}%'},
                        {"label": "最高", "value": data["high"]},
                        {"label": "最低", "value": data["low"]},
                        {"label": "数据源", "value": data.get("source", "-")},
                    ]
                )
    with t2:
        code = st.text_input("股票代码", "600519", key="history_code")
        days = st.slider("历史天数", 20, 240, 60, key="history_days")
        if st.button("查询走势", key="history_btn"):
            payload, err = safe_get_json(f"{backend_url}/api/market/history", params={"code": code, "days": days})
            if err:
                st.error(err)
            else:
                df = pd.DataFrame(payload["history"])
                st.line_chart(df.set_index("trade_date")[["close", "ma5", "ma20"]])
    with t3:
        code = st.text_input("股票代码", "600519", key="tech_code")
        days = st.slider("区间", 60, 300, 120, key="tech_days")
        if st.button("计算技术指标", key="tech_btn"):
            data, err = safe_get_json(f"{backend_url}/api/indicator/technical", params={"code": code, "days": days})
            if err:
                st.error(err)
            else:
                metric_row(
                    [
                        {"label": "RSI14", "value": data["rsi14"]},
                        {"label": "DIF", "value": data["macd"]["dif"]},
                        {"label": "DEA", "value": data["macd"]["dea"]},
                        {"label": "MACD", "value": data["macd"]["macd"]},
                    ]
                )

with risk_tab:
    r1, r2, r3 = st.tabs(["风险摘要", "VaR/CVaR", "组合分析"])
    with r1:
        code = st.text_input("股票代码", "600519", key="risk_code")
        days = st.slider("风险区间", 60, 300, 120, key="risk_days")
        if st.button("生成风险摘要", key="risk_btn"):
            data, err = safe_get_json(f"{backend_url}/api/risk/summary", params={"code": code, "days": days})
            if err:
                st.error(err)
            else:
                metric_row([{"label": "年化波动率(%)", "value": data["volatility_annual"]}, {"label": "最大回撤(%)", "value": data["max_drawdown_pct"]}])
    with r2:
        code = st.text_input("股票代码", "600519", key="var_code")
        days = st.slider("回看区间", 60, 300, 120, key="var_days")
        confidence = st.slider("置信度", 0.90, 0.99, 0.95, 0.01, key="var_conf")
        if st.button("计算 VaR/CVaR", key="var_btn"):
            data, err = safe_get_json(f"{backend_url}/api/risk/var", params={"code": code, "days": days, "confidence": confidence})
            if err:
                st.error(err)
            else:
                metric_row([{"label": "VaR(%)", "value": data["var_pct"]}, {"label": "CVaR(%)", "value": data["cvar_pct"]}])
    with r3:
        raw = st.text_area("组合输入（每行: code,weight）", "600519,0.4\n000858,0.3\n601318,0.3", key="portfolio_raw")
        days = st.slider("组合回看天数", 60, 300, 120, key="portfolio_days")
        if st.button("分析组合", key="portfolio_btn"):
            positions = []
            for line in raw.strip().splitlines():
                code, weight = line.split(",")
                positions.append({"code": code.strip(), "weight": float(weight.strip())})
            data, err = safe_post_json(f"{backend_url}/api/portfolio/analyze", params={"days": days}, payload=positions, timeout=120)
            if err:
                st.error(err)
            else:
                st.dataframe(pd.DataFrame(data.get("positions", [])), use_container_width=True)

with strategy_tab:
    feature = st.selectbox(
        "功能菜单",
        ["投研策略工作流", "Polymarket预测市场", "大盘波动预警", "深度研报", "专家辩论", "板块/标的轮动对比"],
        key="advanced_feature",
    )
    if feature == "投研策略工作流":
        c1, c2, c3 = st.columns(3)
        code = c1.text_input("股票代码", "600519", key="wf_code")
        days = c2.slider("分析天数", 60, 300, 120, key="wf_days")
        style = c3.selectbox("风格", ["conservative", "balanced", "aggressive"], index=1, key="wf_style")
        if st.button("生成投研策略方案", key="wf_btn", type="primary"):
            data, err = safe_post_json(f"{backend_url}/api/workflow/investment-plan", payload={"code": code, "days": days, "style": style}, timeout=180)
            if err:
                st.error(err)
            else:
                plan = data.get("plan", {})
                market = plan.get("market_state", {})
                pos = plan.get("positioning", {})
                metric_row(
                    [
                        {"label": "综合评分", "value": market.get("overview_score")},
                        {"label": "风险等级", "value": market.get("risk_level")},
                        {"label": "预警级别", "value": market.get("alert_level")},
                        {"label": "目标仓位", "value": pos.get("target_exposure")},
                    ]
                )
                st.write(data.get("summary", ""))
    elif feature == "Polymarket预测市场":
        keyword = st.text_input("关键词", "stock", key="pm_keyword")
        if st.button("查询预测市场", key="pm_btn"):
            data, err = safe_get_json(f"{backend_url}/api/alt/polymarket", params={"keyword": keyword, "limit": 10}, timeout=60)
            if err:
                st.error(err)
            else:
                st.dataframe(pd.DataFrame(data.get("markets", [])), use_container_width=True)
    elif feature == "大盘波动预警":
        code = st.text_input("指数代码", "000001", key="alert_code")
        if st.button("生成波动预警", key="alert_btn"):
            data, err = safe_get_json(f"{backend_url}/api/alert/market-volatility", params={"code": code, "days": 60}, timeout=60)
            if err:
                st.error(err)
            else:
                st.info(data.get("message", ""))
    elif feature == "深度研报":
        topic = st.text_input("研报主题", "白酒行业景气度", key="report_topic")
        code = st.text_input("标的代码", "600519", key="report_code")
        if st.button("生成深度研报", key="report_btn"):
            data, err = safe_post_json(f"{backend_url}/api/research/deep-report", payload={"topic": topic, "code": code}, timeout=180)
            if err:
                st.error(err)
            else:
                st.markdown(data.get("report", ""))
    elif feature == "专家辩论":
        topic = st.text_input("辩论主题", "当前估值是否透支未来增长", key="debate_topic")
        code = st.text_input("标的代码", "600519", key="debate_code")
        if st.button("发起专家辩论", key="debate_btn"):
            data, err = safe_post_json(f"{backend_url}/api/research/expert-debate", payload={"topic": topic, "code": code}, timeout=220)
            if err:
                st.error(err)
            else:
                st.write(data.get("judge", ""))
    elif feature == "板块/标的轮动对比":
        codes = st.text_input("代码列表（逗号分隔）", "600519,000858,601318,000001", key="rot_codes")
        if st.button("生成轮动排名", key="rot_btn"):
            data, err = safe_get_json(f"{backend_url}/api/analysis/rotation", params={"codes": codes, "days": 60}, timeout=90)
            if err:
                st.error(err)
            else:
                st.dataframe(pd.DataFrame(data.get("ranking", [])), use_container_width=True)
