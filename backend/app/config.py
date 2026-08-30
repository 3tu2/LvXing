"""配置管理模块。

这个文件是整个后端的"总开关",负责从 .env 文件和环境变量里读取各种配置,
比如:高德地图的 API Key、大模型的 API Key、服务器端口等。

小白可以这样理解:很多地方都要用到的"设置项"都集中在这里定义,
别的地方只需要调用 get_settings() 就能拿到同一个配置对象,避免到处重复写。
"""

import os
import sys
from typing import List
from pydantic_settings import BaseSettings  # 用来定义"配置类",能自动从环境变量/文件读取值
from dotenv import load_dotenv  # 用来加载 .env 文件,把里面的 KEY=VALUE 读进环境变量
from .logging import logger  # 统一日志(loguru)

# 兼容 Windows GBK 控制台/管道:项目日志含 emoji,统一把标准输出重配置为 UTF-8,
# 否则在 cmd 或重定向日志时会因编码失败而崩溃。
for _stream in (sys.stdout, sys.stderr):
    try:
        _stream.reconfigure(encoding="utf-8", errors="replace")
    except Exception:
        pass

# 加载环境变量:读取 backend/ 目录下的 .env 文件
load_dotenv()


class Settings(BaseSettings):
    """应用配置类。

    继承自 BaseSettings 后,每一个类属性(比如 amap_api_key)都会自动
    去环境变量 / .env 文件里找同名的大写变量(比如 AMAP_API_KEY)来填充。
    找不到就用等号后面的默认值。
    """

    # 应用基本配置
    app_name: str = "LangGraph智能旅行助手"   # 应用名称
    app_version: str = "1.0.0"                    # 应用版本号
    debug: bool = False                           # 是否开启调试模式

    # 服务器配置
    host: str = "0.0.0.0"   # 监听地址,0.0.0.0 表示允许局域网内其他设备访问
    port: int = 8000        # 监听端口

    # CORS配置 - 用字符串保存多个来源,在代码中再分割成列表
    # CORS(跨域资源共享):允许哪些前端页面可以调用这个后端接口
    cors_origins: str = "http://localhost:5173,http://localhost:3000,http://127.0.0.1:5173,http://127.0.0.1:3000"

    # 高德地图API配置
    amap_api_key: str = ""   # 高德开放平台申请的 Web服务 API Key(搜索、路线、天气都用它)

    # Unsplash API配置(免费图片网站,用来给景点配图)
    unsplash_access_key: str = ""
    unsplash_secret_key: str = ""

    # LLM配置(实际生效的是 LLM_MODEL_ID / LLM_API_KEY / LLM_BASE_URL / LLM_TIMEOUT
    # 这几个环境变量,由 llm_service 直接读取;下面字段作为兜底默认值保留)
    openai_api_key: str = ""                             # LLM 的 API Key(备用)
    openai_base_url: str = "https://api.openai.com/v1"   # LLM 服务的接口地址(备用)
    openai_model: str = "gpt-4"                          # 使用的模型名称(备用)

    # ---------- RAG:千问 Embedding API 配置 ----------
    # 向量化模型独立于 LLM,走阿里云百炼(text-embedding-v3,OpenAI 兼容模式)
    dashscope_api_key: str = ""                                          # 阿里云百炼 API Key
    embedding_model: str = "text-embedding-v3"                           # Embedding 模型名
    embedding_base_url: str = "https://dashscope.aliyuncs.com/compatible-mode/v1"  # OpenAI 兼容端点
    embedding_dimensions: int = 1024                                     # 向量维度(text-embedding-v3 支持 1024/768/512)

    # ---------- RAG:向量库(Chroma)配置 ----------
    chroma_persist_dir: str = "data/chroma"    # Chroma 持久化目录(相对 backend/ 目录)
    rag_collection_name: str = "travel_kb"     # 向量库集合名
    rag_top_k: int = 3                         # 每次检索返回的片段条数
    rag_chunk_size: int = 400                  # 文档分块大小(字符,中文 300~500 为宜)
    rag_chunk_overlap: int = 80                # 分块重叠(字符)

    # ---------- 记忆系统配置(个性化问答) ----------
    memory_top_k: int = 5                          # 问答时检索的历史记忆条数
    enable_preference_extraction: bool = True      # 是否启用反馈分析 Agent 提取偏好

    # ---------- 认证与数据库配置 ----------
    jwt_secret: str = "dev-secret-change-me"       # JWT 签名密钥(生产必须用环境变量覆盖!)
    jwt_algorithm: str = "HS256"                   # JWT 签名算法
    jwt_expire_minutes: int = 10080                # token 有效期(分钟,默认 7 天)
    db_path: str = "data/app.db"                   # SQLite 数据库文件路径(相对 backend/ 目录)

    # 日志配置
    log_level: str = "INFO"   # 日志级别:DEBUG / INFO / WARNING / ERROR

    class Config:
        """pydantic 的配置项(注意这是 pydantic 旧版的写法,用于指定 .env 文件等)。"""
        env_file = ".env"          # 指定从哪个文件读取配置
        case_sensitive = False     # 环境变量名不区分大小写(AMAP_API_KEY 也能匹配 amap_api_key)
        extra = "ignore"           # 忽略 .env 里多余的、这里没定义的变量(避免报错)

    def get_cors_origins_list(self) -> List[str]:
        """把逗号分隔的 CORS 字符串拆成 Python 列表。

        比如 "a.com,b.com" -> ["a.com", "b.com"],方便后面直接传给中间件。
        """
        return [origin.strip() for origin in self.cors_origins.split(',')]


# 创建全局配置实例(整个程序只有这一个实例,这就是"单例模式")
settings = Settings()


def get_settings() -> Settings:
    """获取全局配置实例。

    别的地方想读配置时,就调用 get_settings().xxx 来取,
    保证所有模块用的是同一份配置。
    """
    return settings


# 验证必要的配置
def validate_config():
    """在启动时检查配置是否齐全。

    如果缺少关键配置(比如高德 API Key),会抛出异常阻止启动,
    避免程序带着错误配置运行。
    """
    errors = []    # 收集"必须修复"的错误
    warnings = []  # 收集"可以继续但需注意"的警告

    if not settings.amap_api_key:
        errors.append("AMAP_API_KEY未配置")

    # JWT 密钥校验:使用弱默认值/空值时给出明确警告(生产必须改)
    if settings.jwt_secret in ("", "dev-secret-change-me"):
        warnings.append("JWT_SECRET 使用了默认值,生产环境必须改为随机长字符串")

    # ChatOpenAI 从 LLM_API_KEY 读取,不强制要求 OPENAI_API_KEY
    llm_api_key = os.getenv("LLM_API_KEY") or os.getenv("OPENAI_API_KEY")
    if not llm_api_key:
        warnings.append("LLM_API_KEY或OPENAI_API_KEY未配置,LLM功能可能无法使用")

    # 有错误就抛出异常,阻止启动
    if errors:
        error_msg = "配置错误:\n" + "\n".join(f"  - {e}" for e in errors)
        raise ValueError(error_msg)

    # 有警告就记录日志,但继续运行
    for w in warnings:
        logger.warning(f"配置警告: {w}")

    return True


# 打印配置信息(用于调试)
def print_config():
    """打印当前配置(会隐藏 API Key 等敏感信息,只显示"已配置/未配置")。"""
    logger.info(f"应用名称: {settings.app_name}")
    logger.info(f"版本: {settings.app_version}")
    logger.info(f"服务器: {settings.host}:{settings.port}")
    logger.info(f"高德地图API Key: {'已配置' if settings.amap_api_key else '未配置'}")

    # 检查LLM配置
    llm_api_key = os.getenv("LLM_API_KEY") or os.getenv("OPENAI_API_KEY")
    llm_base_url = os.getenv("LLM_BASE_URL") or settings.openai_base_url
    llm_model = os.getenv("LLM_MODEL_ID") or settings.openai_model

    logger.info(f"LLM API Key: {'已配置' if llm_api_key else '未配置'}")
    logger.info(f"LLM Base URL: {llm_base_url}")
    logger.info(f"LLM Model: {llm_model}")
    logger.info(f"日志级别: {settings.log_level}")
