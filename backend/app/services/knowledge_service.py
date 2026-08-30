"""知识服务:检索南昌本地知识并拼成可注入 prompt 的上下文。

上层(行程规划 / 问答)通过这里获取知识,不直接接触向量库与 BM25:
- search():        混合检索,返回结构化的知识条目列表;
- build_context(): 拼接成可注入 prompt 的文本(带来源标注);
- 所有方法都做异常降级:知识库未构建 / 依赖缺失时返回空,不阻塞主流程。
"""

from typing import Dict, List, Optional

from ..logging import logger
from . import retrieval_service


def search(
    query: str,
    categories: Optional[List[str]] = None,
    top_k: int = 5,
) -> List[Dict]:
    """
    混合检索南昌知识。

    Args:
        query: 查询文本
        categories: 可选类别过滤(攻略/景点/美食/拍照点/交通枢纽/营业时间)
        top_k: 返回条数

    Returns:
        [{text, category, title, source}] 列表(检索失败返回空列表)
    """
    try:
        docs = retrieval_service.hybrid_search(query, categories=categories, top_k=top_k)
        return [
            {
                "text": d.page_content,
                "category": d.metadata.get("category", ""),
                "title": d.metadata.get("title", ""),
                "source": d.metadata.get("source", ""),
            }
            for d in docs
        ]
    except Exception as e:
        logger.warning(f"检索失败(降级为空): {e}")
        return []


def build_context(
    query: str,
    categories: Optional[List[str]] = None,
    top_k: int = 3,
) -> str:
    """
    检索并拼接知识上下文(带来源标注),供注入 prompt。

    Returns:
        上下文文本(无知识时返回空字符串)
    """
    items = search(query, categories=categories, top_k=top_k)
    if not items:
        return ""
    parts = []
    for it in items:
        parts.append(
            f"【{it['category']}·{it['title']}】{it['text']}\n(来源:{it['source']})"
        )
    return "\n\n".join(parts)


def build_planning_context(city: str, interests: List[str], top_k: int = 5) -> str:
    """
    针对行程规划场景拼接知识:按城市 + 兴趣检索景点/美食/攻略/营业时间。

    Args:
        city: 城市(南昌)
        interests: 兴趣标签

    Returns:
        上下文文本
    """
    interest_str = "、".join(interests) if interests else "南昌旅游"
    query = f"{city} {interest_str} 景点 美食 攻略 营业时间"
    # 优先景点/攻略/美食/营业时间,拍照与交通按需补充
    ctx = build_context(query, categories=["景点", "攻略", "美食", "营业时间"], top_k=top_k)
    if not ctx:
        ctx = build_context(query, top_k=top_k)
    return ctx


def get_opening_hours_text(attraction_name: str, top_k: int = 2) -> str:
    """检索某景点的营业时间文本(供后处理校验)。"""
    hits = search(f"{attraction_name} 营业时间 开放时间 闭馆", categories=["营业时间"], top_k=top_k)
    return " ".join(h.get("text", "") for h in hits)
