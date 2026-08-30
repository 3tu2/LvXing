"""RAG 知识库摄取脚本(M3):清洗 → 切片 → 向量化 → 双索引。

把 data/documents/nanchang/ 下的知识文档(带 front-matter)处理成:
1. 向量索引:千问 embedding + ChromaDB(集合 nanchang_kb);
2. 关键词索引:rank_bm25(缓存到 data/kb/bm25.pkl)。

用法(在 backend/ 目录下,先激活 .venv 并安装依赖):
    python scripts/kb_ingest.py                    # 全量摄取
    python scripts/kb_ingest.py --recreate         # 清空知识库后重建
    python scripts/kb_ingest.py --dry-run          # 只解析统计,不写库
    python scripts/kb_ingest.py --search "滕王阁"  # 混合检索验证
    python scripts/kb_ingest.py --search "拌粉" --category 美食
"""

import argparse
import sys
from pathlib import Path
from typing import Dict, List, Optional, Tuple

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from langchain_core.documents import Document

from app.config import get_settings
from app.services import retrieval_service


def _parse_front_matter(text: str) -> Tuple[Dict[str, str], str]:
    """解析文件头的 front-matter(--- 包裹的 key: value 行)。"""
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


def load_documents(data_dir: Path) -> List[Document]:
    """扫描目录,解析 front-matter 并切片成 Document 列表。"""
    from langchain_text_splitters import RecursiveCharacterTextSplitter

    settings = get_settings()
    splitter = RecursiveCharacterTextSplitter(
        chunk_size=settings.rag_chunk_size,
        chunk_overlap=settings.rag_chunk_overlap,
    )

    files = sorted([p for p in data_dir.rglob("*") if p.suffix.lower() in (".md", ".txt")])
    print(f"📂 扫描到 {len(files)} 个知识文档")

    documents: List[Document] = []
    for fp in files:
        text = fp.read_text(encoding="utf-8")
        meta, body = _parse_front_matter(text)

        city = meta.get("city", "nanchang")
        category = meta.get("category", "攻略")
        title = meta.get("title", fp.stem)
        source = meta.get("source", "本地知识库")

        chunks = splitter.split_text(body)
        for i, chunk in enumerate(chunks):
            documents.append(Document(
                page_content=chunk,
                metadata={
                    "city": city,
                    "category": category,
                    "title": title,
                    "source": source,
                    "poi_name": meta.get("poi_name", ""),
                    "chunk_index": i,
                },
            ))
    return documents


def ingest(data_dir: Path, recreate: bool = False) -> int:
    """把文档写入 Chroma 并构建 BM25,返回切片总数。"""
    from langchain_chroma import Chroma
    from app.services.embedding_service import get_embedding

    documents = load_documents(data_dir)
    if not documents:
        print("❌ 没有可摄取的知识文档")
        return 0

    chroma = Chroma(
        collection_name=retrieval_service.KB_COLLECTION,
        embedding_function=get_embedding(),
        persist_directory=retrieval_service._kb_dir(),
    )
    if recreate:
        try:
            chroma.delete_collection()
        except Exception:
            pass
        chroma = Chroma(
            collection_name=retrieval_service.KB_COLLECTION,
            embedding_function=get_embedding(),
            persist_directory=retrieval_service._kb_dir(),
        )

    # 写入向量库(分批:DashScope API 对批量 input 格式敏感,一批 8 条,保证所有内容是干净 str)
    print(f"🚀 向量化 {len(documents)} 条切片(调用千问 Embedding API)...")
    batch_size = 8
    for i in range(0, len(documents), batch_size):
        batch = documents[i:i + batch_size]
        # 强制清理每条内容:去前后空白,确保是纯 str(排除 bytes/其他类型混入)
        for d in batch:
            if not isinstance(d.page_content, str):
                d.page_content = str(d.page_content)
            d.page_content = d.page_content.strip() or " "
        chroma.add_documents(batch)
        print(f"   ...已写入 {min(i + batch_size, len(documents))}/{len(documents)}")

    # 构建 BM25 索引
    print("🔍 构建 BM25 关键词索引...")
    retrieval_service.build_bm25(documents)

    print(f"✅ 摄取完成,知识库现有 {len(documents)} 条切片")
    return len(documents)


def main():
    parser = argparse.ArgumentParser(description="南昌知识库摄取脚本")
    parser.add_argument("--data-dir", default=None, help="文档目录(默认 data/documents/nanchang)")
    parser.add_argument("--recreate", action="store_true", help="清空知识库后重建")
    parser.add_argument("--dry-run", action="store_true", help="只解析统计不写库")
    parser.add_argument("--search", default=None, help="混合检索验证")
    parser.add_argument("--category", default=None, help="检索时按类别过滤")
    args = parser.parse_args()

    if args.search:
        cats = [args.category] if args.category else None
        print(f"\n🔎 混合检索: {args.search}" + (f" (类别:{args.category})" if args.category else ""))
        docs = retrieval_service.hybrid_search(args.search, categories=cats, top_k=5)
        if not docs:
            print("   未命中。请先执行 python scripts/kb_ingest.py 摄取知识库。")
            return
        for i, d in enumerate(docs, 1):
            m = d.metadata
            print(f"\n[{i}] ({m.get('category')}) {m.get('title')} 来源:{m.get('source')}")
            print(f"    {d.page_content[:120].replace(chr(10), ' ')}...")
        return

    data_dir = Path(args.data_dir) if args.data_dir else (
        Path(__file__).resolve().parent.parent / "data" / "documents" / "nanchang"
    )
    if not data_dir.exists():
        print(f"❌ 文档目录不存在: {data_dir}")
        sys.exit(1)

    if args.dry_run:
        docs = load_documents(data_dir)
        stats: Dict[str, int] = {}
        for d in docs:
            stats[d.metadata["category"]] = stats.get(d.metadata["category"], 0) + 1
        print(f"📦 待摄取切片: {len(docs)} 条")
        for c, n in stats.items():
            print(f"   - {c}: {n} 条")
        return

    ingest(data_dir, recreate=args.recreate)
    print("\n💡 验证检索: python scripts/kb_ingest.py --search \"滕王阁\"")


if __name__ == "__main__":
    main()
