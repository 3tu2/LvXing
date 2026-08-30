"""规划后处理:降低路线冲突与内容幻觉的确定性规则(不依赖 LLM)。

在行程生成/修改后执行,输出冲突提示。当前实现营业时间相关校验:
- 周一闭馆检测:计划某天是周一,且该景点知识含"周一闭馆";
- 预约提示:景点需实名预约时提醒。

距离/交通冲突依赖高德路线(实时),在后续接入 amap_service 后补充;
存在性校验依赖高德 POI 交叉验证,亦为后续扩展点。
"""

from datetime import datetime
from typing import Any, Callable, Dict, List, Optional

from ..models.schemas import ConflictInfo


def weekday_of(date_str: str) -> Optional[int]:
    """返回星期几(0=周一 … 6=周日),解析失败返回 None。"""
    try:
        return datetime.strptime(date_str, "%Y-%m-%d").weekday()
    except (ValueError, TypeError):
        return None


def detect_monday_closure(weekday: int, knowledge_text: str) -> bool:
    """判断是否为周一且知识文本标注了周一闭馆。"""
    return weekday == 0 and ("周一闭馆" in knowledge_text or "星期一闭馆" in knowledge_text)


def check_opening_hours(
    plan: Optional[Dict[str, Any]],
    kb_search: Callable[[str, Optional[List[str]], int], List[Dict]],
) -> List[ConflictInfo]:
    """
    营业时间校验:对计划中每个景点,检索营业时间知识并检查冲突。

    Args:
        plan: 旅行计划 dict(含 days)
        kb_search: 知识检索函数(与 knowledge_service.search 同签名),便于测试注入

    Returns:
        冲突列表
    """
    conflicts: List[ConflictInfo] = []
    if not plan:
        return conflicts

    for day in plan.get("days") or []:
        wd = weekday_of(day.get("date", ""))
        for attr in day.get("attractions") or []:
            name = attr.get("name", "")
            if not name:
                continue
            hits = kb_search(f"{name} 营业时间 开放时间 闭馆", ["营业时间"], 2)
            text = " ".join(h.get("text", "") for h in hits)
            if not text:
                continue

            if wd is not None and detect_monday_closure(wd, text):
                conflicts.append(ConflictInfo(
                    type="opening", level="warning",
                    message=f"景点「{name}」周一闭馆,但被安排在 {day.get('date')}",
                    suggestion="建议调整到其他日期或替换为其他景点",
                ))
            elif "需预约" in text or "实名预约" in text:
                conflicts.append(ConflictInfo(
                    type="booking", level="warning",
                    message=f"景点「{name}」需提前预约",
                    suggestion="请提前在官方渠道实名预约",
                ))
    return conflicts
