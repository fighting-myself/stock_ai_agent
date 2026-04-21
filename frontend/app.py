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
        data, err = safe_get_json(
            f"{BACKEND_URL}/api/workbench/overview",
            params={"code": code, "days": days},
            timeout=120,
        )
        if err:
            st.error(f"总览请求失败: {err}")
            st.stop()
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
        data, err = safe_get_json(
            f"{BACKEND_URL}/api/fundamental/valuation",
            params={"code": code},
            timeout=60,
        )
        if err:
            st.error(f"估值接口请求失败: {err}")
            st.stop()
        c1, c2, c3 = st.columns(3)
        c1.metric("PE", data.get("pe"))
        c2.metric("PB", data.get("pb"))
        c3.metric("PS", data.get("ps"))
        c4, c5 = st.columns(2)
        c4.metric("总市值(万元)", data.get("total_mv"))
        c5.metric("流通市值(万元)", data.get("circ_mv"))
        if not data.get("available", True):
            st.warning(f"估值数据暂不可用：{data.get('reason', '未知原因')}")
        st.json(data)

st.divider()
st.subheader("🚀 高级投资分析（新增10项）")

feature = st.selectbox(
    "选择高级功能",
    [
        "投研策略工作流",
        "Polymarket预测市场",
        "大盘波动预警",
        "深度研报",
        "专家辩论",
        "技术分析评分卡",
        "事件冲击情景分析",
        "组合再平衡建议",
        "情绪代理指标",
        "均线策略回测",
        "板块/标的轮动对比",
    ],
    key="advanced_feature",
)

if feature == "Polymarket预测市场":
    pass

if feature == "投研策略工作流":
    code = st.text_input("股票代码", "600519", key="wf_code")
    days = st.slider("分析天数", min_value=60, max_value=300, value=120, key="wf_days")
    style = st.selectbox("风格", ["conservative", "balanced", "aggressive"], index=1, key="wf_style")
    if st.button("生成投研策略方案", key="wf_btn"):
        data, err = safe_post_json(
            f"{BACKEND_URL}/api/workflow/investment-plan",
            payload={"code": code, "days": days, "style": style},
            timeout=180,
        )
        if err:
            st.error(err)
        else:
            st.markdown("### 执行摘要")
            st.write(data.get("summary", ""))
            plan = data.get("plan", {})
            market = plan.get("market_state", {})
            pos = plan.get("positioning", {})
            exe = plan.get("execution", {})
            c1, c2, c3 = st.columns(3)
            c1.metric("综合评分", market.get("overview_score"))
            c2.metric("风险等级", market.get("risk_level"))
            c3.metric("预警级别", market.get("alert_level"))
            c4, c5 = st.columns(2)
            c4.metric("目标仓位", pos.get("target_exposure"))
            c5.metric("现金比例", pos.get("cash_ratio"))
            st.markdown("### 执行计划")
            st.write(exe)
            st.markdown("### 风控检查清单")
            for item in plan.get("checks", []):
                st.write(f"- {item}")
            st.json(data)

elif feature == "Polymarket预测市场":
    keyword = st.text_input("关键词", "stock", key="pm_keyword")
    limit = st.slider("返回条数", min_value=5, max_value=30, value=10, key="pm_limit")
    if st.button("查询预测市场", key="pm_btn"):
        data, err = safe_get_json(f"{BACKEND_URL}/api/alt/polymarket", params={"keyword": keyword, "limit": limit}, timeout=60)
        if err:
            st.error(err)
        else:
            st.dataframe(pd.DataFrame(data.get("markets", [])), use_container_width=True)
            st.json(data)

elif feature == "大盘波动预警":
    code = st.text_input("指数代码", "000001", key="alert_code")
    days = st.slider("观察天数", min_value=20, max_value=240, value=60, key="alert_days")
    if st.button("生成波动预警", key="alert_btn"):
        data, err = safe_get_json(f"{BACKEND_URL}/api/alert/market-volatility", params={"code": code, "days": days}, timeout=60)
        if err:
            st.error(err)
        else:
            if data["level"] == "red":
                st.error(data["message"])
            elif data["level"] == "yellow":
                st.warning(data["message"])
            else:
                st.success(data["message"])
            st.json(data)

elif feature == "深度研报":
    topic = st.text_input("研报主题", "白酒行业景气度", key="report_topic")
    code = st.text_input("标的代码", "600519", key="report_code")
    if st.button("生成深度研报", key="report_btn"):
        data, err = safe_post_json(f"{BACKEND_URL}/api/research/deep-report", payload={"topic": topic, "code": code}, timeout=180)
        if err:
            st.error(err)
        else:
            st.markdown(data.get("report", ""))

elif feature == "专家辩论":
    topic = st.text_input("辩论主题", "当前估值是否透支未来增长", key="debate_topic")
    code = st.text_input("标的代码", "600519", key="debate_code")
    if st.button("发起专家辩论", key="debate_btn"):
        data, err = safe_post_json(f"{BACKEND_URL}/api/research/expert-debate", payload={"topic": topic, "code": code}, timeout=220)
        if err:
            st.error(err)
        else:
            st.markdown("### 多头观点")
            st.write(data.get("bull", ""))
            st.markdown("### 空头观点")
            st.write(data.get("bear", ""))
            st.markdown("### 裁决")
            st.write(data.get("judge", ""))

elif feature == "技术分析评分卡":
    code = st.text_input("股票代码", "600519", key="tscore_code")
    days = st.slider("计算天数", min_value=60, max_value=300, value=120, key="tscore_days")
    if st.button("生成技术评分", key="tscore_btn"):
        data, err = safe_get_json(f"{BACKEND_URL}/api/analysis/technical-score", params={"code": code, "days": days}, timeout=60)
        if err:
            st.error(err)
        else:
            st.metric("技术评分", data["score"])
            st.metric("信号", data["signal"])
            st.json(data)

elif feature == "事件冲击情景分析":
    code = st.text_input("股票代码", "600519", key="scene_code")
    event = st.text_area("事件描述", "若出现超预期降息，对白酒龙头影响如何？", key="scene_event")
    horizon_days = st.slider("观察窗口(天)", min_value=5, max_value=120, value=20, key="scene_horizon")
    if st.button("分析事件冲击", key="scene_btn"):
        data, err = safe_post_json(
            f"{BACKEND_URL}/api/analysis/scenario-impact",
            payload={"code": code, "event": event, "horizon_days": horizon_days},
            timeout=180,
        )
        if err:
            st.error(err)
        else:
            st.write(data.get("analysis", ""))

elif feature == "组合再平衡建议":
    raw = st.text_area("组合输入（每行: code,weight）", "600519,0.4\n000858,0.3\n601318,0.3", key="rebalance_raw")
    days = st.slider("历史窗口", min_value=60, max_value=300, value=120, key="rebalance_days")
    if st.button("生成再平衡建议", key="rebalance_btn"):
        positions = []
        for line in raw.strip().splitlines():
            code, weight = line.split(",")
            positions.append({"code": code.strip(), "weight": float(weight.strip())})
        data, err = safe_post_json(
            f"{BACKEND_URL}/api/portfolio/rebalance",
            payload={"positions": positions, "days": days},
            timeout=120,
        )
        if err:
            st.error(err)
        else:
            st.dataframe(pd.DataFrame(data.get("suggestions", [])), use_container_width=True)
            st.json(data)

elif feature == "情绪代理指标":
    code = st.text_input("股票代码", "600519", key="sent_code")
    days = st.slider("观察天数", min_value=30, max_value=240, value=60, key="sent_days")
    if st.button("计算情绪指标", key="sent_btn"):
        data, err = safe_get_json(f"{BACKEND_URL}/api/analysis/sentiment-proxy", params={"code": code, "days": days}, timeout=60)
        if err:
            st.error(err)
        else:
            st.metric("情绪分", data["sentiment_score"])
            st.metric("情绪标签", data["sentiment"])
            st.json(data)

elif feature == "均线策略回测":
    code = st.text_input("股票代码", "600519", key="bt_code")
    short_w = st.slider("短均线", min_value=3, max_value=20, value=5, key="bt_short")
    long_w = st.slider("长均线", min_value=10, max_value=60, value=20, key="bt_long")
    days = st.slider("回测天数", min_value=60, max_value=500, value=180, key="bt_days")
    if st.button("运行回测", key="bt_btn"):
        data, err = safe_get_json(
            f"{BACKEND_URL}/api/analysis/ma-backtest",
            params={"code": code, "short_window": short_w, "long_window": long_w, "days": days},
            timeout=60,
        )
        if err:
            st.error(err)
        else:
            st.metric("策略收益(%)", data.get("strategy_return_pct", 0))
            st.metric("基准收益(%)", data.get("benchmark_return_pct", 0))
            st.metric("超额收益(%)", data.get("excess_return_pct", 0))
            st.json(data)

elif feature == "板块/标的轮动对比":
    codes = st.text_input("代码列表（逗号分隔）", "600519,000858,601318,000001", key="rot_codes")
    days = st.slider("对比天数", min_value=20, max_value=240, value=60, key="rot_days")
    if st.button("生成轮动排名", key="rot_btn"):
        data, err = safe_get_json(f"{BACKEND_URL}/api/analysis/rotation", params={"codes": codes, "days": days}, timeout=90)
        if err:
            st.error(err)
        else:
            st.dataframe(pd.DataFrame(data.get("ranking", [])), use_container_width=True)
            st.json(data)
