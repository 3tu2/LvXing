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

from fastapi import FastAPI                                     # 用来创建 Web 应用
from fastapi.middleware.cors import CORSMiddleware              # 处理跨域问题的中间件
from ..config import get_settings, validate_config, print_config  # 从上级目录导入配置相关函数
from ..services.amap_service import close_amap_tools            # 应用关闭时释放 MCP 资源
from .routes import trip, poi, map as map_routes                # 导入三组路由

# 获取配置(单例,全局只有一份)
settings = get_settings()

# 创建 FastAPI 应用实例
# 这些参数会显示在自动生成的接口文档(/docs)页面上
app = FastAPI(
    title=settings.app_name,          # 应用标题
    version=settings.app_version,     # 版本号
    description="基于LangChain + LangGraph框架的智能旅行规划助手API",  # 简介
    docs_url="/docs",                 # Swagger 文档地址
    redoc_url="/redoc"                # ReDoc 文档地址
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

# 注册路由:把三个路由模块挂载到 app 上
# prefix="/api" 表示这些接口的网址都会以 /api 开头(例如 /api/trip/plan)
app.include_router(trip.router, prefix="/api")
app.include_router(poi.router, prefix="/api")
app.include_router(map_routes.router, prefix="/api")


@app.on_event("startup")
async def startup_event():
    """应用启动事件。

    当后端服务启动完成时,会自动执行这个函数,用来打印欢迎信息、
    校验配置、显示接口文档地址等。
    """
    print("\n" + "="*60)
    print(f"🚀 {settings.app_name} v{settings.app_version}")
    print("="*60)

    # 打印配置信息
    print_config()

    # 验证配置(缺关键配置会抛出异常,阻止启动)
    try:
        validate_config()
        print("\n✅ 配置验证通过")
    except ValueError as e:
        print(f"\n❌ 配置验证失败:\n{e}")
        print("\n请检查.env文件并确保所有必要的配置项都已设置")
        raise  # 重新抛出异常,让启动失败,避免带病运行

    print("\n" + "="*60)
    print("📚 API文档: http://localhost:8000/docs")
    print("📖 ReDoc文档: http://localhost:8000/redoc")
    print("="*60 + "\n")


@app.on_event("shutdown")
async def shutdown_event():
    """应用关闭事件:当服务被停止时执行,释放 MCP 资源并打印关闭提示。"""
    await close_amap_tools()  # 释放高德 MCP 工具缓存
    print("\n" + "="*60)
    print("👋 应用正在关闭...")
    print("="*60 + "\n")


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
