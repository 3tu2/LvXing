"""AI 行程规划引擎服务(对话式增量规划)。

在现有多智能体生成(LangGraph)之上,封装状态化、可增量调整的规划能力:
1. 规划状态(PlannerState)持久化(planning_sessions 表);
2. 参数补全:识别缺失字段,一次性列出让用户批量补全;
3. 行程生成:复用 trip_planner_agent 的多智能体(景点/天气/酒店/规划专家);
4. 局部重规划:按修改指令在现有计划上做局部调整,避免全景重新生成;
5. 冲突检查:确定性规则(预算/重复/日期/同行人数/空计划)。

说明:距离与营业时间冲突依赖高德路线 + 知识库营业时间(M3 接入),
本模块已预留 check_conflicts 扩展点,先实现不依赖外部数据的规则。
"""

import json
import uuid
from datetime import datetime
from typing import Any, Dict, List, Optional, Tuple

from ..db import get_connection
from ..logging import logger
from ..models.schemas import (
    PlannerState,
    ConflictInfo,
    PlanFillRequest,
)
from ..agents.trip_planner_agent import get_trip_planner_agent
from ..services.llm_service import get_llm


# ============ 字段定义 ============

FIELD_LABELS: Dict[str, str] = {
    "departure_city": "出发地",
    "start_date": "出发日期",
    "end_date": "结束日期",
    "travel_days": "旅行天数",
    "party_adults": "成人人数",
    "party_children": "儿童人数",
    "budget": "预算(元)",
    "transportation": "交通方式",
    "accommodation": "住宿偏好",
    "interests": "兴趣标签",
    "notes": "额外要求",
}

# 必填:缺失会阻止生成;建议:缺失不阻塞但提示补全
REQUIRED_FIELDS = ["start_date", "end_date"]
OPTIONAL_FIELDS = ["departure_city", "transportation", "interests", "budget", "accommodation"]


def _is_empty(value: Any) -> bool:
    """判断字段值是否为空(空串/0/空列表/None 都算空)。"""
    if value is None:
        return True
    if isinstance(value, str):
        return not value.strip()
    if isinstance(value, (list, dict)):
        return len(value) == 0
    if isinstance(value, (int, float)):
        return value == 0
    return False


def compute_missing(state: PlannerState) -> Tuple[List[str], List[str]]:
    """计算缺失字段,返回 (必填缺失, 建议缺失)。"""
    data = state.model_dump()
    missing_required = [f for f in REQUIRED_FIELDS if _is_empty(data.get(f))]
    missing_optional = [f for f in OPTIONAL_FIELDS if _is_empty(data.get(f))]
    return missing_required, missing_optional


def missing_labels(fields: List[str]) -> List[str]:
    """把字段名转成中文标签。"""
    return [FIELD_LABELS.get(f, f) for f in fields]


# ============ 会话持久化 ============

def create_session(user_id: Optional[int], state: PlannerState) -> str:
    """创建规划会话,返回 session_id。"""
    session_id = uuid.uuid4().hex
    with get_connection() as conn:
        conn.execute(
            "INSERT INTO planning_sessions (id, user_id, state_json, status) VALUES (?, ?, ?, 'draft')",
            (session_id, user_id, state.model_dump_json()),
        )
    return session_id


def _row_to_state(row) -> Tuple[PlannerState, Optional[Dict], str, Optional[int]]:
    """把 planning_sessions 行转成 (state, plan, status, user_id)。"""
    state = PlannerState(**json.loads(row["state_json"]))
    plan = json.loads(row["plan_json"]) if row["plan_json"] else None
    return state, plan, row["status"], row["user_id"]


def get_session(session_id: str) -> Optional[Tuple[PlannerState, Optional[Dict], str, Optional[int]]]:
    """读取规划会话(不存在返回 None)。"""
    with get_connection() as conn:
        row = conn.execute(
            "SELECT * FROM planning_sessions WHERE id = ?",
            (session_id,),
        ).fetchone()
    return _row_to_state(row) if row else None


def _save_state(session_id: str, state: PlannerState, plan: Optional[Dict] = None, status: Optional[str] = None) -> None:
    """更新会话的状态/计划/状态标记。"""
    with get_connection() as conn:
        conn.execute(
            "UPDATE planning_sessions SET state_json = ?, plan_json = ?, status = COALESCE(?, status), "
            "updated_at = datetime('now','localtime') WHERE id = ?",
            (state.model_dump_json(), json.dumps(plan, ensure_ascii=False) if plan is not None else None, status, session_id),
        )


# ============ 参数补全 ============

def fill_state(session_id: str, req: PlanFillRequest) -> PlannerState:
    """批量补全字段:只更新请求里显式提供的字段。"""
    found = get_session(session_id)
    if found is None:
        raise ValueError("规划会话不存在")
    state, plan, _, _ = found

    # 只取用户显式提供的字段(model_fields_set 记录哪些字段被传入)
    provided = req.model_dump(exclude_unset=True, exclude={"session_id"})
    for key, value in provided.items():
        if value is not None:
            setattr(state, key, value)

    # 若提供了起止日期但未给天数,自动推算
    if state.start_date and state.end_date:
        try:
            s = datetime.strptime(state.start_date, "%Y-%m-%d")
            e = datetime.strptime(state.end_date, "%Y-%m-%d")
            state.travel_days = max(1, (e - s).days + 1)
        except ValueError:
            pass

    _save_state(session_id, state, plan)
    return state


# ============ 行程生成 ============

def _state_to_trip_request(state: PlannerState):
    """把 PlannerState 转成现有多智能体需要的 TripRequest。"""
    from ..models.schemas import TripRequest
    return TripRequest(
        city=state.city or "南昌",
        start_date=state.start_date,
        end_date=state.end_date,
        travel_days=state.travel_days or 1,
        transportation=state.transportation or "公共交通",
        accommodation=state.accommodation or "经济型酒店",
        preferences=state.interests,
        free_text_input=state.notes,
    )


async def generate_plan(session_id: str) -> Tuple[Optional[Dict], List[ConflictInfo]]:
    """
    生成行程计划:参数齐全后调用多智能体,保存并做冲突检查。

    Returns:
        (计划 dict, 冲突列表)
    """
    found = get_session(session_id)
    if found is None:
        raise ValueError("规划会话不存在")
    state, _, _, user_id = found

    missing_required, _ = compute_missing(state)
    if missing_required:
        raise ValueError(f"规划参数不完整,缺少: {'、'.join(missing_labels(missing_required))}")

    planner = get_trip_planner_agent()
    trip_plan = await planner.plan_trip(_state_to_trip_request(state))
    plan = trip_plan.model_dump()

    conflicts = check_conflicts(state, plan)
    status = "has_conflict" if conflicts else "planned"
    _save_state(session_id, state, plan, status)

    # 登录用户:生成后自动保存为历史行程
    if user_id:
        try:
            from . import trip_service
            trip_service.create_trip(user_id, state.city or "南昌", plan)
        except Exception as e:
            logger.warning(f"自动保存行程失败: {e}")

    return plan, conflicts


# ============ 局部重规划 ============

REPLAN_PROMPT = """你是行程规划专家。下面是用户当前的南昌旅行计划(JSON)和一条修改要求。

请根据修改要求调整计划:**只修改必要的部分,其余保持不变**,然后返回完整的修改后计划 JSON。

要求:
1. 保持与原计划相同的 JSON 结构;
2. 只改动修改要求涉及的部分(如某天、某景点、某酒店、某餐食、预算等);
3. 若修改影响费用,同步更新 budget 汇总;
4. 景点经纬度、地址等信息保持真实,不要凭空编造;
5. 只输出 JSON,不要加任何解释。

当前计划:
{plan_json}

修改要求:
{instruction}
"""


def _extract_json(text: str) -> Optional[Dict]:
    """从 LLM 返回文本中提取 JSON 对象(兼容代码块/前后杂文)。"""
    s = str(text)
    if "```json" in s:
        s = s[s.find("```json") + 7: s.find("```", s.find("```json") + 7)]
    elif "```" in s:
        s = s[s.find("```") + 3: s.find("```", s.find("```") + 3)]
    elif "{" in s and "}" in s:
        s = s[s.find("{"): s.rfind("}") + 1]
    try:
        return json.loads(s.strip())
    except Exception:
        return None


async def replan(session_id: str, instruction: str) -> Tuple[Optional[Dict], List[ConflictInfo]]:
    """
    局部重规划:在现有计划基础上按指令做局部调整。

    Returns:
        (新计划 dict, 冲突列表)
    """
    found = get_session(session_id)
    if found is None:
        raise ValueError("规划会话不存在")
    state, plan, _, _ = found
    if not plan:
        raise ValueError("尚无已生成计划,请先生成行程")

    llm = get_llm()
    prompt = REPLAN_PROMPT.format(
        plan_json=json.dumps(plan, ensure_ascii=False),
        instruction=instruction,
    )
    response = await llm.ainvoke([("human", prompt)])
    new_plan = _extract_json(response.content)

    if new_plan is None:
        raise ValueError("局部重规划失败:LLM 返回内容无法解析")

    # 结构校验:确保仍符合 TripPlan 结构
    from ..models.schemas import TripPlan
    new_plan = TripPlan(**new_plan).model_dump()

    conflicts = check_conflicts(state, new_plan)
    status = "has_conflict" if conflicts else "planned"
    _save_state(session_id, state, new_plan, status)
    return new_plan, conflicts


# ============ 冲突检查(确定性规则) ============

def check_conflicts(state: PlannerState, plan: Optional[Dict]) -> List[ConflictInfo]:
    """
    冲突检查(确定性规则,不依赖 LLM)。

    规则:空计划 / 重复景点 / 日期天数不一致 / 预算超支 / 同行人数提示。
    距离与营业时间冲突在 M3 接入高德路线与知识库后补充。
    """
    conflicts: List[ConflictInfo] = []
    if not plan:
        conflicts.append(ConflictInfo(type="empty", level="error", message="尚无行程计划"))
        return conflicts

    days = plan.get("days") or []

    # 1) 空计划
    if not days:
        conflicts.append(ConflictInfo(type="empty", level="error", message="行程为空,未安排任何天数"))
        return conflicts

    # 2) 日期/天数一致性
    if state.travel_days and len(days) != state.travel_days:
        conflicts.append(ConflictInfo(
            type="date", level="warning",
            message=f"计划天数为 {len(days)} 天,与期望的 {state.travel_days} 天不一致",
            suggestion="请调整计划天数或修改出行日期",
        ))

    # 3) 重复景点
    seen: Dict[str, str] = {}
    for day in days:
        for attr in day.get("attractions") or []:
            name = attr.get("name")
            if not name:
                continue
            if name in seen:
                conflicts.append(ConflictInfo(
                    type="repeat", level="warning",
                    message=f"景点「{name}」重复出现(第{seen[name]}天 与 第{day.get('day_index', 0) + 1}天)",
                    suggestion="建议删除重复景点,替换为其他景点",
                ))
            else:
                seen[name] = f"第{day.get('day_index', 0) + 1}天"

    # 4) 预算超支
    if state.budget and state.budget > 0:
        total = (plan.get("budget") or {}).get("total", 0)
        if total and total > state.budget:
            conflicts.append(ConflictInfo(
                type="budget", level="warning",
                message=f"预估总费用 ¥{total} 超出预算 ¥{state.budget}",
                suggestion="可调低住宿/餐饮档次,或减少高门票景点",
            ))

    # 5) 同行人数提示(有儿童时)
    if state.party_children and state.party_children > 0:
        conflicts.append(ConflictInfo(
            type="party", level="warning",
            message=f"同行有 {state.party_children} 名儿童",
            suggestion="建议确认行程节奏轻松,并留意景点是否适合儿童",
        ))

    # 6) 营业时间校验(依赖知识库;知识库未构建时自动降级为空)
    try:
        from . import knowledge_service, postprocess
        conflicts.extend(postprocess.check_opening_hours(plan, knowledge_service.search))
    except Exception as e:
        logger.warning(f"营业时间校验跳过: {e}")

    return conflicts
