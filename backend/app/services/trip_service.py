"""历史行程服务:保存、列表、详情、删除。

行程计划(TripPlan JSON)按登录用户持久化到 SQLite trips 表,
支撑"我的行程"回看功能。
"""

import json
from typing import Any, Dict, List, Optional

from ..db import get_connection


def create_trip(user_id: int, city: str, plan: Dict[str, Any]) -> int:
    """保存一份行程,返回行程 ID。"""
    with get_connection() as conn:
        cur = conn.execute(
            "INSERT INTO trips (user_id, city, plan_json) VALUES (?, ?, ?)",
            (user_id, city, json.dumps(plan, ensure_ascii=False)),
        )
        return cur.lastrowid


def _row_to_item(row) -> Dict[str, Any]:
    """把 trips 行转成列表摘要项。"""
    plan = json.loads(row["plan_json"]) if row["plan_json"] else {}
    return {
        "id": row["id"],
        "city": row["city"],
        "start_date": plan.get("start_date", ""),
        "end_date": plan.get("end_date", ""),
        "travel_days": len(plan.get("days") or []),
        "created_at": row["created_at"],
    }


def list_trips(user_id: int) -> List[Dict[str, Any]]:
    """按用户列出历史行程(新的在前)。"""
    with get_connection() as conn:
        rows = conn.execute(
            "SELECT * FROM trips WHERE user_id = ? ORDER BY id DESC",
            (user_id,),
        ).fetchall()
    return [_row_to_item(r) for r in rows]


def get_trip(trip_id: int, user_id: int) -> Optional[Dict[str, Any]]:
    """获取单份行程(校验归属,非本人返回 None)。"""
    with get_connection() as conn:
        row = conn.execute(
            "SELECT * FROM trips WHERE id = ? AND user_id = ?",
            (trip_id, user_id),
        ).fetchone()
    if row is None:
        return None
    return json.loads(row["plan_json"]) if row["plan_json"] else {}


def delete_trip(trip_id: int, user_id: int) -> bool:
    """删除行程(校验归属),返回是否删除成功。"""
    with get_connection() as conn:
        cur = conn.execute(
            "DELETE FROM trips WHERE id = ? AND user_id = ?",
            (trip_id, user_id),
        )
        return cur.rowcount > 0
