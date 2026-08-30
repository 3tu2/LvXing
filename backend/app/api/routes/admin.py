"""后台管理 API 路由(仅管理员)。

接口(均需 admin 角色):
- GET    /api/admin/stats             仪表盘统计
- GET    /api/admin/users            用户列表
- PATCH  /api/admin/users/{id}/status 启用/禁用用户
- GET    /api/admin/kb               知识库条目列表
- POST   /api/admin/kb               新增知识条目
- PUT    /api/admin/kb/{id}          修改知识条目
- DELETE /api/admin/kb/{id}          删除知识条目
"""

from fastapi import APIRouter, Depends, HTTPException, Query, UploadFile, File
from typing import List

from ...models.schemas import (
    AdminStats,
    AdminUserItem,
    AdminUsersResponse,
    KBItem,
    KBListResponse,
    KBUpsertRequest,
)
from ...services import admin_service
from ..deps import require_admin

router = APIRouter(prefix="/admin", tags=["后台管理"])


@router.get(
    "/stats",
    response_model=AdminStats,
    summary="仪表盘统计",
    description="返回用户数、行程数、问答数、知识库切片数、近7日趋势",
)
async def stats(admin=Depends(require_admin)):
    """仪表盘统计。"""
    return AdminStats(**admin_service.get_stats())


@router.get(
    "/users",
    response_model=AdminUsersResponse,
    summary="用户列表",
    description="返回所有用户(含行程数、状态)",
)
async def list_users(admin=Depends(require_admin)):
    """用户列表。"""
    users = admin_service.list_users()
    return AdminUsersResponse(
        success=True,
        message=f"共 {len(users)} 个用户",
        data=[AdminUserItem(**u) for u in users],
    )


@router.patch(
    "/users/{user_id}/status",
    response_model=AdminUsersResponse,
    summary="启用/禁用用户",
    description="status: active(启用) / disabled(禁用)",
)
async def update_user_status(
    user_id: int,
    status: str = Query(..., description="active / disabled"),
    admin=Depends(require_admin),
):
    """启用/禁用用户。"""
    try:
        ok = admin_service.set_user_status(user_id, status)
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    if not ok:
        raise HTTPException(status_code=404, detail="用户不存在")
    return AdminUsersResponse(success=True, message=f"用户状态已更新为 {status}")


@router.get(
    "/kb",
    response_model=KBListResponse,
    summary="知识库条目",
    description="列出知识库切片(含类别/标题/来源)",
)
async def list_kb(
    limit: int = Query(100, ge=1, le=500),
    admin=Depends(require_admin),
):
    """知识库条目列表。"""
    items = admin_service.list_kb(limit=limit)
    return KBListResponse(
        success=True,
        message=f"共 {len(items)} 条(知识库未构建时为 0)",
        data=[KBItem(**it) for it in items],
    )


@router.post(
    "/kb",
    response_model=KBListResponse,
    summary="新增知识条目",
    description="新增一条知识(向量化写入并重建关键词索引)",
)
async def add_kb(request: KBUpsertRequest, admin=Depends(require_admin)):
    """新增知识条目。"""
    if not request.text.strip():
        raise HTTPException(status_code=400, detail="知识内容不能为空")
    try:
        kb_id = admin_service.add_kb(
            request.text.strip(),
            category=request.category,
            title=request.title,
            source=request.source,
            poi_name=request.poi_name,
        )
        return KBListResponse(success=True, message=f"知识已添加(ID: {kb_id})")
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"添加失败(知识库可能未构建): {str(e)}")


@router.put(
    "/kb/{kb_id}",
    response_model=KBListResponse,
    summary="修改知识条目",
    description="修改一条知识(删旧加新并重建关键词索引,未提供的字段保留原值)",
)
async def update_kb(kb_id: str, request: KBUpsertRequest, admin=Depends(require_admin)):
    """修改知识条目。"""
    if not request.text.strip():
        raise HTTPException(status_code=400, detail="知识内容不能为空")
    try:
        ok = admin_service.update_kb(
            kb_id,
            request.text.strip(),
            category=request.category,
            title=request.title,
            source=request.source,
            poi_name=request.poi_name,
        )
        if not ok:
            raise HTTPException(status_code=404, detail="知识条目不存在")
        return KBListResponse(success=True, message="知识已更新")
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"修改失败(知识库可能未构建): {str(e)}")


@router.post(
    "/kb/import",
    summary="批量导入知识",
    description="上传 .md/.txt(front-matter)或 .json(数组/单对象)文件,批量切片向量化入库",
)
async def import_kb(files: List[UploadFile] = File(...), admin=Depends(require_admin)):
    """批量导入知识文件。"""
    contents = []
    for f in files:
        try:
            content = (await f.read()).decode("utf-8")
        except UnicodeDecodeError:
            content = (await f.read()).decode("utf-8", errors="replace")
        contents.append({"filename": f.filename or "", "content": content})

    try:
        result = admin_service.import_kb_files(contents)
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"批量导入失败(知识库可能未构建): {str(e)}")

    return {
        "success": True,
        "message": f"导入 {result['imported']} 条切片,跳过 {result['skipped']} 个文件",
        "imported": result["imported"],
        "skipped": result["skipped"],
    }


@router.delete(
    "/kb/{kb_id}",
    response_model=KBListResponse,
    summary="删除知识条目",
    description="删除单条知识并重建关键词索引",
)
async def delete_kb(kb_id: str, admin=Depends(require_admin)):
    """删除知识条目。"""
    ok = admin_service.delete_kb(kb_id)
    if not ok:
        raise HTTPException(status_code=500, detail="删除失败(知识库可能未构建)")
    return KBListResponse(success=True, message="知识条目已删除")
