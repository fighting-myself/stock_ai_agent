"""非结构化市场信息：公司公告等（公开 HTTP 接口）。"""
import json
import httpx
from typing import List, Dict, Any, Optional, Tuple

from config.settings import settings
from utils.logger import logger


class MarketIntelClient:
    """上市公司公告列表（公开披露提要接口）。"""

    _ANN_LIST_URL = "https://np-anotice-stock.eastmoney.com/api/v1/ann/sk_ann_list"

    def fetch_recent_notices_ex(self, code: str, page_size: int = 10) -> Tuple[List[Dict[str, Any]], Optional[str]]:
        """
        拉取近期公告标题。
        返回 (rows, error_reason)。error_reason 为 None 表示请求与解析成功（列表可为空）。
        网络异常、非 JSON、空响应等不会抛异常，避免拖垮上层接口。
        """
        code = code.strip()
        params = {
            "stock_list": code,
            "page_size": min(page_size, 50),
            "page_index": 1,
            "ann_type": "A",
            "client_source": "web",
        }
        try:
            with httpx.Client(timeout=settings.EASTMONEY_API_TIMEOUT) as client:
                resp = client.get(self._ANN_LIST_URL, params=params)
                resp.raise_for_status()
                raw = resp.text or ""
                if not raw.strip():
                    logger.warning(f"{code} 公告接口返回空 body，status={resp.status_code}")
                    return [], "empty_response"
                try:
                    payload = resp.json()
                except json.JSONDecodeError as exc:
                    logger.warning(
                        f"{code} 公告接口非 JSON: {exc}; content-type={resp.headers.get('content-type')}; "
                        f"body_prefix={raw[:200]!r}"
                    )
                    return [], "invalid_json"
        except httpx.HTTPError as exc:
            logger.warning(f"{code} 公告接口 HTTP 错误: {exc}")
            return [], "http_error"
        except Exception as exc:
            logger.warning(f"{code} 公告接口未预期错误: {exc}")
            return [], "unknown_error"

        data = payload.get("data") if isinstance(payload, dict) else None
        if data is None and isinstance(payload, dict):
            # 部分错误形态为整包非标准
            if payload.get("message") or payload.get("error"):
                logger.info(f"{code} 公告接口业务提示: {payload}")
        data = (data or {}) if isinstance(data, dict) else {}
        rows = data.get("list") or []
        out = []
        for row in rows[:page_size]:
            if not isinstance(row, dict):
                continue
            out.append(
                {
                    "title": row.get("title") or row.get("notice_title") or "",
                    "date": row.get("notice_date") or row.get("display_time") or "",
                    "art_code": row.get("art_code") or "",
                }
            )
        logger.info(f"{code} 拉取公告 {len(out)} 条")
        return out, None

    def fetch_recent_notices(self, code: str, page_size: int = 10) -> List[Dict[str, Any]]:
        rows, _ = self.fetch_recent_notices_ex(code, page_size=page_size)
        return rows
