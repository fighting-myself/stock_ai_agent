from langgraph.prebuilt import create_react_agent
from langgraph.graph import StateGraph, END
from core.state import AgentState
from langchain_core.messages import AIMessage, HumanMessage


class AgentFactory:
    @staticmethod
    def create_agent(agent_type: str, model, tools):
        agent_type = agent_type.strip().lower()

        # ========== 1. ReAct（原生稳定）==========
        if agent_type == "react":
            return create_react_agent(model, tools)

        # ========== 2. Plan & Execute（修复消息结构）==========
        elif agent_type == "plan_execute":

            async def plan_node(state: AgentState):
                from core.prompts import PLANNER_PROMPT

                res = await model.ainvoke(
                    [
                        ("system", PLANNER_PROMPT.strip()),
                        state["messages"][-1],
                    ]
                )
                return {"messages": [AIMessage(content=res.content)]}

            async def execute_node(state: AgentState):
                return await create_react_agent(model, tools).ainvoke(state)

            workflow = StateGraph(AgentState)
            workflow.add_node("plan", plan_node)
            workflow.add_node("execute", execute_node)
            workflow.set_entry_point("plan")
            workflow.add_edge("plan", "execute")
            workflow.add_edge("execute", END)
            return workflow.compile()

        # ========== 3. Reflection 【彻底修复：保留user消息】==========
        elif agent_type == "reflection":
            from core.prompts import REFLECTION_PROMPT

            async def run_agent(state: AgentState):
                # 执行工具，保留所有消息
                return await create_react_agent(model, tools).ainvoke(state)

            async def reflect_node(state: AgentState):
                # 🔥 🔥 🔥 修复：必须把【用户原始消息】放在最前面！
                messages = [
                    state["messages"][0],  # user 消息（必须保留）
                    state["messages"][1],  # assistant 消息
                    ("system", REFLECTION_PROMPT.strip()),
                ]
                res = await model.ainvoke(messages)
                return {"messages": [AIMessage(content=res.content)]}

            workflow = StateGraph(AgentState)
            workflow.add_node("run", run_agent)
            workflow.add_node("reflect", reflect_node)
            workflow.set_entry_point("run")
            workflow.add_edge("run", "reflect")
            workflow.add_edge("reflect", END)
            return workflow.compile()

        # ========== 4. ReWoo（修复消息结构）==========
        elif agent_type == "rewoo":

            async def planner(state: AgentState):
                tool_names = [t.name for t in tools]
                prompt = f"可用工具：{tool_names}，请执行用户查询"
                return {"messages": [AIMessage(content=prompt)]}

            async def executor(state: AgentState):
                return await create_react_agent(model, tools).ainvoke(state)

            workflow = StateGraph(AgentState)
            workflow.add_node("planner", planner)
            workflow.add_node("executor", executor)
            workflow.set_entry_point("planner")
            workflow.add_edge("planner", "executor")
            workflow.add_edge("executor", END)
            return workflow.compile()

        # ========== 默认 ==========
        return create_react_agent(model, tools)
