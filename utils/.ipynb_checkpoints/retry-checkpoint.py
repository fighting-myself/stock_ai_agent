from tenacity import retry, stop_after_attempt, wait_exponential, retry_if_exception_type
from utils.logger import logger
from config.settings import settings

def stock_retry(func):
    @retry(
        stop=stop_after_attempt(settings.STOCK_RETRY_MAX),
        wait=wait_exponential(multiplier=1, min=1, max=5),
        retry=retry_if_exception_type(Exception),
        before_sleep=lambda s: logger.warning(f"重试第 {s.attempt_number} 次")
    )
    def wrapper(*args, **kwargs):
        return func(*args, **kwargs)
    return wrapper