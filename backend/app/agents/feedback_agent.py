"""反馈分析 Agent(用户旅行偏好提取)。

需求:结合反馈分析 Agent 提取用户旅行偏好,并在后续对话中注入偏好上下文。

职责:输入用户的对话/反馈文本,让 LLM 从中提取结构化的旅行偏好,
输出一个固定格式的 JSON 字典。提取出的偏好由 memory_service 写入
该用户的记忆(向量库),后续问答时自动检索并注入 prompt。

实现要点:
- 复用 llm_service 的 ChatOpenAI(DeepSeek),不新建模型;
- 用"提示词 + JSON 解析"的方式(与 trip_planner_agent 的解析风格一致),
  不依赖额外的结构化输出框架;
- 解析失败时降级返回空画像,不阻塞主流程。
"""

import json
import re
from typing import Dict, List

from ..logging import logger
from ..services.llm_service import get_llm

# 偏好提取提示词:要求 LLM 只提取"明确表达"的偏好,未提及的字段留空。
PREFERENCE_EXTRACT_PROMPT = """你是用户旅行偏好分析专家。请从下面的对话/反馈文本中,提取用户的旅行偏好,并严格按以下 JSON 格式输出(不要输出任何其他文字):

{
  "destinations": [],        # 用户提到想去的/喜欢的城市或地区,如 ["上海", "日本"]
  "food_preferences": [],    # 美食偏好,如 ["海鲜", "粤菜", "不吃辣"]
  "travel_style": [],        # 旅行风格,如 ["历史文化", "自然风光", "休闲度假", "美食", "购物"]
  "budget_level": "",        # 预算水平: 经济 / 舒适 / 豪华 / 未提及
  "transportation": "",      # 交通偏好,如 "高铁", "自驾", "公共交通"
  "accommodation": "",       # 住宿偏好,如 "民宿", "经济型酒店", "五星酒店"
  "pace": "",                # 行程节奏: 轻松 / 适中 / 紧凑 / 未提及
  "notes": ""                # 其他值得记住的偏好或约束,如 "对海鲜过敏", "带老人小孩同行"
}

规则:
1. 只提取对话中**明确表达**的信息,不要猜测;
2. 数组字段没有提到就输出空数组,字符串字段没有提到就输出空字符串;
3. 如果对话完全与旅行无关,所有字段都输出空值;
4. 只输出 JSON,不要加解释。
"""

_EMPTY_PREFERENCES: Dict[str, object] = {
    "destinations": [],
    "food_preferences": [],
    "travel_style": [],
    "budget_level": "",
    "transportation": "",
    "accommodation": "",
    "pace": "",
    "notes": "",
}


class FeedbackAnalyzer:
    """反馈分析 Agent:从对话文本中提取用户旅行偏好。"""

    def __init__(self):
        """初始化:复用全局 LLM 实例。"""
        self.llm = get_llm()

    async def analyze(self, texts: List[str]) -> Dict[str, object]:
        """
        分析对话/反馈文本,提取旅行偏好。

        Args:
            texts: 对话文本列表(如 [用户问题, 助手回答]),会拼接后一起分析

        Returns:
            偏好字典(未提及的字段为空,失败时返回全空字典)
        """
        content = "\n".join(texts).strip()
        if not content:
            return dict(_EMPTY_PREFERENCES)

        try:
            response = await self.llm.ainvoke([
                ("system", PREFERENCE_EXTRACT_PROMPT),
                ("human", f"对话内容:\n{content}"),
            ])
            return self._parse_response(response.content)
        except Exception as e:
            logger.warning(f"偏好提取失败: {e}")
            return dict(_EMPTY_PREFERENCES)

    @staticmethod
    def _parse_response(response: str) -> Dict[str, object]:
        """从 LLM 返回文本中解析 JSON(兼容代码块包裹/前后杂文)。"""
        text = str(response)
        try:
            # 情况1:```json 代码块
            if "```json" in text:
                start = text.find("```json") + 7
                end = text.find("```", start)
                text = text[start:end].strip()
            elif "```" in text:
                start = text.find("```") + 3
                end = text.find("```", start)
                text = text[start:end].strip()
            # 情况2:直接提取第一个 { 到最后一个 }
            elif "{" in text and "}" in text:
                start = text.find("{")
                end = text.rfind("}") + 1
                text = text[start:end]
            else:
                # 完全不含 JSON 结构,直接返回空画像
                return dict(_EMPTY_PREFERENCES)

            data = json.loads(text)
        except Exception:
            logger.warning(f"偏好 JSON 解析失败,返回空画像: {str(response)[:80]}")
            return dict(_EMPTY_PREFERENCES)

        # 用空模板兜底,只保留模板里定义的字段,防止 LLM 输出奇怪结构
        result = dict(_EMPTY_PREFERENCES)
        for key in result:
            if key in data and data[key] is not None:
                result[key] = data[key]
        return result


# 全局单例
_feedback_analyzer = None


def get_feedback_analyzer() -> FeedbackAnalyzer:
    """获取反馈分析 Agent 实例(单例)。"""
    global _feedback_analyzer
    if _feedback_analyzer is None:
        _feedback_analyzer = FeedbackAnalyzer()
    return _feedback_analyzer
