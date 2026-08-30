"""认证 API 路由。

接口:
- POST /api/auth/register  注册(用户名 + 密码 + 可选昵称)
- POST /api/auth/login     登录 → 返回 JWT token + 用户信息(带限流)
- GET  /api/auth/me        获取当前登录用户信息(需 token)
"""

import time
from fastapi import APIRouter, Depends, HTTPException, Request

from ...models.schemas import (
    RegisterRequest,
    LoginRequest,
    UserResponse,
    AuthResponse,
    ErrorResponse,
)
from ...services import auth_service
from ...services.security import create_access_token
from ..deps import get_current_user

router = APIRouter(prefix="/auth", tags=["认证"])

# 登录限流(内存,单进程):{key: 最近尝试时间戳列表}
_login_attempts = {}
_LOGIN_MAX_ATTEMPTS = 5      # 窗口内最大失败次数
_LOGIN_WINDOW_SECONDS = 60   # 时间窗口(秒)


def _is_rate_limited(key: str) -> bool:
    """判断某 key(IP)是否在窗口内超过失败次数;未超则记录一次。"""
    now = time.time()
    attempts = [t for t in _login_attempts.get(key, []) if now - t < _LOGIN_WINDOW_SECONDS]
    if len(attempts) >= _LOGIN_MAX_ATTEMPTS:
        return True
    attempts.append(now)
    _login_attempts[key] = attempts
    return False


@router.post(
    "/register",
    response_model=AuthResponse,
    summary="注册",
    description="用户名唯一、密码至少 6 位;成功后自动登录并返回 token",
)
async def register(request: RegisterRequest):
    """注册新用户。"""
    try:
        user = auth_service.register(
            username=request.username,
            password=request.password,
            nickname=request.nickname or "",
        )
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))

    token = create_access_token(user["id"], user["username"], user["role"])
    return AuthResponse(
        success=True,
        message="注册成功",
        token=token,
        user=UserResponse(**user),
    )


@router.post(
    "/login",
    response_model=AuthResponse,
    summary="登录",
    description="校验用户名密码,成功返回 JWT token",
)
async def login(request: LoginRequest, http_request: Request):
    """登录(带失败限流)。"""
    # 按 IP 限流,防止暴力破解
    key = f"login:{http_request.client.host}"
    if _is_rate_limited(key):
        raise HTTPException(status_code=429, detail="尝试次数过多,请稍后再试")

    user = auth_service.authenticate(request.username, request.password)
    if user is None:
        raise HTTPException(status_code=401, detail="用户名或密码错误")

    # 登录成功,清除该 IP 的失败计数
    _login_attempts.pop(key, None)

    token = create_access_token(user["id"], user["username"], user["role"])
    return AuthResponse(
        success=True,
        message="登录成功",
        token=token,
        user=UserResponse(**user),
    )


@router.get(
    "/me",
    response_model=UserResponse,
    summary="当前用户信息",
    description="根据 token 返回当前登录用户",
)
async def me(user=Depends(get_current_user)):
    """返回当前登录用户。"""
    return UserResponse(**user)
