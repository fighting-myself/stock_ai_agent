from loguru import logger
import sys
import os
from config.settings import settings

os.makedirs("logs", exist_ok=True)

logger.remove()

logger.add(
    sys.stdout,
    format="<green>{time:YYYY-MM-DD HH:mm:ss}</green> | <level>{level}</level> | <cyan>{name}</cyan> | {message}",
    level=settings.LOG_LEVEL
)

logger.add(
    "logs/stock_agent.log",
    rotation="1 day",
    retention="7 days",
    encoding="utf-8",
    level="INFO"
)

__all__ = ["logger"]