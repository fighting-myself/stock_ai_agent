import os

import httpx
import pandas as pd
import streamlit as st

BACKEND_URL = os.getenv("BACKEND_URL", "http://localhost:8001")

st.set_page_config(page_title="股票AI助手", layout="wide")
st.title("📈 股票AI智能助手（LangGraph多智能体）")

with st.sidebar:
    st.subheader("⚙️ 配置中心")
    agent_type = st.selectbox("选择Agent范式", ["react", "plan_execute", "reflection", "rewoo"])
    model_name = st.selectbox(
        "选择模型",
        ["qwen3-vl-plus", "doubao", "deepseek-chat", "minimax-chat", "gpt-3.5-turbo"],
    )

query = st.text_input("请输入股票查询", "分析股票600519，获取当前价格并计算5日均线")

if st.button("🚀 开始智能分析"):
    with st.spinner("智能体执行中..."):
        try:
            resp = httpx.post(
                f"{BACKEND_URL}/api/agent/analyze",
                params={"query": query, "agent_type": agent_type, "model_name": model_name},
                timeout=60,
            )
            data = resp.json()

            if data.get("success"):
                st.success("✅ 执行完成")
                st.markdown("### 分析结果")
                st.write(data["data"])
                st.caption(f"🤖 智能体: {data['agent_type']} | 🧠 模型: {data['model']}")
            else:
                st.error(f"❌ 失败: {data.get('error')}")
        except Exception as exc:
            st.error(f"请求异常: {str(exc)}")

st.divider()
st.subheader("📊 金融功能面板")

tab0, tab1, tab2, tab3, tab4, tab5, tab6, tab7, tab8, tab9, tab10 = st.tabs(
    [
        "⭐ 工作台总览",
        "1) 行情快照",
        "2) 历史走势",
        "3) RSI/MACD",
        "4) 风险摘要",
        "5) 组合分析",
        "6) 布林带",
        "7) KDJ",
        "8) VaR/CVaR",
        "9) 支撑阻力",
        "10) 估值面板",
    ]
)

with tab0:
    code = st.text_input("股票代码", "600519", key="overview_code")
    days = st.slider("总览回看区间", min_value=60, max_value=300, value=120, key="overview_days")
    if st.button("生成量化总览", key="overview_btn"):
        resp = httpx.get(
            f"{BACKEND_URL}/api/workbench/overview",
            params={"code": code, "days": days},
            timeout=120,
        )
        data = resp.json()
        c1, c2, c3 = st.columns(3)
        c1.metric("综合评分", data["score"])
        c2.metric("风险等级", data["risk_level"])
        c3.metric("建议动作", data["action"])
        st.info(data["comment"])
        c4, c5, c6 = st.columns(3)
        c4.metric("最新价", data["quote"]["price"], f'{data["quote"]["change_pct"]}%')
        c5.metric("年化波动率(%)", data["risk"]["volatility_annual"])
        c6.metric("最大回撤(%)", data["risk"]["max_drawdown_pct"])
        st.markdown("#### 关键指标快照")
        metric_df = pd.DataFrame(
            [
                {"指标": "RSI14", "值": data["technical"]["rsi14"]},
                {"指标": "MACD", "值": data["technical"]["macd"]["macd"]},
                {"指标": "布林上轨", "值": data["technical"]["boll"]["upper"]},
                {"指标": "布林下轨", "值": data["technical"]["boll"]["lower"]},
                {"指标": "K", "值": data["technical"]["kdj"]["k"]},
                {"指标": "D", "值": data["technical"]["kdj"]["d"]},
                {"指标": "J", "值": data["technical"]["kdj"]["j"]},
                {"指标": "VaR(%)", "值": data["risk"]["var_pct"]},
                {"指标": "CVaR(%)", "值": data["risk"]["cvar_pct"]},
                {"指标": "PE", "值": data["valuation"]["pe"]},
                {"指标": "PB", "值": data["valuation"]["pb"]},
                {"指标": "支撑位", "值": data["levels"]["support"]},
                {"指标": "阻力位", "值": data["levels"]["resistance"]},
                {"指标": "位置/信号", "值": data["levels"]["signal"]},
            ]
        )
        st.dataframe(metric_df, use_container_width=True)
        st.json(data)

with tab1:
    code = st.text_input("股票代码", "600519", key="quote_code")
    if st.button("查询快照", key="quote_btn"):
        resp = httpx.get(f"{BACKEND_URL}/api/market/quote", params={"code": code}, timeout=60)
        data = resp.json()
        c1, c2, c3 = st.columns(3)
        c1.metric("最新价", data["price"], f'{data["change_pct"]}%')
        c2.metric("最高", data["high"])
        c3.metric("最低", data["low"])
        st.json(data)

with tab2:
    code = st.text_input("股票代码", "600519", key="history_code")
    days = st.slider("历史天数", min_value=20, max_value=240, value=60, key="history_days")
    if st.button("查询历史走势", key="history_btn"):
        resp = httpx.get(
            f"{BACKEND_URL}/api/market/history",
            params={"code": code, "days": days},
            timeout=60,
        )
        payload = resp.json()
        df = pd.DataFrame(payload["history"])
        st.line_chart(df.set_index("trade_date")[["close", "ma5", "ma20"]])
        st.dataframe(df.tail(20), use_container_width=True)

with tab3:
    code = st.text_input("股票代码", "600519", key="tech_code")
    days = st.slider("计算区间", min_value=60, max_value=300, value=120, key="tech_days")
    if st.button("计算 RSI/MACD", key="tech_btn"):
        resp = httpx.get(
            f"{BACKEND_URL}/api/indicator/technical",
            params={"code": code, "days": days},
            timeout=60,
        )
        data = resp.json()
        c1, c2, c3, c4 = st.columns(4)
        c1.metric("RSI14", data["rsi14"])
        c2.metric("DIF", data["macd"]["dif"])
        c3.metric("DEA", data["macd"]["dea"])
        c4.metric("MACD", data["macd"]["macd"])
        st.json(data)

with tab4:
    code = st.text_input("股票代码", "600519", key="risk_code")
    days = st.slider("风险区间", min_value=60, max_value=300, value=120, key="risk_days")
    if st.button("生成风险摘要", key="risk_btn"):
        resp = httpx.get(
            f"{BACKEND_URL}/api/risk/summary",
            params={"code": code, "days": days},
            timeout=60,
        )
        data = resp.json()
        c1, c2 = st.columns(2)
        c1.metric("年化波动率(%)", data["volatility_annual"])
        c2.metric("最大回撤(%)", data["max_drawdown_pct"])
        st.json(data)

with tab5:
    raw = st.text_area(
        "组合输入（每行: code,weight）",
        value="600519,0.4\n000858,0.3\n601318,0.3",
        key="portfolio_raw",
    )
    days = st.slider("组合回看天数", min_value=60, max_value=300, value=120, key="portfolio_days")
    if st.button("分析组合", key="portfolio_btn"):
        positions = []
        for line in raw.strip().splitlines():
            code, weight = line.split(",")
            positions.append({"code": code.strip(), "weight": float(weight.strip())})
        resp = httpx.post(
            f"{BACKEND_URL}/api/portfolio/analyze",
            params={"days": days},
            json=positions,
            timeout=120,
        )
        data = resp.json()
        st.metric("组合年化波动率(%)", data.get("portfolio_volatility_annual", 0))
        st.metric("组合回撤评分", data.get("portfolio_drawdown_score", 0))
        if "positions" in data:
            st.dataframe(pd.DataFrame(data["positions"]), use_container_width=True)
        st.json(data)

with tab6:
    code = st.text_input("股票代码", "600519", key="boll_code")
    days = st.slider("回看区间", min_value=40, max_value=300, value=90, key="boll_days")
    window = st.slider("布林窗口", min_value=10, max_value=60, value=20, key="boll_window")
    if st.button("计算布林带", key="boll_btn"):
        resp = httpx.get(
            f"{BACKEND_URL}/api/indicator/bollinger",
            params={"code": code, "days": days, "window": window},
            timeout=60,
        )
        data = resp.json()
        c1, c2, c3 = st.columns(3)
        c1.metric("中轨", data["mid"])
        c2.metric("上轨", data["upper"])
        c3.metric("下轨", data["lower"])
        st.json(data)

with tab7:
    code = st.text_input("股票代码", "600519", key="kdj_code")
    days = st.slider("回看区间", min_value=40, max_value=300, value=90, key="kdj_days")
    period = st.slider("KDJ 周期", min_value=5, max_value=30, value=9, key="kdj_period")
    if st.button("计算 KDJ", key="kdj_btn"):
        resp = httpx.get(
            f"{BACKEND_URL}/api/indicator/kdj",
            params={"code": code, "days": days, "period": period},
            timeout=60,
        )
        data = resp.json()
        c1, c2, c3 = st.columns(3)
        c1.metric("K", data["k"])
        c2.metric("D", data["d"])
        c3.metric("J", data["j"])
        st.json(data)

with tab8:
    code = st.text_input("股票代码", "600519", key="var_code")
    days = st.slider("回看区间", min_value=60, max_value=300, value=120, key="var_days")
    confidence = st.slider("置信度", min_value=0.90, max_value=0.99, value=0.95, step=0.01, key="var_conf")
    if st.button("计算 VaR/CVaR", key="var_btn"):
        resp = httpx.get(
            f"{BACKEND_URL}/api/risk/var",
            params={"code": code, "days": days, "confidence": confidence},
            timeout=60,
        )
        data = resp.json()
        c1, c2 = st.columns(2)
        c1.metric("VaR(%)", data["var_pct"])
        c2.metric("CVaR(%)", data["cvar_pct"])
        st.json(data)

with tab9:
    code = st.text_input("股票代码", "600519", key="sr_code")
    days = st.slider("回看区间", min_value=40, max_value=300, value=120, key="sr_days")
    lookback = st.slider("支撑阻力窗口", min_value=10, max_value=60, value=20, key="sr_lookback")
    if st.button("分析支撑阻力", key="sr_btn"):
        resp = httpx.get(
            f"{BACKEND_URL}/api/strategy/support-resistance",
            params={"code": code, "days": days, "lookback": lookback},
            timeout=60,
        )
        data = resp.json()
        c1, c2, c3 = st.columns(3)
        c1.metric("当前价", data["price"])
        c2.metric("支撑位", data["support"])
        c3.metric("阻力位", data["resistance"])
        st.info(f"信号：{data['signal']}")
        st.json(data)

with tab10:
    code = st.text_input("股票代码", "600519", key="valuation_code")
    if st.button("查询估值面板", key="valuation_btn"):
        resp = httpx.get(
            f"{BACKEND_URL}/api/fundamental/valuation",
            params={"code": code},
            timeout=60,
        )
        data = resp.json()
        c1, c2, c3 = st.columns(3)
        c1.metric("PE", data.get("pe"))
        c2.metric("PB", data.get("pb"))
        c3.metric("PS", data.get("ps"))
        c4, c5 = st.columns(2)
        c4.metric("总市值(万元)", data.get("total_mv"))
        c5.metric("流通市值(万元)", data.get("circ_mv"))
        st.json(data)
