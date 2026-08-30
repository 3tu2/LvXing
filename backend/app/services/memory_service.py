"""对话记忆服务模块。

把"记忆"做成可检索、可复用的能力,支撑个性化问答。核心职责:

1. record_dialogue(): 记录一轮问答(用户问题 + AI 回答各存一条记忆);
2. save_preferences(): 把反馈分析 Agent 提取的偏好写入记忆,
   并更新该用户的"偏好画像"快照;
3. build_user_context(): 组装注入 prompt 的个性化上下文——
   (a) 用户偏好画像(profile 快照,解析成易读文本);
   (b) 与当前问题最相关的历史记忆(语义检索);
4. get_user_profile(): 读取用户画像(供管理接口 / 前端展示)。

隔离规则:所有读写都带 user_id,检索时由 vector_store 强制过滤,
不同用户之间的记忆互不可见。
"""

import json
from typing import Dict, List, Optional

from langchain_core.documents import Document

from ..config import get_settings
from ..logging import logger
from . import vector_store
from .vector_store import (
    MEMORY_TYPE_DIALOGUE,
    MEMORY_TYPE_PREFERENCE,
    MEMORY_TYPE_PROFILE,
    add_memory,
    search_memory,
    get_all_memories,
)


# ============ 对话记录 ============

def record_dialogue(user_id: str, question: str, answer: str) -> None:
    """记录一轮问答对话(问题、回答各存一条 dialogue 记忆)。

    Args:
        user_id: 用户 ID
        question: 用户的问题
        answer: 助手的回答
    """
    add_memory(
        text=f"用户提问: {question}",
        user_id=user_id,
        memory_type=MEMORY_TYPE_DIALOGUE,
        metadata={"role": "user"},
    )
    add_memory(
        text=f"助手回答: {answer}",
        user_id=user_id,
        memory_type=MEMORY_TYPE_DIALOGUE,
        metadata={"role": "assistant"},
    )


# ============ 偏好保存 ============

def save_preferences(user_id: str, preferences: Dict[str, object]) -> None:
    """
    保存反馈分析 Agent 提取的偏好:
    1. 非空字段逐条写入 preference 记忆(方便语义检索命中);
    2. 整体偏好写成 profile 快照(JSON 字符串),便于读取画像。

    Args:
        user_id: 用户 ID
        preferences: 偏好字典(见 feedback_agent 的输出格式)
    """
    # 1) 逐条偏好写入 preference 记忆
    for key, value in preferences.items():
        if value is None:
            continue
        if isinstance(value, list):
            if not value:
                continue
            text = f"用户旅行偏好 - {key}: {'、'.join(str(v) for v in value)}"
        elif isinstance(value, (str, int, float)) and str(value).strip():
            text = f"用户旅行偏好 - {key}: {value}"
        else:
            continue

        add_memory(
            text=text,
            user_id=user_id,
            memory_type=MEMORY_TYPE_PREFERENCE,
            metadata={"preference_key": str(key)},
        )

    # 2) 更新画像快照(profile 类型,先删旧的避免无限累积)
    old = get_all_memories(user_id, memory_type=MEMORY_TYPE_PROFILE, limit=10)
    old_ids = [d.metadata.get("id") for d in old if d.metadata.get("id")]
    if old_ids:
        try:
            vector_store.get_vector_store().delete(ids=old_ids)
        except Exception as e:
            logger.warning(f"清理旧画像失败: {e}")

    add_memory(
        text=json.dumps(preferences, ensure_ascii=False),
        user_id=user_id,
        memory_type=MEMORY_TYPE_PROFILE,
        metadata={"preference_key": "profile"},
    )


# ============ 画像读取 ============

def get_user_profile(user_id: str) -> Dict[str, object]:
    """读取用户最新的偏好画像快照(解析 JSON)。"""
    docs = get_all_memories(user_id, memory_type=MEMORY_TYPE_PROFILE, limit=1)
    if not docs:
        return {}
    try:
        return json.loads(docs[0].page_content)
    except Exception:
        return {}


def _profile_to_text(profile: Dict[str, object]) -> str:
    """把画像字典转成易读的中文描述(用于注入 prompt)。"""
    if not profile:
        return ""
    lines = []
    if profile.get("destinations"):
        lines.append(f"喜欢的旅行目的地: {'、'.join(profile['destinations'])}")
    if profile.get("food_preferences"):
        lines.append(f"美食偏好: {'、'.join(profile['food_preferences'])}")
    if profile.get("travel_style"):
        lines.append(f"旅行风格: {'、'.join(profile['travel_style'])}")
    if profile.get("budget_level"):
        lines.append(f"预算水平: {profile['budget_level']}")
    if profile.get("transportation"):
        lines.append(f"交通偏好: {profile['transportation']}")
    if profile.get("accommodation"):
        lines.append(f"住宿偏好: {profile['accommodation']}")
    if profile.get("pace"):
        lines.append(f"行程节奏: {profile['pace']}")
    if profile.get("notes"):
        lines.append(f"其他: {profile['notes']}")
    return "\n".join(lines)


# ============ 上下文组装(注入 prompt) ============

def build_user_context(user_id: str, query: str, top_k: Optional[int] = None) -> str:
    """
    组装个性化上下文:偏好画像 + 与该问题最相关的历史记忆。

    结果是一个字符串,调用方拼进 system prompt 即可。

    Args:
        user_id: 用户 ID
        query: 当前问题
        top_k: 检索的历史记忆条数

    Returns:
        上下文文本(无内容时返回空字符串)
    """
    settings = get_settings()
    k = top_k or settings.memory_top_k

    parts: List[str] = []

    # 1) 偏好画像
    profile = get_user_profile(user_id)
    profile_text = _profile_to_text(profile)
    if profile_text:
        parts.append("【用户偏好画像】\n" + profile_text)

    # 2) 相关历史记忆(语义检索,只在该用户自己的记忆里找)
    related = search_memory(query, user_id=user_id, top_k=k)
    if related:
        lines = []
        for doc in related:
            mtype = doc.metadata.get("type", "dialogue")
            label = "历史对话" if mtype == MEMORY_TYPE_DIALOGUE else "偏好记忆"
            lines.append(f"- [{label}] {doc.page_content}")
        parts.append("【与该问题相关的历史记忆】\n" + "\n".join(lines))

    return "\n\n".join(parts)


def format_related_memories(user_id: str, query: str, top_k: Optional[int] = None) -> List[str]:
    """给前端展示用的:返回命中的记忆原文列表。"""
    settings = get_settings()
    k = top_k or settings.memory_top_k
    related = search_memory(query, user_id=user_id, top_k=k)
    return [d.page_content for d in related]
