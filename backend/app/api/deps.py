"""FastAPI 依赖注入:当前用户、管理员权限。

供需要鉴权的路由使用,例如:
    @router.get("/me")
    async def me(user = Depends(get_current_user)): ...

- get_current_user: 解析 Authorization 头里的 Bearer token,返回用户 dict,无效抛 401;
- require_admin: 在 get_current_user 基础上校验 role == 'admin',否则抛 403。
"""

from typing import Dict, Any, Optional

from fastapi import Depends, Header, HTTPException, status

from ..services.security import decode_access_token
from ..services.auth_service import get_user_by_id


def get_current_user(
    authorization: str = Header(default=""),
) -> Dict[str, Any]:
    """
    从 Authorization: Bearer <token> 解析当前登录用户。

    Raises:
        HTTPException 401: 未提供 token / token 无效或过期 / 用户不存在
    """
    if not authorization or not authorization.startswith("Bearer "):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="未登录,请先登录",
        )

    token = authorization[len("Bearer "):].strip()
    payload = decode_access_token(token)
    if payload is None:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="登录已过期或无效,请重新登录",
        )

    try:
        user_id = int(payload.get("sub"))
    except (TypeError, ValueError):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="登录凭证无效",
        )

    user = get_user_by_id(user_id)
    if user is None:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="用户不存在",
        )
    return user


def get_optional_user(
    authorization: str = Header(default=""),
) -> Optional[Dict[str, Any]]:
    """
    可选认证:解析 Authorization 头里的 Bearer token。
    有效返回用户 dict;未提供 / 无效 / 过期则返回 None(不抛 401)。

    用于"游客可用、登录则绑定账号"的接口(如个性化问答)。
    """
    if not authorization or not authorization.startswith("Bearer "):
        return None

    token = authorization[len("Bearer "):].strip()
    payload = decode_access_token(token)
    if payload is None:
        return None

    try:
        user_id = int(payload.get("sub"))
    except (TypeError, ValueError):
        return None

    return get_user_by_id(user_id)


def require_admin(user: Dict[str, Any] = Depends(get_current_user)) -> Dict[str, Any]:
    """
    校验当前用户是否为管理员。

    Raises:
        HTTPException 403: 非管理员
    """
    if user.get("role") != "admin":
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="无管理员权限",
        )
    return user
