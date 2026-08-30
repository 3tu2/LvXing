"""知识库 API 路由(调试/查询)。

摄取走离线脚本 scripts/kb_ingest.py(离线脚本为主);
本路由提供查询与调试接口:
- GET /api/kb/search   混合检索验证(向量 + BM25 → RRF)
- GET /api/kb/stats    知识库切片统计

在线摄取(上传文档/重新向量化)将在 M7 后台管理的知识库模块中提供。
"""

from fastapi import APIRouter, HTTPException, Query
from typing import Optional, List

from ...services import knowledge_service, retrieval_service

router = APIRouter(prefix="/kb", tags=["知识库"])


@router.get(
    "/search",
    summary="混合检索",
    description="对南昌知识库做混合检索(向量 + BM25 → RRF),返回带来源的知识条目",
)
async def search(
    q: str = Query(..., description="查询文本"),
    category: Optional[str] = Query(None, description="类别过滤: 攻略/景点/美食/拍照点/交通枢纽/营业时间"),
    top_k: int = Query(5, ge=1, le=20, description="返回条数"),
):
    """混合检索。"""
    try:
        categories = [category] if category else None
        items = knowledge_service.search(q, categories=categories, top_k=top_k)
        return {
            "success": True,
            "message": f"命中 {len(items)} 条",
            "data": items,
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"检索失败: {str(e)}")


@router.get(
    "/stats",
    summary="知识库统计",
    description="返回知识库切片总数",
)
async def stats():
    """知识库统计。"""
    return {
        "success": True,
        "collection": retrieval_service.KB_COLLECTION,
        "chunks": retrieval_service.count_documents(),
    }
