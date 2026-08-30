"""混合检索服务:向量检索(ChromaDB)+ BM25 关键词检索 + RRF 融合。

这是 RAG 知识增强的"查询"端,配合摄取脚本(scripts/kb_ingest.py)使用:
- 向量检索:千问 embedding + ChromaDB(语义相似);
- 关键词检索:rank_bm25(南昌专有名词如"拌粉""滕王阁"召回更稳);
- 融合:Reciprocal Rank Fusion(RRF)合并两路结果。

设计要点:
1. 知识库使用独立集合 nanchang_kb(与记忆系统的 travel_kb 分开);
2. 依赖(chromadb / rank_bm25)延迟导入,未安装时降级为纯向量检索或返回空,
   不影响账号、行程规划等核心功能启动;
3. 中文分词用字符 2-gram(零依赖),英文/数字按词处理。
"""

import re
from typing import Any, Dict, List, Optional

from langchain_core.documents import Document

from ..config import get_settings
from ..logging import logger

KB_COLLECTION = "nanchang_kb"      # 知识库集合名(区别于记忆集合)
BM25_PKL = "bm25.pkl"              # BM25 索引缓存文件名
BM25_DOCS = "bm25_docs.json"       # BM25 对应文本/元数据缓存文件名


def _kb_dir() -> str:
    """知识库持久化目录(backend/data/kb)。"""
    from pathlib import Path
    backend_dir = Path(__file__).resolve().parent.parent.parent
    return str(backend_dir / "data" / "kb")


def _get_chroma():
    """获取知识库 Chroma 实例(延迟导入,首次调用才建)。"""
    from langchain_chroma import Chroma
    from .embedding_service import get_embedding
    return Chroma(
        collection_name=KB_COLLECTION,
        embedding_function=get_embedding(),
        persist_directory=_kb_dir(),
    )


# ============ 中文分词(零依赖) ============

def tokenize(text: str) -> List[str]:
    """中文 2-gram + 英文/数字按词,用于 BM25。"""
    tokens: List[str] = []
    for seg in re.findall(r"[\u4e00-\u9fff]+|[A-Za-z0-9]+", text):
        if re.match(r"[\u4e00-\u9fff]", seg):
            if len(seg) == 1:
                tokens.append(seg)
            else:
                tokens.extend(seg[i:i + 2] for i in range(len(seg) - 1))
        else:
            tokens.append(seg.lower())
    return tokens


# ============ BM25 索引 ============

_bm25 = None          # rank_bm25 实例
_bm25_docs: List[Document] = []


def _load_bm25():
    """加载 BM25 索引与文档缓存(摄取脚本构建)。"""
    global _bm25, _bm25_docs
    import json
    import pickle
    from pathlib import Path

    pkl_path = Path(_kb_dir()) / BM25_PKL
    docs_path = Path(_kb_dir()) / BM25_DOCS
    if _bm25 is not None:
        return _bm25, _bm25_docs
    if pkl_path.exists() and docs_path.exists():
        with open(pkl_path, "rb") as f:
            _bm25 = pickle.load(f)
        raw = json.loads(docs_path.read_text(encoding="utf-8"))
        _bm25_docs = [Document(page_content=d["text"], metadata=d["meta"]) for d in raw]
    return _bm25, _bm25_docs


def build_bm25(documents: List[Document]) -> None:
    """用一批文档构建 BM25 索引并缓存(摄取脚本调用)。"""
    global _bm25, _bm25_docs
    import json
    import pickle
    from pathlib import Path
    from rank_bm25 import BM25Okapi

    _bm25_docs = documents
    corpus = [tokenize(d.page_content) for d in documents]
    _bm25 = BM25Okapi(corpus)

    Path(_kb_dir()).mkdir(parents=True, exist_ok=True)
    with open(Path(_kb_dir()) / BM25_PKL, "wb") as f:
        pickle.dump(_bm25, f)
    (Path(_kb_dir()) / BM25_DOCS).write_text(
        json.dumps([{"text": d.page_content, "meta": d.metadata} for d in documents], ensure_ascii=False),
        encoding="utf-8",
    )


# ============ 检索 ============

def vector_search(query: str, categories: Optional[List[str]] = None, top_k: int = 5) -> List[Document]:
    """向量检索(ChromaDB 语义相似)。"""
    chroma = _get_chroma()
    chroma_filter: Optional[Dict] = None
    if categories:
        chroma_filter = {"category": {"$in": categories}}
    return chroma.similarity_search(query, k=top_k, filter=chroma_filter)


def bm25_search(query: str, top_k: int = 5) -> List[Document]:
    """BM25 关键词检索。"""
    _load_bm25()
    if _bm25 is None or not _bm25_docs:
        return []
    scores = _bm25.get_scores(tokenize(query))
    if not len(scores):
        return []
    top_idx = sorted(range(len(scores)), key=lambda i: scores[i], reverse=True)[:top_k]
    return [_bm25_docs[i] for i in top_idx if scores[i] > 0]


def rrf_fuse(results_a: List[Document], results_b: List[Document], k: int = 60) -> List[Document]:
    """
    Reciprocal Rank Fusion:合并两路结果(倒排名次加权,名次越靠前权重越高)。
    相同内容的文档会合并(分数累加),避免重复出现。
    """
    scores: Dict[str, float] = {}
    doc_map: Dict[str, Document] = {}

    def _add(results: List[Document]):
        for rank, doc in enumerate(results):
            key = doc.page_content  # 用内容做 key,实现去重
            doc_map[key] = doc
            scores[key] = scores.get(key, 0.0) + 1.0 / (k + rank + 1)

    _add(results_a)
    _add(results_b)

    ranked = sorted(scores.items(), key=lambda x: x[1], reverse=True)
    return [doc_map[key] for key, _ in ranked]


def hybrid_search(
    query: str,
    categories: Optional[List[str]] = None,
    top_k: int = 5,
) -> List[Document]:
    """
    混合检索:向量 + BM25 → RRF 融合 → Top-K。

    任一检索失败都降级(向量失败则只用 BM25,BM25 失败则只用向量),
    确保不因单个依赖缺失而抛错。
    """
    vec_docs: List[Document] = []
    bm_docs: List[Document] = []

    try:
        vec_docs = vector_search(query, categories=categories, top_k=top_k * 2)
    except Exception as e:
        logger.warning(f"向量检索不可用: {e}")

    try:
        bm_docs = bm25_search(query, top_k=top_k * 2)
    except Exception as e:
        logger.warning(f"BM25 检索不可用: {e}")

    if vec_docs and bm_docs:
        fused = rrf_fuse(vec_docs, bm_docs)
        return fused[:top_k]
    if vec_docs:
        return vec_docs[:top_k]
    return bm_docs[:top_k]


def count_documents() -> int:
    """知识库文档(切片)总数。"""
    try:
        return _get_chroma()._collection.count()
    except Exception:
        return 0
