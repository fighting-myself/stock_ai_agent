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
    html, body, [class*="css"] { font-family: "Segoe UI", "PingFang SC", "Hiragino Sans GB", "Microsoft YaHei", sans-serif; }
    [data-testid="stAppViewContainer"] > .main {
        background: linear-gradient(165deg, #f8fafc 0%, #eef2ff 45%, #f1f5f9 100%);
    }
    .block-container {
        padding-top: 1rem !important;
        padding-bottom: 2.5rem !important;
        max-width: 1180px;
    }
    h1 { font-weight: 700 !important; letter-spacing: -0.03em !important; color: #0f172a !important; }
    [data-testid="stHeader"] { background: rgba(255,255,255,0.85); backdrop-filter: blur(8px); }
    div[data-testid="stTabs"] [data-baseweb="tab-list"] {
        gap: 4px;
        background: rgba(255,255,255,0.6);
        border-radius: 12px;
        padding: 6px 8px;
        border: 1px solid #e2e8f0;
    }
    div[data-testid="stTabs"] button[data-baseweb="tab"] {
        border-radius: 8px;
        padding: 0.5rem 1rem;
    }
    div[data-testid="stTabs"] button[data-baseweb="tab"][aria-selected="true"] {
        background: #fff !important;
        box-shadow: 0 1px 2px rgba(15,23,42,0.08);
        color: #1d4ed8 !important;
        font-weight: 600;
    }
    div[data-testid="stVerticalBlockBorderWrapper"] {
        background: #ffffff !important;
        border: 1px solid #e2e8f0 !important;
        border-radius: 14px !important;
        padding: 1.1rem 1.35rem !important;
        box-shadow: 0 4px 24px rgba(15, 23, 42, 0.04);
    }
    div[data-testid="stMetric"] {
        background: linear-gradient(180deg, #ffffff 0%, #f8fafc 100%);
        border: 1px solid #e2e8f0;
        border-radius: 12px;
        padding: 10px 14px;
    }
    div[data-testid="stMetric"] * { color: #0f172a !important; }
    div[data-testid="stMetric"] label { color: #64748b !important; font-size: 0.8rem !important; }
    .sr-section-title {
        font-size: 1.05rem;
        font-weight: 600;
        color: #0f172a;
        margin: 0 0 0.15rem 0;
        letter-spacing: 0.01em;
    }
    .sr-section-desc { font-size: 0.82rem; color: #64748b; margin: 0 0 1rem 0; line-height: 1.5; }
    .sr-disclaimer { font-size: 0.78rem; color: #94a3b8; margin-bottom: 1.25rem; line-height: 1.55; }
    </style>
    """,
    unsafe_allow_html=True,
)

st.title("股票 AI 投研决策系统")
st.caption("多源数据融合 · LangGraph 决策编排 · 量化与披露联动分析")

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
            if "ext_intel_ready" in health:
                bits.append(f"扩展={'✓' if health.get('ext_intel_ready') else '✗'}")
            st.success("服务正常 · " + " ".join(bits))

main_tab, capability_tab, market_tab, risk_tab, strategy_tab = st.tabs(
    ["智能分析", "投研能力看板", "市场与技术", "风险与组合", "高级策略"]
)

with main_tab:
    with st.container(border=True):
        st.markdown('<p class="sr-section-title">智能体问答</p>', unsafe_allow_html=True)
        st.markdown(
            '<p class="sr-section-desc">自然语言下达分析任务；后端按所选 Agent 范式与模型执行工具调用与推理。</p>',
            unsafe_allow_html=True,
        )
        query = st.text_area("问题描述", "分析股票600519，获取当前价格并计算5日均线", height=110, label_visibility="visible")
        if st.button("执行智能分析", type="primary", use_container_width=True):
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

    with st.container(border=True):
        st.markdown('<p class="sr-section-title">量化驾驶舱总览</p>', unsafe_allow_html=True)
        st.markdown(
            '<p class="sr-section-desc">技术面、风险与估值维度的综合评分与建议动作摘要。</p>',
            unsafe_allow_html=True,
        )
        c1, c2 = st.columns([1, 1])
        code = c1.text_input("证券代码", "600519", key="overview_code")
        days = c2.slider("回看天数", 60, 300, 120, key="overview_days")
        if st.button("生成总览", key="overview_btn", use_container_width=True):
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
    st.markdown(
        '<p class="sr-disclaimer">本页功能仅供研究与内部演示；模型输出不构成投资建议或证券咨询服务。</p>',
        unsafe_allow_html=True,
    )

    with st.container(border=True):
        st.markdown('<p class="sr-section-title">发行人公开披露与证券行情综合监测</p>', unsafe_allow_html=True)
        st.markdown(
            '<p class="sr-section-desc">同步上市公司<strong>监管披露</strong>、<strong>二级市场行情</strong>、'
            "<strong>量价联动状态指征</strong>及可选<strong>扩展专题披露</strong>，形成单一标的的综合监测视图。</p>",
            unsafe_allow_html=True,
        )
        f1, f2 = st.columns([3, 2])
        with f1:
            snap_code = st.text_input("证券代码", "600519", key="intel_snap_code", help="A 股 6 位代码，可含或不含交易所后缀")
        with f2:
            snap_ths_days = st.number_input("扩展专题回溯天数", 7, 120, 14, key="intel_ths_days", help="扩展专题披露数据的查询窗口（按环境启用）")
        if st.button("加载综合监测数据", key="intel_snap_btn", type="primary", use_container_width=True):
            with st.spinner("正在拉取披露、行情与专题数据..."):
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
            ann = snap.get("announcements") or []
            if snap.get("announcements_ok", True) is False:
                st.warning("监管披露提要暂不可用（网络或上游响应异常）。行情与其余模块仍可使用。")
            q = snap.get("quote") or {}
            vp = snap.get("volume_sentiment_proxy") or {}
            metric_row(
                [
                    {"label": "最新成交价", "value": q.get("price", "—"), "delta": f'{q.get("change_pct", "—")}%'},
                    {"label": "量价状态指征", "value": vp.get("sentiment", "—")},
                    {"label": "量价综合评分（0–100）", "value": vp.get("sentiment_score", "—")},
                ]
            )
            left, right = st.columns([1, 1], gap="medium")
            with left:
                st.markdown("###### 监管披露与重大事项")
                if snap.get("announcements_ok", True) is False:
                    st.caption("本区块监管披露提要暂不可用。")
                elif not ann:
                    st.caption("暂无近期公告条目。")
                else:
                    for row in ann:
                        st.markdown(f"**{row.get('date', '')}** · {row.get('title', '')}")
            with right:
                st.markdown("###### 第三方专题数据摘要")
                digest = (
                    snap.get("extension_disclosure_digest") or snap.get("ths_disclosure_digest") or ""
                ).strip() or "（无返回内容）"
                st.code(digest, language=None)

    with st.container(border=True):
        st.markdown('<p class="sr-section-title">投研综述生成（自然语言）</p>', unsafe_allow_html=True)
        st.markdown(
            '<p class="sr-section-desc">在综合行情与披露事实基础上，由 LangGraph 编排生成<strong>单一标的</strong>的'
            "文字化投研综述；输出为连贯段落，便于内部研判留痕。</p>",
            unsafe_allow_html=True,
        )
        g1, g2 = st.columns([3, 2])
        with g1:
            sig_code = st.text_input("证券代码", "600519", key="sig_code")
        with g2:
            sig_ths = st.checkbox("纳入扩展专题披露", value=False, key="sig_ths", help="可选；未启用时综述仍基于行情与监管披露提要")
        if st.button("生成投研综述", key="sig_btn", type="primary", use_container_width=True):
            with st.spinner("正在生成综述..."):
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
            st.caption("事实来源：" + "、".join(sig.get("sources_used") or []))
            st.markdown("---")
            st.markdown(sig.get("signal_narrative", ""))

    with st.container(border=True):
        st.markdown('<p class="sr-section-title">扩展条件检索</p>', unsafe_allow_html=True)
        st.markdown(
            '<p class="sr-section-desc">面向标的或市场的<strong>自然语言条件查询</strong>；与智能体工具链互补，按部署环境返回检索文本。</p>',
            unsafe_allow_html=True,
        )
        wq = st.text_input("检索语句", "贵州茅台 近期资金与舆情相关要点", key="ths_q")
        if st.button("执行条件检索", key="ths_btn", use_container_width=True):
            with st.spinner("检索中…"):
                wencai, err = safe_post_json(f"{backend_url}/api/intel/ths-wencai", payload={"question": wq}, timeout=90)
            if err:
                st.error(err)
            else:
                st.session_state["ths_wencai"] = wencai
        wc = st.session_state.get("ths_wencai")
        if wc:
            st.markdown("###### 检索结果")
            st.code((wc.get("text") or "").strip() or "（空）", language=None)

    with st.container(border=True):
        st.markdown('<p class="sr-section-title">双移动平均线交叉策略回测</p>', unsafe_allow_html=True)
        st.markdown(
            '<p class="sr-section-desc">经典<strong>金叉 / 死叉</strong>规则：短期均线与长期均线交叉产生持仓信号，'
            "对比买入并持有的累计收益与超额收益。</p>",
            unsafe_allow_html=True,
        )
        b1, b2 = st.columns([2, 3])
        with b1:
            bt_code = st.text_input("证券代码", "600519", key="ma_bt_code")
        with b2:
            bt_days = st.slider("回测区间（交易日）", 60, 360, 180, key="ma_bt_days")
        if st.button("运行回测", key="ma_bt_btn", use_container_width=True):
            with st.spinner("回测计算中..."):
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
                    {"label": "策略累计收益（%）", "value": bt.get("strategy_return_pct")},
                    {"label": "基准累计收益（%）", "value": bt.get("benchmark_return_pct")},
                    {"label": "超额收益（%）", "value": bt.get("excess_return_pct")},
                    {"label": "信号换手次数", "value": bt.get("trades")},
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
