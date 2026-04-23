"""非结构化市场信息：公司公告等（公开接口，无需额外 key）。"""
import httpx
from typing import List, Dict, Any

from config.settings import settings
from utils.logger import logger


class MarketIntelClient:
    """东方财富公告列表（与项目内 Eastmoney 数据源风格一致）。"""

    _ANN_LIST_URL = "https://np-anotice-stock.eastmoney.com/api/v1/ann/sk_ann_list"

    def fetch_recent_notices(self, code: str, page_size: int = 10) -> List[Dict[str, Any]]:
        code = code.strip()
        params = {
            "stock_list": code,
            "page_size": min(page_size, 50),
            "page_index": 1,
            "ann_type": "A",
            "client_source": "web",
        }
        with httpx.Client(timeout=settings.EASTMONEY_API_TIMEOUT) as client:
            resp = client.get(self._ANN_LIST_URL, params=params)
            resp.raise_for_status()
            payload = resp.json()
        data = payload.get("data") or {}
        rows = data.get("list") or []
        out = []
        for row in rows[:page_size]:
            out.append(
                {
                    "title": row.get("title") or row.get("notice_title") or "",
                    "date": row.get("notice_date") or row.get("display_time") or "",
                    "art_code": row.get("art_code") or "",
                }
            )
        logger.info(f"{code} 拉取公告 {len(out)} 条")
        return out
