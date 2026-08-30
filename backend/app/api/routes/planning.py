"""AI 行程规划引擎 API 路由(对话式增量规划)。

接口:
- POST /api/plan/session       创建规划会话(提交规划状态)
- GET  /api/plan/session       读取会话(状态 + 缺失字段 + 计划 + 冲突)
- POST /api/plan/fill          参数补全(一次性批量提交缺失字段)
- POST /api/plan/generate      生成行程(参数齐全后调用多智能体)
- POST /api/plan/replan        局部重规划(按修改指令调整现有计划)
- POST /api/plan/check         冲突检查
"""

from fastapi import APIRouter, HTTPException
from typing import Optional, Dict, Any

from ...models.schemas import (
    PlannerState,
    PlanSessionCreateRequest,
    PlanFillRequest,
    PlanReplanRequest,
    PlanningSessionResponse,
)
from ...services import planning_service

router = APIRouter(prefix="/plan", tags=["行程规划引擎"])


def _build_response(session_id: str) -> PlanningSessionResponse:
    """根据会话 ID 组装统一响应(状态 + 缺失字段 + 计划 + 冲突)。"""
    found = planning_service.get_session(session_id)
    if found is None:
        raise HTTPException(status_code=404, detail="规划会话不存在")
    state, plan, _, _ = found
    missing_required, missing_optional = planning_service.compute_missing(state)
    conflicts = planning_service.check_conflicts(state, plan)

    return PlanningSessionResponse(
        success=True,
        message="成功",
        session_id=session_id,
        state=state,
        missing_required=planning_service.missing_labels(missing_required),
        missing_optional=planning_service.missing_labels(missing_optional),
        current_plan=plan,
        conflicts=conflicts,
    )


@router.post(
    "/session",
    response_model=PlanningSessionResponse,
    summary="创建规划会话",
    description="提交规划状态(出发地/日期/人数/预算/交通/兴趣等),返回 session_id 与缺失字段",
)
async def create_session(request: PlanSessionCreateRequest):
    """创建规划会话。"""
    try:
        session_id = planning_service.create_session(request.user_id, request.state)
        return _build_response(session_id)
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"创建会话失败: {str(e)}")


@router.get(
    "/session",
    response_model=PlanningSessionResponse,
    summary="读取规划会话",
    description="读取会话的规划状态、缺失字段、当前计划与冲突",
)
async def get_session(session_id: str):
    """读取规划会话。"""
    try:
        return _build_response(session_id)
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"读取会话失败: {str(e)}")


@router.post(
    "/fill",
    response_model=PlanningSessionResponse,
    summary="参数补全",
    description="一次性批量提交缺失字段(只更新提供的字段),返回补全后的缺失情况",
)
async def fill(request: PlanFillRequest):
    """参数补全。"""
    try:
        planning_service.fill_state(request.session_id, request)
        return _build_response(request.session_id)
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"参数补全失败: {str(e)}")


@router.post(
    "/generate",
    response_model=PlanningSessionResponse,
    summary="生成行程",
    description="参数齐全后调用多智能体生成行程,保存并做冲突检查",
)
async def generate(session_id: str):
    """生成行程计划。"""
    try:
        plan, conflicts = await planning_service.generate_plan(session_id)
        return PlanningSessionResponse(
            success=True,
            message="行程生成成功" if plan else "生成失败",
            session_id=session_id,
            current_plan=plan,
            conflicts=conflicts,
        )
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"生成行程失败: {str(e)}")


@router.post(
    "/replan",
    response_model=PlanningSessionResponse,
    summary="局部重规划",
    description="按修改指令在现有计划上做局部调整(不重新生成全量计划)",
)
async def replan(request: PlanReplanRequest):
    """局部重规划。"""
    try:
        plan, conflicts = await planning_service.replan(request.session_id, request.instruction)
        return PlanningSessionResponse(
            success=True,
            message="局部重规划完成",
            session_id=request.session_id,
            current_plan=plan,
            conflicts=conflicts,
        )
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"局部重规划失败: {str(e)}")


@router.post(
    "/check",
    response_model=PlanningSessionResponse,
    summary="冲突检查",
    description="对当前计划执行确定性冲突检查(预算/重复/日期/同行人数)",
)
async def check(session_id: str):
    """冲突检查。"""
    try:
        return _build_response(session_id)
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"冲突检查失败: {str(e)}")
