"""个性化问答 / 旅行对话助手 API 路由。

核心接口:
- POST /api/chat    旅行对话助手:检索南昌知识 + 高德实时信息 + 用户记忆/偏好,
                    注入 prompt 后由 LLM 回答,记录对话并异步提取偏好。

增强能力(相对早期版本):
1. 多轮对话:chat_history 携带最近几轮上下文,支持追问("那怎么过去?");
2. 实时工具:按意图调用高德(天气/POI),回答实时问题;
3. 来源标注:返回引用的知识来源 sources,降低幻觉;
4. 用户绑定:登录用户用数据库 ID(记忆跨设备持久),游客用前端 UUID。
"""

import json
from fastapi import APIRouter, BackgroundTasks, Depends, HTTPException
from fastapi.responses import StreamingResponse
from typing import List

from ...logging import logger
from ...models.schemas import ChatRequest, ChatResponse, ErrorResponse
from ...services import memory_service, knowledge_service
from ...services.llm_service import get_llm
from ...agents.feedback_agent import get_feedback_analyzer
from ..deps import get_current_user

router = APIRouter(prefix="/chat", tags=["旅行对话助手"])

CHAT_SYSTEM_PROMPT = """你是「南昌旅行助手」,熟悉南昌旅游,擅长规划行程、推荐景点美食、回答旅行问题。

请遵循以下要求:
1. 优先参考【南昌本地知识】与【实时信息】回答;知识为空则基于常识,不确定的信息要明确说明;
2. 结合【个性化上下文】中的用户偏好画像和历史记忆,给出个性化建议(如用户不吃辣,美食推荐避开辣);
3. 回答用中文,条理清晰、实用具体;
4. 涉及景点、路线、美食时给出具体名称和实用建议。

【南昌本地知识】
{knowledge}

【实时信息】
{realtime}

【个性化上下文】
{context}
"""


def _query_realtime(message: str) -> str:
    """
    按意图调用高德实时服务(天气/POI),返回拼好的文本。
    实时服务失败则返回空字符串,不阻塞主流程。
    """
    from ..services.amap_service import get_amap_service
    svc = get_amap_service()
    parts: List[str] = []

    # 天气意图
    if "天气" in message:
        try:
            infos = svc.get_weather("南昌")
            if infos:
                seg = "、".join(
                    f"{w.date} {w.day_weather} {w.day_temp}~{w.night_temp}°C"
                    for w in infos[:3]
                )
                parts.append(f"[南昌天气] {seg}")
        except Exception as e:
            logger.warning(f"天气查询失败: {e}")

    # POI 意图(附近/推荐/有什么/美食/景点)
    if any(k in message for k in ["附近", "推荐", "有什么", "好吃", "景点", "美食", "玩"]):
        try:
            keywords = "美食" if "美食" in message else ("景点" if "景点" in message else "景点美食")
            pois = svc.search_poi(keywords, "南昌")
            if pois:
                seg = "; ".join(f"{p.name}({p.address})" for p in pois[:5])
                parts.append(f"[南昌{keywords}POI] {seg}")
        except Exception as e:
            logger.warning(f"POI 查询失败: {e}")

    return "\n".join(parts)


def _format_history(chat_history: List) -> str:
    """把最近几轮对话历史转成文本(多轮上下文)。"""
    if not chat_history:
        return ""
    lines = []
    for m in chat_history[-6:]:  # 最多取最近 6 条
        role = "用户" if getattr(m, "role", "user") == "user" else "助手"
        content = getattr(m, "content", "")
        if content:
            lines.append(f"{role}: {content}")
    return "\n".join(lines)


def _prepare(request: ChatRequest, user_id: str):
    """
    检索南昌知识 + 实时信息 + 用户记忆,组装 prompt 输入。
    返回 (system 消息, human 消息, 来源列表, 相关记忆列表)。
    供普通问答与 SSE 流式问答复用。
    """
    # 1) 南昌知识
    knowledge_items: List[dict] = []
    try:
        knowledge_items = knowledge_service.search(request.message, top_k=3)
    except Exception as e:
        logger.warning(f"知识检索失败: {e}")
    knowledge = "\n\n".join(
        f"【{it['category']}·{it['title']}】{it['text']}" for it in knowledge_items
    )
    sources = list(dict.fromkeys(it.get("source", "") for it in knowledge_items if it.get("source")))

    # 2) 实时信息
    realtime = ""
    try:
        realtime = _query_realtime(request.message)
    except Exception as e:
        logger.warning(f"实时信息查询失败: {e}")

    # 3) 个性化上下文
    context = ""
    try:
        context = memory_service.build_user_context(user_id, request.message)
    except Exception as e:
        logger.warning(f"记忆检索失败: {e}")

    # 4) 多轮历史
    history_text = _format_history(request.chat_history)
    human_msg = request.message
    if history_text:
        human_msg = f"对话历史:\n{history_text}\n\n当前问题: {request.message}"

    system = CHAT_SYSTEM_PROMPT.format(
        knowledge=knowledge or "暂无",
        realtime=realtime or "暂无",
        context=context or "暂无",
    )

    # 5) 相关记忆(供前端展示)
    related = []
    try:
        related = memory_service.format_related_memories(user_id, request.message)
    except Exception as e:
        logger.warning(f"获取相关记忆失败: {e}")

    return system, human_msg, sources, related


async def _extract_preferences(user_id: str, message: str, reply: str) -> None:
    """后台提取偏好并写入记忆(供流式结束后异步执行)。"""
    analyzer = get_feedback_analyzer()
    try:
        prefs = await analyzer.analyze([message, reply])
        if any(v for v in prefs.values()):
            memory_service.save_preferences(user_id, prefs)
    except Exception as e:
        logger.warning(f"偏好提取任务失败: {e}")


@router.post(
    "",
    response_model=ChatResponse,
    summary="旅行对话助手",
    description="多轮旅行问答:南昌知识 + 高德实时信息 + 用户记忆/偏好,附来源引用",
)
async def chat(
    request: ChatRequest,
    background_tasks: BackgroundTasks,
    user=Depends(get_current_user),
):
    """旅行对话助手(需登录)。"""
    user_id = str(user["id"])
    system, human_msg, sources, related = _prepare(request, user_id)

    # LLM 生成回答
    llm = get_llm()
    try:
        response = await llm.ainvoke([
            ("system", system),
            ("human", human_msg),
        ])
        reply = str(response.content)
    except Exception as e:
        logger.error(f"LLM 调用失败: {e}")
        raise HTTPException(status_code=500, detail=f"生成回答失败: {str(e)}")

    # 记录本轮对话
    try:
        memory_service.record_dialogue(user_id, request.message, reply)
    except Exception as e:
        logger.warning(f"对话记忆写入失败: {e}")

    # 后台异步提取偏好
    background_tasks.add_task(_extract_preferences, user_id, request.message, reply)

    return ChatResponse(
        success=True,
        message="回答生成成功",
        reply=reply,
        user_id=user_id,
        related_memories=related,
        sources=sources,
        preference_updated=False,
    )


@router.post(
    "/stream",
    summary="旅行对话助手(SSE 流式)",
    description="与 /api/chat 相同的能力,但以 Server-Sent Events 流式返回答案",
)
async def chat_stream(
    request: ChatRequest,
    user=Depends(get_current_user),
):
    """旅行对话助手,SSE 流式输出(需登录)。"""
    user_id = str(user["id"])
    system, human_msg, sources, related = _prepare(request, user_id)
    llm = get_llm()

    async def event_generator():
        full_reply = ""
        try:
            async for chunk in llm.astream([
                ("system", system),
                ("human", human_msg),
            ]):
                delta = chunk.content if hasattr(chunk, "content") else str(chunk)
                if delta:
                    full_reply += delta
                    yield f"data: {json.dumps({'delta': delta}, ensure_ascii=False)}\n\n"
        except Exception as e:
            logger.error(f"LLM 流式调用失败: {e}")
            yield f"data: {json.dumps({'error': str(e)}, ensure_ascii=False)}\n\n"
        finally:
            # 保存本轮对话(同步,快速)
            try:
                memory_service.record_dialogue(user_id, request.message, full_reply)
            except Exception as e:
                logger.warning(f"对话记忆写入失败: {e}")
            # 后台异步提取偏好(不阻塞流结束)
            import asyncio
            asyncio.create_task(_extract_preferences(user_id, request.message, full_reply))
            # 结束事件:附带来源与相关记忆
            yield f"data: {json.dumps({'done': True, 'sources': sources, 'related': related}, ensure_ascii=False)}\n\n"

    return StreamingResponse(event_generator(), media_type="text/event-stream")
