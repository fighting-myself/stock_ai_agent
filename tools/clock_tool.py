"""运行时墙钟快照：供 Agent 工具调用，避免用训练数据臆测「今天」。"""
from __future__ import annotations

from datetime import datetime, timezone
from zoneinfo import ZoneInfo, ZoneInfoNotFoundError


def build_clock_answer(iana_timezone: str = "") -> str:
    """在**调用瞬间**读取进程运行环境的时钟；可选换算到 IANA 时区。"""
    now_utc = datetime.now(timezone.utc)
    lines = [
        f"UTC：{now_utc.isoformat()}",
        f"Unix 秒：{int(now_utc.timestamp())}",
    ]
    local = datetime.now().astimezone()
    lines.append(f"进程系统本地：{local.isoformat()}（tzname={local.tzname()}）")
    tz = (iana_timezone or "").strip()
    if tz:
        try:
            z = ZoneInfo(tz)
            there = now_utc.astimezone(z)
            wk = ["一", "二", "三", "四", "五", "六", "日"][there.weekday()]
            lines.append(f"换算 {tz}：{there.strftime('%Y-%m-%d %H:%M:%S')}（星期{wk}）")
        except ZoneInfoNotFoundError:
            lines.append(f"无法识别 IANA 时区「{tz}」；请使用如 Asia/Shanghai、Europe/London 等标准名称。")
    lines.append("以上为本次工具调用时刻的快照；解释「今天」「此刻」等须以此为准。")
    return "\n".join(lines)
