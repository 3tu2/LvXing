"""认证服务:注册、登录、用户查询。

封装 users 表的读写,配合 security.py(密码哈希 / JWT)与路由层使用。
用户对象统一为不含密码哈希的 dict:{id, username, nickname, role, created_at}。
"""

import sqlite3
from typing import Optional, Dict, Any

from ..db import get_connection
from .security import hash_password, verify_password


def _row_to_user(row: sqlite3.Row) -> Dict[str, Any]:
    """把 users 表的一行转成对外用户 dict(不含 password_hash)。"""
    return {
        "id": row["id"],
        "username": row["username"],
        "nickname": row["nickname"] or row["username"],
        "role": row["role"],
        "status": row["status"] if "status" in row.keys() else "active",
        "created_at": row["created_at"],
    }


def register(username: str, password: str, nickname: str = "") -> Dict[str, Any]:
    """
    注册新用户。

    Args:
        username: 用户名(登录名,唯一)
        password: 明文密码(内部哈希后存储)
        nickname: 昵称(可空,默认等于用户名)

    Returns:
        新用户 dict

    Raises:
        ValueError: 用户名已存在、用户名/密码不合法
    """
    username = (username or "").strip()
    if not username:
        raise ValueError("用户名不能为空")
    if len(username) < 3:
        raise ValueError("用户名至少 3 个字符")
    if not password or len(password) < 6:
        raise ValueError("密码至少 6 位")

    hashed = hash_password(password)
    nickname = (nickname or "").strip() or username

    try:
        with get_connection() as conn:
            cur = conn.execute(
                "INSERT INTO users (username, password_hash, nickname, role) VALUES (?, ?, ?, 'user')",
                (username, hashed, nickname),
            )
            user_id = cur.lastrowid
        return get_user_by_id(user_id)
    except sqlite3.IntegrityError:
        raise ValueError("该用户名已被注册")


def authenticate(username: str, password: str) -> Optional[Dict[str, Any]]:
    """
    校验用户名密码,成功返回用户 dict,失败返回 None。
    """
    username = (username or "").strip()
    with get_connection() as conn:
        row = conn.execute(
            "SELECT * FROM users WHERE username = ?",
            (username,),
        ).fetchone()

    if row is None:
        return None
    if not verify_password(password, row["password_hash"]):
        return None
    # 禁用用户不可登录
    status = row["status"] if "status" in row.keys() else "active"
    if status != "active":
        return None
    return _row_to_user(row)


def get_user_by_id(user_id: int) -> Optional[Dict[str, Any]]:
    """按 ID 查用户。"""
    with get_connection() as conn:
        row = conn.execute(
            "SELECT * FROM users WHERE id = ?",
            (user_id,),
        ).fetchone()
    return _row_to_user(row) if row else None


def get_user_by_username(username: str) -> Optional[Dict[str, Any]]:
    """按用户名查用户。"""
    with get_connection() as conn:
        row = conn.execute(
            "SELECT * FROM users WHERE username = ?",
            (username,),
        ).fetchone()
    return _row_to_user(row) if row else None
