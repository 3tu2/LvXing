"""后台管理服务:统计聚合、用户管理、知识库管理。"""

import json
from datetime import datetime, timedelta
from typing import Any, Dict, List, Optional

from ..config import get_settings
from ..db import get_connection
from ..logging import logger
from ..services import retrieval_service


# ============ 统计 ============

def get_stats() -> Dict[str, Any]:
    """仪表盘统计:用户数、行程数、问答数、知识库切片数、近7日趋势。"""
    with get_connection() as conn:
        users_count = conn.execute("SELECT COUNT(*) FROM users").fetchone()[0]
        trips_count = conn.execute("SELECT COUNT(*) FROM trips").fetchone()[0]

    # 近 7 日行程趋势
    trend: List[Dict[str, Any]] = []
    today = datetime.now().date()
    with get_connection() as conn:
        rows = conn.execute(
            "SELECT created_at FROM trips WHERE created_at >= ?",
            ((today - timedelta(days=6)).strftime("%Y-%m-%d"),),
        ).fetchall()
    counts: Dict[str, int] = {}
    for r in rows:
        day = (r["created_at"] or "")[:10]
        counts[day] = counts.get(day, 0) + 1
    for i in range(6, -1, -1):
        day = (today - timedelta(days=i)).strftime("%Y-%m-%d")
        trend.append({"date": day, "count": counts.get(day, 0)})

    # 问答对话总数(记忆集合,未构建则 0)
    chat_count = 0
    try:
        from . import vector_store
        chat_count = vector_store.count()
    except Exception:
        pass

    kb_chunks = 0
    try:
        kb_chunks = retrieval_service.count_documents()
    except Exception:
        pass

    return {
        "users_count": users_count,
        "trips_count": trips_count,
        "chat_count": chat_count,
        "kb_chunks": kb_chunks,
        "trips_last_7d": trend,
    }


# ============ 用户管理 ============

def list_users() -> List[Dict[str, Any]]:
    """用户列表(含每人行程数)。"""
    with get_connection() as conn:
        rows = conn.execute(
            """
            SELECT u.id, u.username, u.nickname, u.role, u.status, u.created_at,
                   (SELECT COUNT(*) FROM trips t WHERE t.user_id = u.id) AS trips_count
            FROM users u
            ORDER BY u.id DESC
            """
        ).fetchall()
    return [dict(r) for r in rows]


def set_user_status(user_id: int, status: str) -> bool:
    """启用/禁用用户。status: active / disabled。"""
    if status not in ("active", "disabled"):
        raise ValueError("无效状态")
    with get_connection() as conn:
        cur = conn.execute(
            "UPDATE users SET status = ? WHERE id = ?",
            (status, user_id),
        )
        return cur.rowcount > 0


# ============ 知识库管理 ============

def list_kb(limit: int = 100) -> List[Dict[str, Any]]:
    """知识库条目列表(从 ChromaDB 读,未构建则空)。"""
    try:
        chroma = retrieval_service._get_chroma()
        result = chroma.get(limit=limit)
        items = []
        ids = result.get("ids") or []
        docs = result.get("documents") or []
        metas = result.get("metadatas") or [{}]
        for i, doc_id in enumerate(ids):
            meta = metas[i] or {}
            items.append({
                "id": doc_id,
                "text": docs[i] or "",  # 返回全文,前端编辑时可回填完整内容
                "category": meta.get("category", ""),
                "title": meta.get("title", ""),
                "source": meta.get("source", ""),
            })
        return items
    except Exception as e:
        logger.warning(f"知识库读取失败(可能未构建): {e}")
        return []


def _rebuild_bm25(chroma) -> None:
    """从当前 Chroma 全量条目重建 BM25 关键词索引。"""
    from langchain_core.documents import Document
    result = chroma.get()
    docs = result.get("documents") or []
    metas = result.get("metadatas") or [{}]
    documents = [Document(page_content=docs[i], metadata=metas[i] or {}) for i in range(len(docs))]
    retrieval_service.build_bm25(documents)


def _kb_metadata(category: str, title: str, source: str, poi_name: str) -> dict:
    """构造知识条目元数据。"""
    return {
        "city": "nanchang",
        "category": category or "攻略",
        "title": title or "",
        "source": source or "后台添加",
        "poi_name": poi_name or "",
    }


def add_kb(text: str, category: str = "攻略", title: str = "", source: str = "后台添加", poi_name: str = "") -> str:
    """新增知识条目:向量化写入 Chroma 并重建 BM25,返回新条目 ID。"""
    chroma = retrieval_service._get_chroma()
    ids = chroma.add_texts(
        texts=[text],
        metadatas=[_kb_metadata(category, title, source, poi_name)],
    )
    _rebuild_bm25(chroma)
    return ids[0] if ids else ""


def update_kb(kb_id: str, text: str, category: str = "", title: str = "", source: str = "", poi_name: str = "") -> bool:
    """修改知识条目:删旧 → 加新(保留未提供的元数据)→ 重建 BM25。"""
    chroma = retrieval_service._get_chroma()

    # 取旧条目元数据,用于补全未提供的字段
    old = chroma.get(ids=[kb_id])
    old_metas = (old.get("metadatas") or [{}])[0] or {}

    meta = _kb_metadata(
        category or old_metas.get("category", "攻略"),
        title or old_metas.get("title", ""),
        source or old_metas.get("source", "后台添加"),
        poi_name or old_metas.get("poi_name", ""),
    )

    chroma.delete(ids=[kb_id])
    chroma.add_texts(texts=[text], metadatas=[meta])
    _rebuild_bm25(chroma)
    return True


def delete_kb(kb_id: str) -> bool:
    """删除知识库单条,并重建 BM25 索引。"""
    try:
        chroma = retrieval_service._get_chroma()
        chroma.delete(ids=[kb_id])
        _rebuild_bm25(chroma)
        return True
    except Exception as e:
        logger.warning(f"删除知识失败: {e}")
        return False


# ============ 批量导入 ============

def _parse_front_matter(text: str) -> tuple:
    """解析 Markdown front-matter(--- 包裹的 key: value 行)。"""
    if not text.startswith("---"):
        return {}, text
    end = text.find("\n---", 3)
    if end == -1:
        return {}, text
    head = text[3:end].strip()
    body = text[end + 4:].lstrip("\n")
    meta: Dict[str, str] = {}
    for line in head.splitlines():
        if ":" in line:
            k, _, v = line.partition(":")
            meta[k.strip()] = v.strip()
    return meta, body


def _split_to_documents(text: str, meta: Dict[str, str]) -> list:
    """把一段文本按配置切片,转成带元数据的 Document 列表。"""
    from langchain_core.documents import Document
    from langchain_text_splitters import RecursiveCharacterTextSplitter

    settings = get_settings()
    splitter = RecursiveCharacterTextSplitter(
        chunk_size=settings.rag_chunk_size,
        chunk_overlap=settings.rag_chunk_overlap,
    )
    chunks = splitter.split_text(text)
    documents = []
    for i, chunk in enumerate(chunks):
        documents.append(Document(
            page_content=chunk,
            metadata={
                "city": "nanchang",
                "category": meta.get("category", "攻略"),
                "title": meta.get("title", ""),
                "source": meta.get("source", "批量导入"),
                "poi_name": meta.get("poi_name", ""),
                "chunk_index": i,
            },
        ))
    return documents


def _parse_json_documents(content: str) -> list:
    """解析 JSON 内容:支持 [{text, category, title, source, poi_name}] 或单对象。"""
    data = json.loads(content)
    if isinstance(data, dict):
        data = [data]
    documents = []
    for item in data:
        if not isinstance(item, dict) or not item.get("text"):
            continue
        meta = {
            "category": item.get("category", "攻略"),
            "title": item.get("title", ""),
            "source": item.get("source", "批量导入"),
            "poi_name": item.get("poi_name", ""),
        }
        documents.extend(_split_to_documents(str(item["text"]), meta))
    return documents


def import_kb_files(files: List[Dict[str, str]]) -> Dict[str, int]:
    """
    批量导入知识文件:files=[{filename, content}]。
    支持 .md/.txt(front-matter)与 .json(数组或单对象)。
    向量化写入 Chroma 并重建 BM25,返回 {imported, skipped}。
    """
    documents = []
    skipped = 0
    for f in files:
        name = f.get("filename", "")
        content = f.get("content", "")
        if not content or not content.strip():
            skipped += 1
            continue
        try:
            if name.lower().endswith(".json"):
                documents.extend(_parse_json_documents(content))
            else:
                meta, body = _parse_front_matter(content)
                if not body.strip():
                    skipped += 1
                    continue
                documents.extend(_split_to_documents(body, meta))
        except Exception as e:
            logger.warning(f"解析文件 {name} 失败: {e}")
            skipped += 1

    if not documents:
        return {"imported": 0, "skipped": skipped}

    chroma = retrieval_service._get_chroma()
    chroma.add_documents(documents)
    _rebuild_bm25(chroma)
    return {"imported": len(documents), "skipped": skipped}
