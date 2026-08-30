"""向量库服务模块(ChromaDB)。

记忆系统的"仓库":历史对话、提取出的用户偏好都以向量形式存在这里,
检索时按相似度找到"和当前问题最相关的历史记忆"。

设计要点(对应需求):
1. **按用户 ID 隔离**:每条记忆的 metadata 都带 user_id,检索时强制加
   filter={"user_id": xxx},不同用户的记忆互不可见;
2. **三类记忆条目**(metadata.type 区分):
   - `dialogue`    历史对话(用户问题 / AI 回答),用于语义检索历史上下文;
   - `preference`  反馈分析 Agent 从对话中提取的单条偏好(如"喜欢轻松行程");
   - `profile`     用户偏好画像快照(整体偏好汇总,JSON 字符串存于 text);
3. **语义相似度检索**:query 向量化后,在该用户自己的记忆里找最相似的片段。

依赖:langchain-chroma / chromadb(本地持久化,零运维)。
"""

from typing import List, Optional

from langchain_core.documents import Document

from ..config import get_settings
from .embedding_service import get_embedding

# 全局 Chroma 实例(单例)
_vector_store = None

# 记忆类型常量
MEMORY_TYPE_DIALOGUE = "dialogue"      # 历史对话
MEMORY_TYPE_PREFERENCE = "preference"  # 单条偏好
MEMORY_TYPE_PROFILE = "profile"        # 偏好画像快照


def _get_persist_dir() -> str:
    """把配置里的相对路径转成绝对路径(相对 backend/ 目录)。"""
    from pathlib import Path
    settings = get_settings()
    backend_dir = Path(__file__).resolve().parent.parent.parent  # backend/
    return str(backend_dir / settings.chroma_persist_dir)


def get_vector_store():  # -> "Chroma"(延迟导入,字符串注解避免加载时求值)
    """
    获取 Chroma 向量库实例(单例模式)。

    注意:Chroma 依赖在此处**延迟导入**,只有真正用到向量库时才需要
    langchain-chroma / chromadb 已安装;账号、行程规划等功能不受其影响。

    Returns:
        Chroma 实例
    """
    global _vector_store

    if _vector_store is None:
        from langchain_chroma import Chroma  # 延迟导入,避免未装依赖时影响启动

        settings = get_settings()
        embeddings = get_embedding()

        _vector_store = Chroma(
            collection_name=settings.rag_collection_name,
            embedding_function=embeddings,
            persist_directory=_get_persist_dir(),
        )
        print(f"✅ Chroma 记忆向量库初始化成功")
        print(f"   集合: {settings.rag_collection_name}")
        print(f"   目录: {_get_persist_dir()}")

    return _vector_store


def add_memory(text: str, user_id: str, memory_type: str, metadata: Optional[dict] = None) -> str:
    """
    写入一条记忆(自动向量化)。

    Args:
        text: 记忆内容(对话内容 / 偏好描述 / 画像 JSON)
        user_id: 用户 ID(必须,用于隔离)
        memory_type: 记忆类型(dialogue / preference / profile)
        metadata: 附加元数据(如 role、timestamp、score 等)

    Returns:
        记忆条目的 ID
    """
    store = get_vector_store()

    meta = {"user_id": user_id, "type": memory_type}
    if metadata:
        # 只保留 Chroma 支持的标量值(str/int/float/bool)
        for k, v in metadata.items():
            if isinstance(v, (str, int, float, bool)):
                meta[k] = v

    ids = store.add_texts(
        texts=[text],
        metadatas=[meta],
    )
    return ids[0] if ids else ""


def add_memories(documents: List[Document]) -> int:
    """
    批量写入记忆(Document 列表,metadata 需含 user_id / type)。

    Args:
        documents: Document 列表

    Returns:
        写入条数
    """
    store = get_vector_store()
    store.add_documents(documents)
    return len(documents)


def search_memory(
    query: str,
    user_id: str,
    top_k: Optional[int] = None,
    memory_type: Optional[str] = None,
) -> List[Document]:
    """
    语义检索某个用户的记忆(强制按 user_id 隔离)。

    Args:
        query: 查询文本(当前问题 / 需要回忆的内容)
        user_id: 用户 ID(必须,隔离键)
        top_k: 返回条数,默认取配置 rag_top_k
        memory_type: 可选,只检索某类记忆(dialogue / preference / profile)

    Returns:
        命中的记忆 Document 列表(按相似度从高到低)
    """
    settings = get_settings()
    store = get_vector_store()
    k = top_k or settings.rag_top_k

    # user_id 是硬性隔离条件,任何检索都不能绕过
    chroma_filter: dict = {"user_id": user_id}
    if memory_type:
        chroma_filter["type"] = memory_type

    return store.similarity_search(query, k=k, filter=chroma_filter)


def get_all_memories(user_id: str, memory_type: Optional[str] = None, limit: int = 100) -> List[Document]:
    """
    按写入顺序取某个用户的记忆(不排序,用于管理/展示)。

    Args:
        user_id: 用户 ID
        memory_type: 可选类型过滤
        limit: 最多取多少条

    Returns:
        Document 列表
    """
    store = get_vector_store()
    chroma_filter: dict = {"user_id": user_id}
    if memory_type:
        chroma_filter["type"] = memory_type

    result = store.get(where=chroma_filter, limit=limit)
    docs = []
    ids = result.get("ids") or []
    metadatas = result.get("metadatas") or [{}]
    for i, text in enumerate(result.get("documents") or []):
        # 把 Chroma 内部 id 放进 metadata,便于后续按 id 删除
        meta = dict(metadatas[i] or {})
        meta["id"] = ids[i] if i < len(ids) else ""
        docs.append(Document(page_content=text, metadata=meta))
    return docs


def count(user_id: Optional[str] = None) -> int:
    """记忆总数(可按用户统计)。"""
    store = get_vector_store()
    if user_id:
        ids = store.get(where={"user_id": user_id}).get("ids") or []
        return len(ids)
    return store._collection.count()


def clear():
    """清空整个向量库(删除集合)。"""
    global _vector_store
    settings = get_settings()

    if _vector_store is not None:
        try:
            _vector_store.delete_collection()
        except Exception as e:
            print(f"⚠️  删除集合失败: {e}")
        _vector_store = None

    print(f"✅ 记忆向量库已清空(集合 {settings.rag_collection_name})")
