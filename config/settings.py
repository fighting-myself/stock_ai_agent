"""应用配置：字段名与 .env 变量名一致（见仓库根目录 .env 示例块）。"""
from dotenv import load_dotenv
from pydantic import Field, model_validator
from pydantic_settings import BaseSettings, SettingsConfigDict

load_dotenv()


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore",
    )

    # ---------------- 模型 API KEY ----------------
    DASHSCOPE_API_KEY: str = ""
    DOUBAO_API_KEY: str = ""
    DEEPSEEK_API_KEY: str = ""
    MINIMAX_API_KEY: str = ""
    OPENAI_API_KEY: str = ""

    # ---------------- vLLM（OpenAI 兼容网关）----------------
    VLLM_BASE_URL: str = ""
    VLLM_MODEL: str = ""
    VLLM_API_KEY: str = "EMPTY"

    # ---------------- Tushare ----------------
    TUSHARE_TOKEN: str = ""

    # ---------------- 默认行为 ----------------
    DEFAULT_MODEL: str = "qwen3-vl-plus"
    DEFAULT_AGENT_TYPE: str = "react"

    # ---------------- 股票数据与超时 ----------------
    EASTMONEY_API_TIMEOUT: int = Field(default=10, ge=1, le=120)
    STOCK_RETRY_MAX: int = Field(default=3, ge=1, le=20)

    # ---------------- 同花顺 iFinD QuantAPI HTTP ----------------
    THS_IFIND_REFRESH_TOKEN: str = ""
    THS_IFIND_BASE_URL: str = "https://quantapi.51ifind.com"
    THS_IFIND_TIMEOUT: int = Field(default=45, ge=5, le=300)
    THS_IFIND_WENCAI_SEARCH_TYPE: str = "stock"
    THS_IFIND_REPORT_TYPE: str = "901"

    # ---------------- 服务 ----------------
    BACKEND_HOST: str = "0.0.0.0"
    BACKEND_PORT: int = Field(default=8001, ge=1, le=65535)
    LOG_LEVEL: str = "INFO"

    @model_validator(mode="after")
    def normalize_urls(self):
        if not (self.THS_IFIND_BASE_URL or "").strip():
            self.THS_IFIND_BASE_URL = "https://quantapi.51ifind.com"
        else:
            self.THS_IFIND_BASE_URL = self.THS_IFIND_BASE_URL.strip().rstrip("/")
        vb = (self.VLLM_BASE_URL or "").strip()
        if vb:
            self.VLLM_BASE_URL = vb.rstrip("/")
        return self

    @property
    def vllm_ready(self) -> bool:
        return bool(self.VLLM_BASE_URL.strip() and self.VLLM_MODEL.strip())

    @property
    def ths_ifind_ready(self) -> bool:
        return bool(self.THS_IFIND_REFRESH_TOKEN.strip())


settings = Settings()
