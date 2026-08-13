"""POI相关API路由。

POI = Point of Interest,意思是"兴趣点",可以简单理解为地图上的一个地点
(景点、餐厅、酒店、商场等都算 POI)。

这个文件定义与 POI 相关的接口:
- GET /api/poi/detail/{poi_id}  根据 POI ID 获取详情(含图片)
- GET /api/poi/search           根据关键词搜索 POI
- GET /api/poi/photo            根据景点名称获取图片 URL

注意:这些接口和 map.py 里的 /map/poi 功能有重叠,是项目演进过程中留下的两套入口。
"""

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel, Field  # 用来在本文件内直接定义一个响应模型
from typing import List, Optional
from ...services.amap_service import get_amap_service

router = APIRouter(prefix="/poi", tags=["POI"])


class POIDetailResponse(BaseModel):
    """POI详情响应结构(和 models/schemas.py 里的模型类似,只是这里就近定义了)。"""
    success: bool
    message: str
    data: Optional[dict] = None  # 详情数据先用灵活的 dict 接收,内容由高德接口决定


@router.get(
    "/detail/{poi_id}",           # {poi_id} 是"路径参数",会从网址里取出来
    response_model=POIDetailResponse,
    summary="获取POI详情",
    description="根据POI ID获取详细信息,包括图片"
)
async def get_poi_detail(poi_id: str):
    """
    获取POI详情

    Args:
        poi_id: POI ID(从网址路径中传入,例如 /poi/detail/B000A8UIN8)

    Returns:
        POI详情响应
    """
    try:
        amap_service = get_amap_service()

        # 调用高德地图POI详情API
        result = amap_service.get_poi_detail(poi_id)

        return POIDetailResponse(
            success=True,
            message="获取POI详情成功",
            data=result
        )

    except Exception as e:
        print(f"❌ 获取POI详情失败: {str(e)}")
        raise HTTPException(
            status_code=500,
            detail=f"获取POI详情失败: {str(e)}"
        )


@router.get(
    "/search",
    summary="搜索POI",
    description="根据关键词搜索POI"
)
async def search_poi(keywords: str, city: str = "北京"):
    """
    搜索POI

    Args:
        keywords: 搜索关键词(查询参数,比如 ?keywords=故宫)
        city: 城市名称(默认北京)

    Returns:
        搜索结果
    """
    try:
        amap_service = get_amap_service()
        result = amap_service.search_poi(keywords, city)

        # 这里直接返回 dict(没有用 response_model),FastAPI 会自动转成 JSON
        return {
            "success": True,
            "message": "搜索成功",
            "data": result
        }

    except Exception as e:
        print(f"❌ 搜索POI失败: {str(e)}")
        raise HTTPException(
            status_code=500,
            detail=f"搜索POI失败: {str(e)}"
        )


@router.get(
    "/photo",
    summary="获取景点图片",
    description="根据景点名称从高德地图获取图片"
)
async def get_attraction_photo(name: str, city: str = ""):
    """
    获取景点图片

    Args:
        name: 景点名称
        city: 城市名称(可选,用于限定搜索范围)

    Returns:
        图片URL
    """
    try:
        amap_service = get_amap_service()

        # 搜索景点图片(返回图片 URL,找不到则为 None)
        photo_url = amap_service.search_poi_photo(name, city)

        return {
            "success": True,
            "message": "获取图片成功" if photo_url else "未找到图片",
            "data": {
                "name": name,
                "photo_url": photo_url
            }
        }

    except Exception as e:
        print(f"❌ 获取景点图片失败: {str(e)}")
        raise HTTPException(
            status_code=500,
            detail=f"获取景点图片失败: {str(e)}"
        )
