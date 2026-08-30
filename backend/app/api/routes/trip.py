"""旅行规划API路由。

这是本项目最核心的接口:
- POST /api/trip/plan   根据用户需求生成完整旅行计划(调用多智能体系统)
- GET  /api/trip/health 检查旅行规划服务是否正常

前端首页点击"开始规划我的旅行"后,就会把表单数据 POST 到这里,
后端再调用 trip_planner_agent 里的多智能体系统生成结果。
"""

from fastapi import APIRouter, HTTPException
from ...logging import logger
from ...models.schemas import (   # 从数据模型导入请求/响应结构
    TripRequest,
    TripPlanResponse,
    ErrorResponse
)
from ...agents.trip_planner_agent import get_trip_planner_agent  # 导入多智能体系统

router = APIRouter(prefix="/trip", tags=["旅行规划"])


@router.post(
    "/plan",
    response_model=TripPlanResponse,
    summary="生成旅行计划",
    description="根据用户输入的旅行需求,生成详细的旅行计划"
)
async def plan_trip(request: TripRequest):
    """
    生成旅行计划

    Args:
        request: 旅行请求参数(前端表单提交的 JSON 会自动解析成 TripRequest 对象)

    Returns:
        旅行计划响应
    """
    try:
        # 目的地固定为南昌(南昌聚焦:后端权威兜底,忽略前端传入的城市)
        request.city = "南昌"

        # 打印收到的请求,方便调试时看日志
        print(f"\n{'='*60}")
        print(f"📥 收到旅行规划请求:")
        print(f"   城市: {request.city}")
        print(f"   日期: {request.start_date} - {request.end_date}")
        print(f"   天数: {request.travel_days}")
        print(f"{'='*60}\n")

        # 获取多智能体系统实例(单例,只初始化一次)
        print("🔄 获取多智能体系统实例...")
        agent = get_trip_planner_agent()

        # 调用核心方法生成旅行计划(异步)
        print("🚀 开始生成旅行计划...")
        trip_plan = await agent.plan_trip(request)

        print("✅ 旅行计划生成成功,准备返回响应\n")

        return TripPlanResponse(
            success=True,
            message="旅行计划生成成功",
            data=trip_plan
        )

    except Exception as e:
        # 出错时打印完整堆栈,方便定位问题
        logger.error(f"生成旅行计划失败: {str(e)}")
        import traceback
        traceback.print_exc()
        raise HTTPException(
            status_code=500,
            detail=f"生成旅行计划失败: {str(e)}"
        )


@router.get(
    "/health",
    summary="健康检查",
    description="检查旅行规划服务是否正常"
)
async def health_check():
    """健康检查:确认多智能体系统能正常初始化。"""
    try:
        # 检查多智能体系统是否可用(初始化失败会抛异常)
        get_trip_planner_agent()

        return {
            "status": "healthy",
            "service": "trip-planner",
            "framework": "LangChain + LangGraph",
        }
    except Exception as e:
        raise HTTPException(
            status_code=503,
            detail=f"服务不可用: {str(e)}"
        )
