"""记忆管理 API 路由。

提供记忆系统的管理/调试接口:
- POST   /api/memory            手动写入一条记忆(测试/调试用)
- GET    /api/memory            查看某用户的记忆列表(?user_id=&type=)
- GET    /api/memory/preferences 查看某用户的偏好画像
- POST   /api/memory/extract    手动触发偏好提取(输入对话文本)
- DELETE /api/memory            清空整个记忆向量库(?confirm=yes)

注意:这些接口主要用于开发调试与验证,正式使用时前端主要只用 /api/chat。
"""

from fastapi import APIRouter, HTTPException
from typing import List

from ...models.schemas import (
    MemoryWriteRequest,
    MemoryItem,
    MemoryListResponse,
    PreferenceExtractRequest,
    PreferenceExtractResponse,
    ErrorResponse,
)
from ...services import memory_service, vector_store
from ...agents.feedback_agent import get_feedback_analyzer

router = APIRouter(prefix="/memory", tags=["记忆管理"])


@router.post(
    "",
    response_model=MemoryListResponse,
    summary="写入一条记忆",
    description="手动向某用户写入一条记忆(测试用)",
)
async def write_memory(request: MemoryWriteRequest):
    """写入一条记忆。"""
    try:
        vector_store.add_memory(
            text=request.text,
            user_id=request.user_id,
            memory_type=request.memory_type,
            metadata=request.metadata or {},
        )
        return MemoryListResponse(success=True, message="记忆写入成功")
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"写入记忆失败: {str(e)}")


@router.get(
    "",
    response_model=MemoryListResponse,
    summary="查看用户记忆",
    description="列出某用户的历史记忆(可按类型过滤)",
)
async def list_memories(user_id: str, type: str = "", limit: int = 50):
    """列出某用户的记忆。"""
    try:
        docs = vector_store.get_all_memories(
            user_id=user_id,
            memory_type=type or None,
            limit=min(limit, 200),
        )
        items = [MemoryItem(text=d.page_content, metadata=d.metadata) for d in docs]
        return MemoryListResponse(success=True, data=items)
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"查询记忆失败: {str(e)}")


@router.get(
    "/preferences",
    response_model=PreferenceExtractResponse,
    summary="查看用户偏好画像",
    description="读取某用户最新的偏好画像快照",
)
async def get_preferences(user_id: str):
    """读取用户偏好画像。"""
    try:
        profile = memory_service.get_user_profile(user_id)
        return PreferenceExtractResponse(
            success=True,
            message="查询成功" if profile else "该用户暂无偏好画像",
            preferences=profile,
            saved=False,
        )
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"查询偏好失败: {str(e)}")


@router.post(
    "/extract",
    response_model=PreferenceExtractResponse,
    summary="手动触发偏好提取",
    description="输入对话/反馈文本,提取偏好并写入该用户记忆",
)
async def extract_preferences(request: PreferenceExtractRequest):
    """手动触发偏好提取(与 /api/chat 后台任务同一条链路)。"""
    try:
        analyzer = get_feedback_analyzer()
        prefs = await analyzer.analyze([request.conversation_text])

        saved = False
        if any(v for v in prefs.values()):
            memory_service.save_preferences(request.user_id, prefs)
            saved = True

        return PreferenceExtractResponse(
            success=True,
            message="偏好提取完成" + ("并已保存" if saved else "(未提取到明确偏好)"),
            preferences=prefs,
            saved=saved,
        )
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"偏好提取失败: {str(e)}")


@router.delete(
    "",
    response_model=MemoryListResponse,
    summary="清空记忆向量库",
    description="清空整个向量库(需 ?confirm=yes,危险操作)",
)
async def clear_memory(confirm: str = ""):
    """清空向量库(开发调试用,生产环境不建议开放)。"""
    if confirm != "yes":
        raise HTTPException(status_code=400, detail="请携带 ?confirm=yes 确认清空")
    try:
        vector_store.clear()
        return MemoryListResponse(success=True, message="记忆向量库已清空")
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"清空失败: {str(e)}")
