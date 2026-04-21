from pydantic_settings import BaseSettings
from dotenv import load_dotenv
import os

load_dotenv()

class Settings(BaseSettings):
    # API KEY
    DASHSCOPE_API_KEY: str = os.getenv("DASHSCOPE_API_KEY", "")
    DOUBAO_API_KEY: str = os.getenv("DOUBAO_API_KEY", "")
    DEEPSEEK_API_KEY: str = os.getenv("DEEPSEEK_API_KEY", "")
    MINIMAX_API_KEY: str = os.getenv("MINIMAX_API_KEY", "")
    OPENAI_API_KEY: str = os.getenv("OPENAI_API_KEY", "")

    # Tushare
    TUSHARE_TOKEN: str = os.getenv("TUSHARE_TOKEN", "")

    # 默认配置
    DEFAULT_MODEL: str = os.getenv("DEFAULT_MODEL", "qwen3-vl-plus")
    DEFAULT_AGENT_TYPE: str = os.getenv("DEFAULT_AGENT_TYPE", "react")

    # 股票
    EASTMONEY_API_TIMEOUT: int = int(os.getenv("EASTMONEY_API_TIMEOUT", 10))
    STOCK_RETRY_MAX: int = int(os.getenv("STOCK_RETRY_MAX", 3))

    # 服务
    BACKEND_HOST: str = os.getenv("BACKEND_HOST", "0.0.0.0")
    BACKEND_PORT: int = int(os.getenv("BACKEND_PORT", 8000))
    LOG_LEVEL: str = os.getenv("LOG_LEVEL", "INFO")

settings = Settings()