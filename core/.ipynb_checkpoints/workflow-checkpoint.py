from models.model_factory import ModelFactory
from core.agent_factory import AgentFactory
from tools.stock_tools import StockTools
from utils.logger import logger
from langchain_core.messages import SystemMessage, HumanMessage  # 修复这里！
from core.prompts import STOCK_AGENT_PROMPT

class StockAgentWorkflow:
    def __init__(self, agent_type: str, model_name: str):
        self.agent_type = agent_type
        self.model_name = model_name
        self.model = ModelFactory.get_model(model_name)
        self.tools = StockTools.get_all_tools()
        self.graph = AgentFactory.create_agent(
            agent_type=agent_type, model=self.model, tools=self.tools
        )

    async def run(self, query: str):
        logger.info(f"执行查询: {query} | 模型: {self.model_name} | 范式: {self.agent_type}")
        
        result = await self.graph.ainvoke({
            "messages": [
                SystemMessage(content=STOCK_AGENT_PROMPT),
                HumanMessage(content=query)
            ]
        })
        
        return result["messages"][-1].content