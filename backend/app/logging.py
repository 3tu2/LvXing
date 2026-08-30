"""日志配置模块(loguru)。

统一全项目的日志输出:控制台 + 文件,带分级与自动轮转。
用法:在任意模块 `from app.logging import logger` 后,用
`logger.info(...)` / `logger.warning(...)` / `logger.error(...)` 代替 print。
"""

import sys
from pathlib import Path

from loguru import logger

# 移除默认 handler,按需重新配置
logger.remove()

# 控制台输出(stderr,带颜色;level 由配置决定)
logger.add(
    sys.stderr,
    level="INFO",
    format="<green>{time:YYYY-MM-DD HH:mm:ss}</green> | <level>{level: <7}</level> | "
           "<cyan>{name}</cyan>:<cyan>{line}</cyan> - <level>{message}</level>",
)

# 文件日志(按天轮转,保留 14 天)
_log_dir = Path(__file__).resolve().parent.parent / "data" / "logs"
_log_dir.mkdir(parents=True, exist_ok=True)
logger.add(
    _log_dir / "app.log",
    level="INFO",
    rotation="1 day",
    retention="14 days",
    encoding="utf-8",
    format="{time:YYYY-MM-DD HH:mm:ss} | {level: <7} | {name}:{line} - {message}",
)

__all__ = ["logger"]
