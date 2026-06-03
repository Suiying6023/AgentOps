import pytest
from httpx import AsyncClient, ASGITransport

from main import app
from db.chat_history import chat_history_store
import sys
import asyncio
import os



if sys.platform == "win32":
    asyncio.set_event_loop_policy(asyncio.WindowsSelectorEventLoopPolicy())

@pytest.fixture
async def async_client():
    """创建一个异步测试客户端，直接连入 FastAPI App 核心，无需绑定端口启动！"""
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        yield client
        await asyncio.sleep(0.1) # 给予 ASGI background task 优雅关闭的时间


@pytest.fixture(autouse=True)
def clear_memory_before_test():
    """每次运行测试前，自动清空系统短期记忆，保证测试隔离性。"""
    import psycopg
    from core.settings import settings
    conn_str = settings.postgres_uri.replace("+psycopg", "")
    with psycopg.connect(conn_str) as conn:
        with conn.cursor() as cur:
            cur.execute("TRUNCATE TABLE messages CASCADE")
            cur.execute("TRUNCATE TABLE threads CASCADE")
        conn.commit()

from unittest.mock import patch
from tools.weather import get_weather
from core.settings import settings

@pytest.fixture(autouse=True)
def mock_mcp_tools():
    """Mock get_mcp_tools 以避免在测试期间启动子进程导致挂起，同时注入本地天气工具以支持工具测试。"""
    async def fake_get_mcp_tools():
        return [get_weather]
    with patch("core.mcp_client.get_mcp_tools", side_effect=fake_get_mcp_tools):
        yield

@pytest.fixture(autouse=True)
async def setup_checkpointer():
    """测试时自动初始化全局 Checkpointer，否则脱离 FastAPI 生命周期的测试会报错"""
    from db.chat_history import init_global_checkpointer, close_global_checkpointer
    await init_global_checkpointer()
    yield
    await close_global_checkpointer()
