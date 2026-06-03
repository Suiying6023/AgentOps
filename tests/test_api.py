import pytest
import json

@pytest.mark.asyncio
async def test_invoke_endpoint(async_client):
    """测试传统的非流式请求兜底机制"""
    payload = {
        "message": "你好，请回复'Hello World'",
        "thread_id": "test_invoke_123"
    }
    response = await async_client.post("/chat/invoke", json=payload)
    
    assert response.status_code == 200, "接口应该成功返回"
    
    data = response.json()
    assert "content" in data
    assert len(data["content"]) > 0, "大模型回复不应该为空"
    print(f"\n[Invoke 测试通过] 收到回复: {data['content']}")

@pytest.mark.asyncio
async def test_stream_endpoint(async_client):
    """测试全新的流式接口"""
    payload = {
        "message": "请数数字，从 1 数到 3",
        "stream_tokens": True,
        "thread_id": "test_stream_123"
    }
    
    # 模拟客户端请求流式数据
    chunks_received = 0
    async with async_client.stream("POST", "/chat/stream", json=payload) as response:
        assert response.status_code == 200
        
        async for line in response.aiter_lines():
            if line.startswith("data: "):
                data_str = line[6:]
                data = json.loads(data_str)
                
                if data["type"] == "token":
                    chunks_received += 1
                elif data["type"] == "done":
                    pass

    assert chunks_received > 0, "必须接收到不止一个文字碎片，否则流式失效！"
    print(f"\n[Stream 测试通过] 成功接收到 {chunks_received} 个字符碎片。")
    
    import asyncio
    await asyncio.sleep(0.2)

@pytest.mark.asyncio
async def test_weather_tool_stream(async_client):
    """测试带有 ReAct 工具调用 (天气查询) 的图流转"""
    payload = {
        "message": "北京今天天气怎么样？",
        "thread_id": "test_weather_123"
    }
    
    print("\n\n[开始测试 ReAct 工具调用] 提问：北京今天天气怎么样？")
    print("-" * 50)
    
    chunks_received = 0
    async with async_client.stream("POST", "/chat/stream", json=payload) as response:
        assert response.status_code == 200, f"状态码异常: {response.status_code}"
        
        async for line in response.aiter_lines():
            if line.startswith("data: "):
                data_str = line[6:]
                data = json.loads(data_str)
                
                if data["type"] == "token":
                    print(data["content"], end="", flush=True)
                    chunks_received += 1
                elif data["type"] == "done":
                    print("\n" + "-" * 50)
                    print("[流式传输结束]")

    assert chunks_received > 0, "必须接收到文字碎片，否则模型未能正确反馈工具结果！"
    
    import asyncio
    await asyncio.sleep(0.2) # 给予 FastAPI 和相关依赖 (Redis, PG) 充足的时间进行资源清理和连接释放


@pytest.mark.asyncio
async def test_thread_management(async_client):
    """测试会话管理：获取、重命名、删除"""
    # 1. 发起一个对话以产生新 thread
    thread_id = "test_manage_123"
    await async_client.post("/chat/invoke", json={
        "message": "hi",
        "thread_id": thread_id
    })

    # 2. 获取列表，断言格式为 [{id: "...", name: "..."}]
    res = await async_client.get("/history/threads")
    assert res.status_code == 200
    threads = res.json()
    assert isinstance(threads, list)
    assert any(t["id"] == thread_id for t in threads)
    target_thread = next(t for t in threads if t["id"] == thread_id)
    assert "name" in target_thread

    # 3. 重命名
    new_name = "测试重命名"
    res_rename = await async_client.put(f"/history/{thread_id}/rename", json={"name": new_name})
    assert res_rename.status_code == 200
    assert res_rename.json()["status"] == "success"

    res_after_rename = await async_client.get("/history/threads")
    renamed_thread = next(t for t in res_after_rename.json() if t["id"] == thread_id)
    assert renamed_thread["name"] == new_name

    # 4. 删除
    res_delete = await async_client.delete(f"/history/{thread_id}")
    assert res_delete.status_code == 200
    res_after_delete = await async_client.get("/history/threads")
    assert not any(t["id"] == thread_id for t in res_after_delete.json())

@pytest.mark.asyncio
async def test_review_mode(async_client):
    """测试不同审查模式的切换逻辑"""
    from db.config_dao import init_db
    import psycopg
    from core.settings import settings
    
    # 模拟切换为 off 模式
    conn_str = settings.postgres_uri.replace("+psycopg", "")
    with psycopg.connect(conn_str) as conn:
        with conn.cursor() as cur:
            cur.execute("UPDATE system_configs SET value = 'off' WHERE key = 'review_mode'")
        conn.commit()
    
    # 发起请求
    payload = {
        "message": "这是一条无害测试消息",
        "stream_tokens": True,
        "thread_id": "test_review_off"
    }
    
    chunks = []
    async with async_client.stream("POST", "/chat/stream", json=payload) as response:
        assert response.status_code == 200
        async for line in response.aiter_lines():
            if line.startswith("data: "):
                data = json.loads(line[6:])
                chunks.append(data)
                
    assert len(chunks) > 0
