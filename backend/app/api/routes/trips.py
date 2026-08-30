"""历史行程 API 路由。

接口(均需登录):
- GET    /api/trips        当前用户的历史行程列表
- GET    /api/trips/{id}   行程详情(完整计划)
- DELETE /api/trips/{id}   删除行程

行程在生成时自动保存(登录用户,见 planning_service.generate_plan);
本路由只负责查询与删除。
"""

from fastapi import APIRouter, Depends, HTTPException

from ...models.schemas import TripListItem, TripListResponse, TripDetailResponse, TripSaveRequest
from ...services import trip_service
from ..deps import get_current_user

router = APIRouter(prefix="/trips", tags=["历史行程"])


@router.get(
    "",
    response_model=TripListResponse,
    summary="历史行程列表",
    description="返回当前登录用户的历史行程摘要列表(新的在前)",
)
async def list_trips(user=Depends(get_current_user)):
    """历史行程列表。"""
    items = trip_service.list_trips(user["id"])
    return TripListResponse(
        success=True,
        message=f"共 {len(items)} 条行程",
        data=[TripListItem(**it) for it in items],
    )


@router.get(
    "/{trip_id}",
    response_model=TripDetailResponse,
    summary="行程详情",
    description="返回某条行程的完整计划(校验归属)",
)
async def get_trip_detail(trip_id: int, user=Depends(get_current_user)):
    """行程详情。"""
    plan = trip_service.get_trip(trip_id, user["id"])
    if plan is None:
        raise HTTPException(status_code=404, detail="行程不存在或无权访问")
    return TripDetailResponse(success=True, message="成功", data=plan)


@router.delete(
    "/{trip_id}",
    response_model=TripListResponse,
    summary="删除行程",
    description="删除某条历史行程(校验归属)",
)
async def delete_trip(trip_id: int, user=Depends(get_current_user)):
    """删除行程。"""
    ok = trip_service.delete_trip(trip_id, user["id"])
    if not ok:
        raise HTTPException(status_code=404, detail="行程不存在或无权删除")
    return TripListResponse(success=True, message="行程已删除")


@router.post(
    "",
    response_model=TripDetailResponse,
    summary="保存行程",
    description="手动保存一份行程(供前端生成后调用,登录用户)",
)
async def save_trip(request: TripSaveRequest, user=Depends(get_current_user)):
    """手动保存行程。"""
    trip_id = trip_service.create_trip(user["id"], request.city, request.plan)
    return TripDetailResponse(success=True, message=f"行程已保存(ID: {trip_id})", data=request.plan)
