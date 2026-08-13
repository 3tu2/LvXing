"""地图服务API路由。

这个文件定义与"地图"相关的一组接口:
- GET /api/map/poi       搜索 POI(兴趣点,比如景点、餐厅)
- GET /api/map/weather   查询某城市天气
- POST /api/map/route    规划两点之间的路线
- GET /api/map/health    检查地图服务是否正常

每个接口都遵循同样的套路:接收参数 -> 调用 amap_service 服务 -> 包装成统一格式返回。
如果出错,统一返回 HTTP 500 错误(给前端一个明确的提示)。

小白可以这样理解:"路由"就是"接待前台",负责收下前端的请求、交给后台服务处理、
再把结果打包送回去。
"""

from fastapi import APIRouter, HTTPException, Query  # APIRouter 用来创建路由;HTTPException 用来抛错误;Query 用来描述查询参数
from typing import Optional
from ...models.schemas import (   # 从数据模型里导入请求/响应的"结构"
    POISearchRequest,
    POISearchResponse,
    RouteRequest,
    RouteResponse,
    WeatherResponse
)
from ...services.amap_service import get_amap_service, get_amap_tools  # 导入高德地图服务与 MCP 工具

# 创建路由对象,prefix="/map" 表示这个文件里的接口网址都带 /map 前缀
# tags 用于在 /docs 文档里分组显示
router = APIRouter(prefix="/map", tags=["地图服务"])


@router.get(
    "/poi",
    response_model=POISearchResponse,   # 告诉 FastAPI 返回结果要符合这个结构
    summary="搜索POI",
    description="根据关键词搜索POI(兴趣点)"
)
async def search_poi(
    keywords: str = Query(..., description="搜索关键词", example="故宫"),
    city: str = Query(..., description="城市", example="北京"),
    citylimit: bool = Query(True, description="是否限制在城市范围内")
):
    """
    搜索POI

    Args:
        keywords: 搜索关键词
        city: 城市
        citylimit: 是否限制在城市范围内

    Returns:
        POI搜索结果
    """
    try:
        # 获取服务实例(单例,重复调用拿到的是同一个对象)
        service = get_amap_service()

        # 调用服务里的搜索方法
        pois = service.search_poi(keywords, city, citylimit)

        # 把结果包装成统一的响应结构返回
        return POISearchResponse(
            success=True,
            message="POI搜索成功",
            data=pois
        )

    except Exception as e:
        # 任何异常都打印日志并返回 500 错误
        print(f"❌ POI搜索失败: {str(e)}")
        raise HTTPException(
            status_code=500,
            detail=f"POI搜索失败: {str(e)}"
        )


@router.get(
    "/weather",
    response_model=WeatherResponse,
    summary="查询天气",
    description="查询指定城市的天气信息"
)
async def get_weather(
    city: str = Query(..., description="城市名称", example="北京")
):
    """
    查询天气

    Args:
        city: 城市名称

    Returns:
        天气信息
    """
    try:
        # 获取服务实例
        service = get_amap_service()

        # 查询天气
        weather_info = service.get_weather(city)

        return WeatherResponse(
            success=True,
            message="天气查询成功",
            data=weather_info
        )

    except Exception as e:
        print(f"❌ 天气查询失败: {str(e)}")
        raise HTTPException(
            status_code=500,
            detail=f"天气查询失败: {str(e)}"
        )


@router.post(
    "/route",
    response_model=RouteResponse,
    summary="规划路线",
    description="规划两点之间的路线"
)
async def plan_route(request: RouteRequest):
    """
    规划路线

    Args:
        request: 路线规划请求(请求体,由 FastAPI 自动解析成 RouteRequest 对象)

    Returns:
        路线信息
    """
    try:
        # 获取服务实例
        service = get_amap_service()

        # 把请求里的各个字段传给服务层的规划方法
        route_info = service.plan_route(
            origin_address=request.origin_address,
            destination_address=request.destination_address,
            origin_city=request.origin_city,
            destination_city=request.destination_city,
            route_type=request.route_type
        )

        return RouteResponse(
            success=True,
            message="路线规划成功",
            data=route_info
        )

    except Exception as e:
        print(f"❌ 路线规划失败: {str(e)}")
        raise HTTPException(
            status_code=500,
            detail=f"路线规划失败: {str(e)}"
        )


@router.get(
    "/health",
    summary="健康检查",
    description="检查地图服务是否正常"
)
async def health_check():
    """健康检查:确认高德地图服务能正常初始化、有多少个可用工具。"""
    try:
        # 异步加载高德 MCP 工具(如果初始化失败会抛异常)
        tools = await get_amap_tools()

        return {
            "status": "healthy",
            "service": "map-service",
            "mcp_tools_count": len(tools)  # 可用工具数量
        }
    except Exception as e:
        # 服务不可用时返回 503(服务不可用)
        raise HTTPException(
            status_code=503,
            detail=f"服务不可用: {str(e)}"
        )
