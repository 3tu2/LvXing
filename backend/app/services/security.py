"""安全模块:密码哈希与 JWT 令牌。

- 密码哈希:用标准库 hashlib.pbkdf2_hmac(PBKDF2-SHA256,加盐、可配置迭代次数),
  零额外依赖;存储格式 `pbkdf2_sha256$迭代次数$盐$哈希`(均 base64 编码)。
- JWT:用 PyJWT(HS256),payload 含用户 id、用户名、角色与过期时间。
"""

import base64
import hashlib
import hmac
import secrets
from datetime import datetime, timedelta, timezone
from typing import Dict, Any, Optional

import jwt  # PyJWT

from ..config import get_settings
from ..logging import logger


# ============ 密码哈希 ============

_PBKDF2_ITERATIONS = 260_000  # 迭代次数(越高越安全,也越慢)


def hash_password(password: str) -> str:
    """对密码做加盐哈希,返回可直接存库的字符串。"""
    salt = secrets.token_bytes(16)  # 16 字节随机盐
    digest = hashlib.pbkdf2_hmac(
        "sha256",
        password.encode("utf-8"),
        salt,
        _PBKDF2_ITERATIONS,
    )
    return "$".join([
        "pbkdf2_sha256",
        str(_PBKDF2_ITERATIONS),
        base64.b64encode(salt).decode("ascii"),
        base64.b64encode(digest).decode("ascii"),
    ])


def verify_password(password: str, hashed: str) -> bool:
    """校验密码是否匹配已存哈希(用 hmac.compare_digest 防时序攻击)。"""
    try:
        algo, iterations, salt_b64, digest_b64 = hashed.split("$")
        if algo != "pbkdf2_sha256":
            return False
        salt = base64.b64decode(salt_b64)
        expected = base64.b64decode(digest_b64)
        actual = hashlib.pbkdf2_hmac(
            "sha256",
            password.encode("utf-8"),
            salt,
            int(iterations),
        )
        return hmac.compare_digest(actual, expected)
    except Exception:
        return False


# ============ JWT 令牌 ============

def create_access_token(user_id: int, username: str, role: str) -> str:
    """生成 JWT 访问令牌。"""
    settings = get_settings()
    now = datetime.now(timezone.utc)
    payload = {
        "sub": str(user_id),          # 主题 = 用户 ID(字符串)
        "username": username,
        "role": role,
        "iat": now,
        "exp": now + timedelta(minutes=settings.jwt_expire_minutes),
    }
    return jwt.encode(payload, settings.jwt_secret, algorithm=settings.jwt_algorithm)


def decode_access_token(token: str) -> Optional[Dict[str, Any]]:
    """解析并校验 JWT,成功返回 payload,失败返回 None。"""
    settings = get_settings()
    try:
        return jwt.decode(
            token,
            settings.jwt_secret,
            algorithms=[settings.jwt_algorithm],
        )
    except jwt.ExpiredSignatureError:
        logger.warning("JWT 已过期")
        return None
    except jwt.InvalidTokenError as e:
        logger.warning(f"JWT 无效: {e}")
        return None
