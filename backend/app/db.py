"""SQLite 数据库模块。

用 Python 标准库 sqlite3(零依赖)做持久化,存用户、行程、规划会话等数据。
(向量记忆仍在 ChromaDB,不在此处。)

设计要点:
- 单文件数据库(backend/data/app.db),路径由 config.db_path 配置;
- get_connection(): 每次操作获取一个新连接(自动创建 data 目录);
- init_db(): 建表(幂等,可重复调用,应用启动时执行一次)。
"""

import sqlite3
from pathlib import Path

from .config import get_settings


def _resolve_db_path() -> Path:
    """把配置里的相对路径转成绝对路径(相对 backend/ 目录)。"""
    settings = get_settings()
    backend_dir = Path(__file__).resolve().parent.parent  # backend/
    return backend_dir / settings.db_path


def get_connection() -> sqlite3.Connection:
    """获取一个 SQLite 连接(自动创建目录)。"""
    path = _resolve_db_path()
    path.parent.mkdir(parents=True, exist_ok=True)
    conn = sqlite3.connect(str(path))
    conn.row_factory = sqlite3.Row  # 让查询结果支持按列名取值(如 row["username"])
    conn.execute("PRAGMA foreign_keys = ON")
    return conn


def init_db() -> None:
    """建表(幂等)。

    users 表:账号体系。
    后续阶段(M3/M4)会追加 trips、planning_sessions、chat_sessions 等表。
    """
    with get_connection() as conn:
        conn.executescript(
            """
            CREATE TABLE IF NOT EXISTS users (
                id            INTEGER PRIMARY KEY AUTOINCREMENT,
                username      TEXT UNIQUE NOT NULL,
                password_hash TEXT NOT NULL,
                nickname      TEXT,
                role          TEXT NOT NULL DEFAULT 'user',
                status        TEXT NOT NULL DEFAULT 'active',
                created_at    TEXT NOT NULL DEFAULT (datetime('now', 'localtime'))
            );

            CREATE TABLE IF NOT EXISTS planning_sessions (
                id          TEXT PRIMARY KEY,
                user_id     INTEGER,
                state_json  TEXT NOT NULL,
                plan_json   TEXT,
                status      TEXT NOT NULL DEFAULT 'draft',
                created_at  TEXT NOT NULL DEFAULT (datetime('now', 'localtime')),
                updated_at  TEXT NOT NULL DEFAULT (datetime('now', 'localtime'))
            );

            CREATE TABLE IF NOT EXISTS trips (
                id          INTEGER PRIMARY KEY AUTOINCREMENT,
                user_id     INTEGER NOT NULL,
                city        TEXT NOT NULL DEFAULT '南昌',
                plan_json   TEXT NOT NULL,
                created_at  TEXT NOT NULL DEFAULT (datetime('now', 'localtime'))
            );
            """
        )

        # 迁移:旧库的 users 表可能没有 status 列,补上
        cols = [r[1] for r in conn.execute("PRAGMA table_info(users)").fetchall()]
        if "status" not in cols:
            conn.execute("ALTER TABLE users ADD COLUMN status TEXT NOT NULL DEFAULT 'active'")
    print("✅ SQLite 数据库初始化完成")


if __name__ == "__main__":
    init_db()
