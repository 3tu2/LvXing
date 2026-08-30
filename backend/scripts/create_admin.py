"""创建管理员账号(种子脚本)。

用法(在 backend/ 目录下,先激活 .venv):
    python scripts/create_admin.py                          # 交互式输入
    python scripts/create_admin.py --username admin --password 123456 --nickname 管理员

说明:
- 若用户名已存在,会将其升级为管理员(role=admin);
- 密码用 PBKDF2 哈希存储,不会明文落库。
"""

import argparse
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from app.db import init_db, get_connection
from app.services.security import hash_password


def create_admin(username: str, password: str, nickname: str = "") -> None:
    """创建管理员,或把已有用户升级为管理员。"""
    if len(password) < 6:
        raise ValueError("密码至少 6 位")

    init_db()
    hashed = hash_password(password)
    nickname = (nickname or "").strip() or username

    with get_connection() as conn:
        existing = conn.execute(
            "SELECT id FROM users WHERE username = ?", (username,)
        ).fetchone()
        if existing:
            conn.execute(
                "UPDATE users SET role='admin', status='active', password_hash = ? WHERE username = ?",
                (hashed, username),
            )
            print(f"✅ 用户「{username}」已存在,已升级为管理员")
        else:
            conn.execute(
                "INSERT INTO users (username, password_hash, nickname, role, status) "
                "VALUES (?, ?, ?, 'admin', 'active')",
                (username, hashed, nickname),
            )
            print(f"✅ 管理员「{username}」创建成功")


def main():
    parser = argparse.ArgumentParser(description="创建管理员账号")
    parser.add_argument("--username", default=None)
    parser.add_argument("--password", default=None)
    parser.add_argument("--nickname", default="")
    args = parser.parse_args()

    username = args.username or input("请输入管理员用户名: ").strip()
    password = args.password or input("请输入密码(至少6位): ").strip()
    nickname = args.nickname or input("昵称(可空,回车跳过): ").strip()

    try:
        create_admin(username, password, nickname)
    except ValueError as e:
        print(f"❌ {e}")
        sys.exit(1)


if __name__ == "__main__":
    main()
