"""千问 Embedding 服务模块(RAG 向量化)。

把文本变成"向量"(一串数字),是 RAG 检索的前提:文档入库前要先向量化,
用户提问时也要把问题向量化,然后在向量库里找最相似的片段。

本模块使用**阿里云百炼 DashScope 官方 SDK**调用 text-embedding-v3,
原因:langchain_openai 的 OpenAIEmbeddings 会在内部把长文本先转成
token id 列表,再把 List[List[int]] 作为 input 传给 DashScope 兼容端点,
而 DashScope 严格要求 input 必须是 str 或 List[str],因此会报
"contents is neither str nor list of str." 错误。改用官方 SDK
可以完全掌控传参格式,避免该问题。

本模块提供两种入口:
- get_embedding():返回遵循 LangChain Embeddings 协议的实例(给 Chroma /
  retrieval_service 用,它们期望的是 .embed_documents() / .embed_query())
- 底层 _dashscope_embed():直接调用 DashScope SDK,方便脚本调试。
"""

import os
import time
from typing import List

# DashScope 官方 SDK(上面已用 pip install dashscope 装好)
import dashscope
from dashscope import TextEmbedding
# LangChain 的 Embeddings 基类:Chroma 只要是这个协议的子类就能用
from langchain_core.embeddings import Embeddings
from pydantic import BaseModel, Field, ConfigDict

from ..config import get_settings


# ======================================================================
# 自定义 Embedding 类:保持 LangChain 协议,底层走 DashScope SDK
# ======================================================================
class DashScopeEmbeddings(BaseModel, Embeddings):
    """使用 DashScope 官方 SDK 的千问 Embedding 实现。

    为什么继承 BaseModel + Embeddings:
    - BaseModel:LangChain 生态很多对象都是 pydantic 模型,继承它 Chroma
      在 pickling / 持久化 metadata 时不会出错;
    - Embeddings:规定了两个必须实现的方法: embed_documents(批量) 和
      embed_query(单条),Chroma 正是靠这两个方法读写向量。
    """
    model_config = ConfigDict(arbitrary_types_allowed=True, extra="allow")

    # ---- pydantic 字段(可以实例化时传入,也可用默认) ----
    api_key: str = ""
    model: str = "text-embedding-v3"
    dimensions: int = 1024
    # 每次批量请求的条数(太多 DashScope 会限流或截断,官方文档建议 ≤25)
    batch_size: int = 16
    # 失败重试次数(网络抖动时兜底)
    max_retries: int = 3
    # 每次重试之间的等待秒数(指数退避系数)
    retry_backoff: float = 2.0

    def _call_once(self, texts: List[str]) -> List[List[float]]:
        """单次请求 DashScope Embedding API,返回二维向量列表。"""
        # 保证所有输入都是非空 str;DashScope 不允许空字符串
        clean: List[str] = []
        for t in texts:
            s = "" if t is None else str(t).strip()
            clean.append(s if s else "空")

        resp = TextEmbedding.call(
            model=self.model,
            input=clean,           # 必须是 List[str]!这就是我们绕开 OpenAI 兼容端的原因
            text_type="document",  # document / query:检索文献文档用 document,查询用 query
            dimensions=self.dimensions,
        )

        if resp.status_code != 200 or resp.output is None:
            raise RuntimeError(
                f"DashScope Embedding 调用失败 code={resp.status_code} "
                f"msg={getattr(resp, 'message', None) or getattr(resp, 'code', None) or resp}"
            )

        # 返回结果:resp.output.embeddings 是 [{embedding:[...]}, {...}]
        embs = resp.output.get("embeddings", [])
        vectors: List[List[float]] = [e["embedding"] for e in embs]
        # 以防万一返回条数和输入不一致
        if len(vectors) != len(clean):
            raise RuntimeError(
                f"DashScope Embedding 返回条数异常:输入 {len(clean)},返回 {len(vectors)}"
            )
        return vectors

    # ------------------------------------------------------------
    # 批量/单条接口(带重试 + 分批)
    # ------------------------------------------------------------
    def embed_documents(self, texts: List[str]) -> List[List[float]]:
        """给 Chroma / 检索服务用:把 N 条文档文本变成 N 条向量。"""
        # 设置 API Key(每次调用设置一次,不重复开销)
        if self.api_key:
            dashscope.api_key = self.api_key

        all_vectors: List[List[float]] = []
        # 按 batch_size 分批,每批失败重试 max_retries 次
        for start in range(0, len(texts), self.batch_size):
            batch = texts[start:start + self.batch_size]
            last_err: Exception | None = None
            for attempt in range(1, self.max_retries + 1):
                try:
                    all_vectors.extend(self._call_once(batch))
                    last_err = None
                    break
                except Exception as exc:  # noqa: BLE001
                    last_err = exc
                    wait_s = self.retry_backoff ** attempt
                    print(f"   [Embedding 重试 {attempt}/{self.max_retries}] {exc};等待 {wait_s}s 后重试")
                    time.sleep(wait_s)
            if last_err is not None:
                raise RuntimeError(f"Embedding 批量请求多次失败(第 {start}-{start + len(batch)} 条):{last_err}")
        return all_vectors

    def embed_query(self, text: str) -> List[float]:
        """给 Chroma / 检索服务用:把单条查询文本变成 1 条向量。
        (text-embedding-v3 推荐查询时 text_type="query",此处单独处理)
        """
        if self.api_key:
            dashscope.api_key = self.api_key

        clean = str(text).strip() or "空"
        last_err: Exception | None = None
        for attempt in range(1, self.max_retries + 1):
            try:
                resp = TextEmbedding.call(
                    model=self.model,
                    input=clean,
                    text_type="query",      # 查询用 query 更精准
                    dimensions=self.dimensions,
                )
                if resp.status_code == 200 and resp.output:
                    embs = resp.output.get("embeddings", [])
                    if embs:
                        return embs[0]["embedding"]
                    raise RuntimeError("DashScope 返回空向量")
                raise RuntimeError(
                    f"code={resp.status_code} msg={getattr(resp, 'message', None) or resp}"
                )
            except Exception as exc:  # noqa: BLE001
                last_err = exc
                wait_s = self.retry_backoff ** attempt
                print(f"   [Embedding 查询重试 {attempt}/{self.max_retries}] {exc};等待 {wait_s}s")
                time.sleep(wait_s)
        raise RuntimeError(f"Embedding 查询多次失败:{last_err}")


# ======================================================================
# 全局单例(和旧版 get_embedding() 保持完全兼容)
# ======================================================================
_embedding_instance: DashScopeEmbeddings | None = None


def get_embedding() -> DashScopeEmbeddings:
    """获取千问 Embedding 实例(单例模式)。

    配置来源(与 .env 变量一一对应):
    - DASHSCOPE_API_KEY  阿里云百炼 API Key(必填)
    - EMBEDDING_MODEL    模型名,默认 text-embedding-v3
    - EMBEDDING_BASE_URL 未使用(官方 SDK 自带默认端点),保留兼容
    - (从 Settings 读取) embedding_dimensions 向量维度,默认 1024

    Returns:
        DashScopeEmbeddings 实例(实现了 LangChain Embeddings 协议)
    """
    global _embedding_instance

    if _embedding_instance is None:
        settings = get_settings()

        api_key = settings.dashscope_api_key
        if not api_key:
            raise ValueError(
                "千问 Embedding API Key 未配置,请在 .env 中设置 DASHSCOPE_API_KEY"
            )

        _embedding_instance = DashScopeEmbeddings(
            api_key=api_key,
            model=settings.embedding_model,
            dimensions=settings.embedding_dimensions,
            batch_size=16,
            max_retries=3,
            retry_backoff=2.0,
        )

        # DashScope SDK 读取全局 api_key(即使我们在方法里也会设置一次,提前设置更保险)
        os.environ.setdefault("DASHSCOPE_API_KEY", api_key)
        dashscope.api_key = api_key

        print(f"✅ 千问 Embedding 服务初始化成功(DashScope SDK)")
        print(f"   模型: {settings.embedding_model}  维度: {settings.embedding_dimensions}")
        print(f"   批量大小: 16   失败重试: 3 次")

    return _embedding_instance


def reset_embedding():
    """重置 Embedding 实例(用于测试或重新配置)。"""
    global _embedding_instance
    _embedding_instance = None
