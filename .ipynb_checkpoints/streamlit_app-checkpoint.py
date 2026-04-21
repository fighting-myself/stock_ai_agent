import streamlit as st
import httpx

BACKEND_URL = "http://localhost:8000"

st.set_page_config(page_title="股票AI助手", layout="wide")
st.title("📈 股票AI智能助手（LangGraph多智能体）")

with st.sidebar:
    st.subheader("⚙️ 配置中心")
    agent_type = st.selectbox(
        "选择Agent范式",
        ["react", "plan_execute", "reflection", "rewoo"]
    )
    model_name = st.selectbox(
        "选择模型",
        [
            "qwen3-vl-plus",
            "doubao",
            "deepseek-chat",
            "minimax-chat",
            "gpt-3.5-turbo"
        ]
    )

query = st.text_input(
    "请输入股票查询",
    "分析股票600519，获取当前价格并计算5日均线"
)

if st.button("🚀 开始智能分析"):
    with st.spinner("智能体执行中..."):
        try:
            resp = httpx.post(
                f"{BACKEND_URL}/api/agent/analyze",
                params={
                    "query": query,
                    "agent_type": agent_type,
                    "model_name": model_name
                },
                timeout=60
            )
            data = resp.json()

            if data.get("success"):
                st.success("✅ 执行完成")
                st.markdown("### 分析结果")
                st.write(data["data"])
                st.caption(f"🤖 智能体: {data['agent_type']} | 🧠 模型: {data['model']}")
            else:
                st.error(f"❌ 失败: {data.get('error')}")
        except Exception as e:
            st.error(f"请求异常: {str(e)}")