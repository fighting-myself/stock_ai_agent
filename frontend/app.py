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


st.set_page_config(page_title="股票 AI 投研决策系统", layout="wide")
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
        ["qwen3-vl-plus", "doubao", "deepseek-chat", "minimax-chat", "gpt-3.5-turbo", "vllm-local"],
        help="vllm-local 需在服务端配置 VLLM_BASE_URL 与 VLLM_MODEL（OpenAI 兼容网关）",
    )
    if st.button("健康检查", use_container_width=True):
        with st.spinner("正在检查服务状态..."):
            health, err = safe_get_json(f"{backend_url}/health", timeout=10)
        if err:
            st.error(err)
        else:
            bits = [f"status={health.get('status')}", f"tushare={'✓' if health.get('tushare_configured') else '✗'}"]
            if "vllm_ready" in health:
                bits.append(f"vllm={'✓' if health.get('vllm_ready') else '✗'}")
            if "ths_ifind_ready" in health:
                bits.append(f"ths={'✓' if health.get('ths_ifind_ready') else '✗'}")
            st.success("服务正常 · " + " ".join(bits))

main_tab, capability_tab, market_tab, risk_tab, strategy_tab = st.tabs(
    ["智能分析", "投研能力看板", "市场与技术", "风险与组合", "高级策略"]
)

with main_tab:
    st.subheader("AI 智能体问答")
    query = st.text_area("输入问题", "分析股票600519，获取当前价格并计算5日均线", height=110)
    if st.button("执行智能分析", type="primary"):
        with st.spinner("AI 正在思考中，请稍候..."):
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
        with st.spinner("正在生成量化总览..."):
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

with capability_tab:
    st.subheader("与简历对齐的项目叙事（演示给面试官）")
    st.caption("业务效果类表述以简历为准；本界面用于展示技术链路，不构成投资建议。")
    with st.expander("项目描述 / 职责 / 业绩（简历原文要点）", expanded=True):
        st.markdown(
            """
**项目描述**：布局 AI 金融投资领域；传统量化模型难以处理海量非结构化市场信息，导致决策滞后、风险识别不足；构建可解析新闻/财报/社交舆情并生成投资信号的智能系统。

**项目职责**：基于 LangGraph 实现决策编排，整合历史行情、公司公告与实时新闻流类数据；针对推理延迟采用 **vLLM** 做 OpenAI 兼容网关加速文本生成与信息抽取；系统 **容器化** 部署，便于在云环境弹性伸缩（单仓代码，前后端可独立扩缩）。

**项目业绩（简历口径）**：非结构化信息处理效率显著提升；策略回测超额收益（以实际回测为准）；vLLM 侧降低端到端响应延迟，为业务提供稳定推理底座。
            """
        )

    st.subheader("系统运行态（后端探测）")
    if st.button("刷新运行态", key="runtime_btn"):
        rt, err = safe_get_json(f"{backend_url}/api/system/runtime", timeout=15)
        if err:
            st.error(err)
        else:
            st.session_state["runtime"] = rt
    rt = st.session_state.get("runtime")
    if rt:
        c1, c2, c3, c4 = st.columns(4)
        c1.metric("Tushare", "已配置" if rt.get("tushare_configured") else "未配置")
        c2.metric("vLLM 就绪", "是" if rt.get("vllm_ready") else "否")
        c3.metric("同花顺 iFinD", "已配置" if rt.get("ths_ifind_ready") else "未配置")
        c4.metric("默认模型", rt.get("default_model", "-"))
        st.write(rt.get("stack", ""))
        st.info(rt.get("deployment_note", ""))
        for row in rt.get("structured_intel_sources") or []:
            st.caption(f"· **{row.get('label')}**：{row.get('role')}")

    st.divider()
    st.subheader("非结构化情报快照")
    st.caption("东方财富公告 + 可选同花顺专题报表 + 量价情绪代理 + 行情")
    ic1, ic2 = st.columns([1, 1])
    snap_code = ic1.text_input("标的代码", "600519", key="intel_snap_code")
    snap_ths_days = ic2.number_input("同花顺报表回溯天数", 7, 120, 14, key="intel_ths_days")
    if st.button("拉取情报快照", key="intel_snap_btn"):
        with st.spinner("正在聚合多源情报..."):
            snap, err = safe_get_json(
                f"{backend_url}/api/intel/snapshot",
                params={"code": snap_code, "notices_limit": 12, "ths_days": int(snap_ths_days)},
                timeout=120,
            )
        if err:
            st.error(err)
        else:
            st.session_state["intel_snap"] = snap
    snap = st.session_state.get("intel_snap")
    if snap:
        q = snap.get("quote") or {}
        metric_row(
            [
                {"label": "最新价", "value": q.get("price", "-"), "delta": f'{q.get("change_pct", "-")}%'},
                {"label": "情绪代理", "value": (snap.get("volume_sentiment_proxy") or {}).get("sentiment", "-")},
                {"label": "情绪分", "value": (snap.get("volume_sentiment_proxy") or {}).get("sentiment_score", "-")},
            ]
        )
        st.markdown("**近期公告标题**")
        for row in snap.get("announcements") or []:
            st.write(f"- {row.get('date', '')} {row.get('title', '')}")
        st.markdown("**同花顺专题报表 / 披露摘要**")
        st.text_area("ths_digest", snap.get("ths_disclosure_digest", ""), height=220, label_visibility="collapsed")

    st.divider()
    st.subheader("投资信号（自然语言结论）")
    st.caption("后端汇总事实后调用 LangGraph Agent，输出单段中文观察，便于演示「信号层」。")
    sig_code = st.text_input("标的代码", "600519", key="sig_code")
    sig_ths = st.checkbox("并入同花顺专题报表（需 token）", value=False, key="sig_ths")
    if st.button("生成投资信号", key="sig_btn", type="primary"):
        with st.spinner("正在生成自然语言投资观察..."):
            sig, err = safe_post_json(
                f"{backend_url}/api/intel/investment-signal",
                payload={
                    "code": sig_code,
                    "model_name": model_name,
                    "agent_type": agent_type,
                    "include_ths_reports": sig_ths,
                },
                timeout=180,
            )
        if err:
            st.error(err)
        else:
            st.session_state["intel_sig"] = sig
    sig = st.session_state.get("intel_sig")
    if sig:
        st.caption("数据来源：" + "、".join(sig.get("sources_used") or []))
        st.markdown(sig.get("signal_narrative", ""))

    st.divider()
    st.subheader("同花顺问财式检索（舆情 / 综合条件）")
    wq = st.text_input("自然语言问题", "贵州茅台 近期资金与舆情相关要点", key="ths_q")
    if st.button("执行问财检索", key="ths_btn"):
        with st.spinner("正在调用同花顺 iFinD..."):
            wencai, err = safe_post_json(f"{backend_url}/api/intel/ths-wencai", payload={"question": wq}, timeout=90)
        if err:
            st.error(err)
        else:
            st.session_state["ths_wencai"] = wencai
    wc = st.session_state.get("ths_wencai")
    if wc:
        st.text_area("wencai_out", wc.get("text", ""), height=260, label_visibility="collapsed")

    st.divider()
    st.subheader("双均线策略回测（量化可展示）")
    st.caption("调用已有 `/api/analysis/ma-backtest`，用于面试中「简单规则 + 超额」演示。")
    bc1, bc2 = st.columns(2)
    bt_code = bc1.text_input("标的代码", "600519", key="ma_bt_code")
    bt_days = bc2.slider("回测天数", 60, 360, 180, key="ma_bt_days")
    if st.button("运行 MA 回测", key="ma_bt_btn"):
        with st.spinner("回测中..."):
            bt, err = safe_get_json(
                f"{backend_url}/api/analysis/ma-backtest",
                params={"code": bt_code, "days": bt_days, "short_window": 5, "long_window": 20},
                timeout=90,
            )
        if err:
            st.error(err)
        else:
            st.session_state["ma_bt"] = bt
    bt = st.session_state.get("ma_bt")
    if bt:
        metric_row(
            [
                {"label": "策略收益%", "value": bt.get("strategy_return_pct")},
                {"label": "基准收益%", "value": bt.get("benchmark_return_pct")},
                {"label": "超额%", "value": bt.get("excess_return_pct")},
                {"label": "换仓次数", "value": bt.get("trades")},
            ]
        )

with market_tab:
    t1, t2, t3 = st.tabs(["行情快照", "历史走势", "技术指标"])
    with t1:
        code = st.text_input("股票代码", "600519", key="quote_code")
        if st.button("查询快照", key="quote_btn"):
            with st.spinner("正在查询行情快照..."):
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
            with st.spinner("正在加载历史走势..."):
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
            with st.spinner("正在计算技术指标..."):
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
            with st.spinner("正在评估风险..."):
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
            with st.spinner("正在计算 VaR/CVaR..."):
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
            with st.spinner("正在分析组合风险..."):
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
            with st.spinner("正在生成投研策略方案..."):
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
            with st.spinner("正在查询预测市场..."):
                data, err = safe_get_json(f"{backend_url}/api/alt/polymarket", params={"keyword": keyword, "limit": 10}, timeout=60)
            if err:
                st.error(err)
            else:
                st.dataframe(pd.DataFrame(data.get("markets", [])), use_container_width=True)
    elif feature == "大盘波动预警":
        code = st.text_input("指数代码", "000001", key="alert_code")
        if st.button("生成波动预警", key="alert_btn"):
            with st.spinner("正在分析大盘波动..."):
                data, err = safe_get_json(f"{backend_url}/api/alert/market-volatility", params={"code": code, "days": 60}, timeout=60)
            if err:
                st.error(err)
            else:
                st.info(data.get("message", ""))
    elif feature == "深度研报":
        topic = st.text_input("研报主题", "白酒行业景气度", key="report_topic")
        code = st.text_input("标的代码", "600519", key="report_code")
        if st.button("生成深度研报", key="report_btn"):
            with st.spinner("正在撰写深度研报..."):
                data, err = safe_post_json(f"{backend_url}/api/research/deep-report", payload={"topic": topic, "code": code}, timeout=180)
            if err:
                st.error(err)
            else:
                st.markdown(data.get("report", ""))
    elif feature == "专家辩论":
        topic = st.text_input("辩论主题", "当前估值是否透支未来增长", key="debate_topic")
        code = st.text_input("标的代码", "600519", key="debate_code")
        if st.button("发起专家辩论", key="debate_btn"):
            with st.spinner("专家正在辩论中..."):
                data, err = safe_post_json(f"{backend_url}/api/research/expert-debate", payload={"topic": topic, "code": code}, timeout=220)
            if err:
                st.error(err)
            else:
                st.write(data.get("judge", ""))
    elif feature == "板块/标的轮动对比":
        codes = st.text_input("代码列表（逗号分隔）", "600519,000858,601318,000001", key="rot_codes")
        if st.button("生成轮动排名", key="rot_btn"):
            with st.spinner("正在计算轮动排名..."):
                data, err = safe_get_json(f"{backend_url}/api/analysis/rotation", params={"codes": codes, "days": 60}, timeout=90)
            if err:
                st.error(err)
            else:
                st.dataframe(pd.DataFrame(data.get("ranking", [])), use_container_width=True)
