import asyncio
import logging
import sys

import uvicorn
from dotenv import load_dotenv

from core import settings


load_dotenv()


def configure_logging() -> None:
    logging.basicConfig(level=settings.LOG_LEVEL.to_logging_level())


def configure_windows_event_loop() -> None:
    """Windows 下设置兼容事件循环策略。

    现在我们还没有接 PostgreSQL、异步数据库驱动或复杂网络库，
    但提前放在启动入口里，后面扩展时不需要再改结构。
    """
    if sys.platform == "win32":
        asyncio.set_event_loop_policy(asyncio.WindowsSelectorEventLoopPolicy())


def main() -> None:
    configure_logging()
    configure_windows_event_loop()

    uvicorn.run(
        "service:app",
        host=settings.HOST,
        port=settings.PORT,
        reload=settings.is_dev(),
    )


if __name__ == "__main__":
    main()