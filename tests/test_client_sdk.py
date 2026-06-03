import pytest
import asyncio
from sdk.client import AgentClient, AsyncAgentClient

@pytest.mark.skip(reason="Requires a live local server running on port 8080")
def test_sync_client() -> None:
    print("=== 开始测试同步客户端 AgentClient ===")
    client = AgentClient(base_url="http://localhost:8080")

    info = client.get_info()
    assert len(info.agents) > 0

    thread_id = "thread-client-sync-001"
    user_id = "user-client-001"

    response_1 = client.invoke(
        agent_id="graph_agent",
        message="你好，我正在用 同步 Python client 测试",
        thread_id=thread_id,
        user_id=user_id,
    )
    assert response_1.content

    history = client.get_history(thread_id)
    assert len(history.messages) > 0

    clear_result = client.clear_history(thread_id)
    assert clear_result.status == "success"

@pytest.mark.asyncio
@pytest.mark.skip(reason="Requires a live local server running on port 8080")
async def test_async_client() -> None:
    print("=== 开始测试异步客户端 AsyncAgentClient ===")
    client = AsyncAgentClient(base_url="http://localhost:8080")

    info = await client.aget_info()
    assert len(info.agents) > 0

    thread_id = "thread-client-async-001"
    user_id = "user-client-001"

    response_1 = await client.ainvoke(
        agent_id="graph_agent",
        message="你好，我正在用 异步 Python client 测试",
        thread_id=thread_id,
        user_id=user_id,
    )
    assert response_1.content

    history = await client.aget_history(thread_id)
    assert len(history.messages) > 0

    clear_result = await client.aclear_history(thread_id)
    assert clear_result.status == "success"
