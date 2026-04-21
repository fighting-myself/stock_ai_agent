from fastapi import FastAPI
from uvicorn import run

from config.settings import settings
from core.workflow import StockAgentWorkflow
from utils.logger import logger
from utils.response import ApiResponse, error_response, success_response

app = FastAPI(
    title="股票AI智能助手",
    description="LangGraph + 4种Agent范式 + 多模型对比",
    version="1.0.0",
)


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
    return {"status": "ok", "model": settings.DEFAULT_MODEL}


if __name__ == "__main__":
    logger.info("股票AI助手后端服务启动")
    run(app, host=settings.BACKEND_HOST, port=settings.BACKEND_PORT)
