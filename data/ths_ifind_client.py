"""同花顺 iFinD QuantAPI HTTP（需 refresh_token；与官方示例路径一致）。"""
from __future__ import annotations

import json
from datetime import datetime, timedelta
from typing import Any, Dict, List, Optional

import httpx

from config.settings import settings
from utils.logger import logger


def to_ths_code(code: str) -> str:
    c = code.strip().upper()
    if "." in c:
        return c
    pure = c[:6] if len(c) >= 6 else c.zfill(6)
    return f"{pure}.SH" if pure.startswith("6") else f"{pure}.SZ"


class ThsIfindClient:
    """封装 get_access_token、report_query、smart_stock_picking；返回可拼进提示词的自然语言片段。"""

    def __init__(self) -> None:
        self._base = settings.THS_IFIND_BASE_URL.rstrip("/")
        self._timeout = settings.THS_IFIND_TIMEOUT
        self._access_token: Optional[str] = None

    def _configured(self) -> bool:
        return bool((settings.THS_IFIND_REFRESH_TOKEN or "").strip())

    def _fetch_access_token(self) -> str:
        if not self._configured():
            raise RuntimeError(
                "未配置 THS_IFIND_REFRESH_TOKEN，无法调用同花顺 iFinD HTTP。"
                "请在环境变量或 .env 中配置后重试。"
            )
        url = f"{self._base}/api/v1/get_access_token"
        headers = {
            "Content-Type": "application/json",
            "refresh_token": settings.THS_IFIND_REFRESH_TOKEN.strip(),
        }
        with httpx.Client(timeout=self._timeout) as client:
            resp = client.post(url, headers=headers)
            resp.raise_for_status()
            payload = resp.json()
        data = payload.get("data") if isinstance(payload.get("data"), dict) else {}
        token = (data or {}).get("access_token") or payload.get("access_token")
        if not token:
            logger.warning("iFinD token 响应异常: %s", str(payload)[:800])
            raise RuntimeError("同花顺 token 响应中未找到 access_token，请核对 refresh_token。")
        self._access_token = str(token)
        return self._access_token

    def _auth_headers(self) -> Dict[str, str]:
        if not self._access_token:
            self._fetch_access_token()
        return {
            "Content-Type": "application/json",
            "access_token": self._access_token or "",
        }

    def _post_json(self, path: str, body: Dict[str, Any], *, retry_auth: bool = True) -> Dict[str, Any]:
        url = f"{self._base}{path}"
        with httpx.Client(timeout=self._timeout) as client:
            resp = client.post(url, headers=self._auth_headers(), json=body)
            if resp.status_code == 401 and retry_auth:
                self._access_token = None
                self._fetch_access_token()
                return self._post_json(path, body, retry_auth=False)
            resp.raise_for_status()
            return resp.json()

    @staticmethod
    def _rows_from_payload(payload: Dict[str, Any]) -> List[Dict[str, Any]]:
        """尽量从专题报表类响应中抽出行列表（不同版本字段名可能略有差异）。"""
        if not isinstance(payload, dict):
            return []
        err = payload.get("errorcode")
        if err not in (0, None, "0", "00"):
            msg = payload.get("errmsg") or payload.get("message") or str(payload)[:500]
            raise RuntimeError(f"同花顺接口业务错误: errorcode={err} errmsg={msg}")
        tables = payload.get("tables")
        rows: List[Dict[str, Any]] = []
        if isinstance(tables, list):
            for block in tables:
                if not isinstance(block, dict):
                    continue
                inner = block.get("table") or block.get("data") or block.get("rows")
                if isinstance(inner, list):
                    for r in inner:
                        if isinstance(r, dict):
                            rows.append(r)
                elif isinstance(inner, dict):
                    rows.append(inner)
        data = payload.get("data")
        if isinstance(data, list):
            for r in data:
                if isinstance(r, dict):
                    rows.append(r)
        elif isinstance(data, dict):
            inner = data.get("table") or data.get("rows") or data.get("list")
            if isinstance(inner, list):
                for r in inner:
                    if isinstance(r, dict):
                        rows.append(r)
        return rows

    def report_query_titles(self, code: str, days: int = 14) -> str:
        """专题报表 report_query（官方示例 reportType=901），输出为自然语言列表。"""
        ths = to_ths_code(code)
        end = datetime.now().date()
        begin = end - timedelta(days=max(1, min(days, 365)))
        body = {
            "codes": ths,
            "functionpara": {"reportType": settings.THS_IFIND_REPORT_TYPE},
            "beginrDate": begin.isoformat(),
            "endrDate": end.isoformat(),
            "outputpara": "reportDate:Y,thscode:Y,secName:Y,ctime:Y,reportTitle:Y,pdfURL:Y,seq:Y",
        }
        payload = self._post_json("/api/v1/report_query", body)
        rows = self._rows_from_payload(payload)
        if not rows:
            snippet = json.dumps(payload, ensure_ascii=False)[:2000]
            return f"标的 {ths} 在 report_query 中未解析到表格行，原始片段：\n{snippet}"
        lines: List[str] = []
        for r in rows[:25]:
            title = r.get("reportTitle") or r.get("title") or ""
            d = r.get("reportDate") or r.get("report_date") or r.get("ctime") or ""
            name = r.get("secName") or r.get("sec_name") or ""
            lines.append(f"- {d} {name} {title}".strip())
        return f"同花顺 iFinD 专题报表（reportType={settings.THS_IFIND_REPORT_TYPE}）近期条目（{ths}，最多25条）：\n" + "\n".join(lines)

    def smart_stock_picking_text(self, searchstring: str) -> str:
        """问财式智能检索 smart_stock_picking；用于综合检索、舆情类自然语言提问。"""
        q = (searchstring or "").strip()
        if not q:
            return "检索语句为空，请提供具体问题或关键词（可含股票名称与代码）。"
        body = {
            "searchstring": q,
            "searchtype": settings.THS_IFIND_WENCAI_SEARCH_TYPE,
        }
        payload = self._post_json("/api/v1/smart_stock_picking", body)
        try:
            text = json.dumps(payload, ensure_ascii=False, indent=2)
        except Exception:
            text = str(payload)
        max_len = 6000
        if len(text) > max_len:
            text = text[:max_len] + "\n…（已截断，完整 JSON 过长）"
        return f"同花顺 iFinD 智能检索（searchtype={settings.THS_IFIND_WENCAI_SEARCH_TYPE}）原始结果：\n{text}"
