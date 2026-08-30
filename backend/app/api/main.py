"""FastAPI主应用。

这个文件是整个后端的"装配车间",负责:
1. 创建 FastAPI 应用实例(app)
2. 配置 CORS(让前端能跨域调用接口)
3. 注册各个路由(把 trip / poi / map 三组接口挂到 app 上)
4. 定义应用启动/关闭时要做的准备工作
5. 提供根路径(/)和健康检查(/health)两个基础接口

小白可以这样理解:把 app 想成一个大管家,各个"路由"是它的下属部门,
这里做的就是把下属部门登记到管家名下,并安排开门/关门时的杂事。
"""

from contextlib import asynccontextmanager                  # lifespan 上下文管理器
from fastapi import FastAPI, Depends                            # 用来创建 Web 应用 / 依赖注入
from fastapi.middleware.cors import CORSMiddleware              # 处理跨域问题的中间件
from ..config import get_settings, validate_config, print_config  # 从上级目录导入配置相关函数
from ..logging import logger                                    # 统一日志(loguru)
from ..services.amap_service import close_amap_tools            # 应用关闭时释放 MCP 资源
from ..db import init_db                                        # 应用启动时初始化 SQLite
from .deps import get_current_user                              # 登录依赖(核心接口强制登录)
from .routes import trip, poi, map as map_routes, chat, memory, auth, planning, kb, trips, admin  # 导入十组路由

# 获取配置(单例,全局只有一份)
settings = get_settings()


# 应用生命周期(替代已废弃的 @app.on_event)
@asynccontextmanager
async def lifespan(app: FastAPI):
    """启动:初始化数据库、校验配置;关闭:释放 MCP 资源。"""
    logger.info("=" * 60)
    logger.info(f"🚀 {settings.app_name} v{settings.app_version}")
    logger.info("=" * 60)

    try:
        init_db()
    except Exception as e:
        logger.error(f"数据库初始化失败: {e}")
        raise

    print_config()

    try:
        validate_config()
        logger.info("配置验证通过")
    except ValueError as e:
        logger.error(f"配置验证失败: {e}")
        logger.error("请检查 .env 文件并确保所有必要配置项都已设置")
        raise

    logger.info("API文档: http://localhost:8000/docs")
    logger.info("ReDoc文档: http://localhost:8000/redoc")

    yield  # 服务运行期间

    # 关闭清理
    await close_amap_tools()
    logger.info("应用已关闭")


# 创建 FastAPI 应用实例
# 这些参数会显示在自动生成的接口文档(/docs)页面上
app = FastAPI(
    title=settings.app_name,          # 应用标题
    version=settings.app_version,     # 版本号
    description="基于LangChain + LangGraph框架的智能旅行规划助手API",  # 简介
    docs_url="/docs",                 # Swagger 文档地址
    redoc_url="/redoc",               # ReDoc 文档地址
    lifespan=lifespan,                # 启动/关闭生命周期
)

# 配置CORS(跨域资源共享)
# 为什么要配?前端运行在 http://localhost:5173,后端在 http://localhost:8000,
# 浏览器默认会拦截"跨域"请求,所以需要明确告诉后端"允许这些地址来访问我"。
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.get_cors_origins_list(),  # 允许访问的来源列表
    allow_credentials=True,                          # 允许携带凭证(如 cookie)
    allow_methods=["*"],                             # 允许所有 HTTP 方法(GET/POST/...)
    allow_headers=["*"],                             # 允许所有请求头
)

# 注册路由:把十个路由模块挂载到 app 上
# prefix="/api" 表示这些接口的网址都会以 /api 开头(例如 /api/trip/plan)
# 除认证(auth)与健康检查外,所有业务接口强制登录(get_current_user 依赖拦截未登录请求)。
app.include_router(auth.router, prefix="/api")   # 认证接口:开放(注册/登录无需登录)
app.include_router(trip.router, prefix="/api", dependencies=[Depends(get_current_user)])
app.include_router(poi.router, prefix="/api", dependencies=[Depends(get_current_user)])
app.include_router(map_routes.router, prefix="/api", dependencies=[Depends(get_current_user)])
app.include_router(chat.router, prefix="/api", dependencies=[Depends(get_current_user)])
app.include_router(memory.router, prefix="/api", dependencies=[Depends(get_current_user)])
app.include_router(planning.router, prefix="/api", dependencies=[Depends(get_current_user)])
app.include_router(kb.router, prefix="/api", dependencies=[Depends(get_current_user)])
app.include_router(trips.router, prefix="/api", dependencies=[Depends(get_current_user)])
app.include_router(admin.router, prefix="/api", dependencies=[Depends(get_current_user)])


@app.get("/")
async def root():
    """根路径接口:访问 http://localhost:8000/ 时返回应用基本信息。

    常用来快速确认"后端是否跑起来了"。
    """
    return {
        "name": settings.app_name,
        "version": settings.app_version,
        "status": "running",
        "docs": "/docs",
        "redoc": "/redoc"
    }


@app.get("/health")
async def health():
    """健康检查接口:访问 /health 时返回服务是否正常。

    前端在启动时会调用它来判断后端是否可用。
    """
    return {
        "status": "healthy",
        "service": settings.app_name,
        "version": settings.app_version
    }


# 如果直接运行这个文件(而不是被 uvicorn 加载),就用 uvicorn 启动服务
if __name__ == "__main__":
    import uvicorn

    uvicorn.run(
        "app.api.main:app",
        host=settings.host,
        port=settings.port,
        reload=True
    )
