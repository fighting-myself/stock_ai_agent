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

tab1, tab2, tab3, tab4, tab5 = st.tabs(
    ["1) 行情快照", "2) 历史走势", "3) RSI/MACD", "4) 风险摘要", "5) 组合分析"]
)

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
