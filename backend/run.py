"""启动脚本。

这是后端项目的"一键启动入口"。你可以直接运行:
    python run.py
来启动后端服务,等价于在命令行执行:
    uvicorn app.api.main:app --reload

小白可以这样理解:这个文件就是"按开关"的入口,真正启动的服务器由 uvicorn 负责。
"""

import uvicorn                      # 一个高性能的 ASGI 服务器,用来运行 FastAPI 应用
from app.config import get_settings  # 导入我们自己的配置读取函数

# 只有当"直接运行本文件"时,下面的代码才会执行
# (如果是被别的文件 import 进来,__name__ 就不是 "__main__",这部分会被跳过)
if __name__ == "__main__":
    settings = get_settings()  # 读取配置(端口、日志级别等)

    # 启动服务器
    uvicorn.run(
        "app.api.main:app",                      # 要启动的应用:app/api/main.py 里的 app 对象
        host=settings.host,                      # 监听地址
        port=settings.port,                      # 监听端口
        reload=True,                             # 代码改动后自动重启(方便开发调试)
        log_level=settings.log_level.lower()     # 日志级别
    )
