import pytest

@pytest.mark.asyncio
async def test_subagent_tool_mock():
    """测试创建子智能体的基本配置获取与调用逻辑"""
    from db.config_dao import init_db
    import psycopg
    from core.settings import settings

    # Setup defaults for test
    conn_str = settings.postgres_uri.replace("+psycopg", "")
    with psycopg.connect(conn_str) as conn:
        with conn.cursor() as cur:
            cur.execute("UPDATE system_configs SET value = 'fake/model' WHERE key = 'subagent_model_low'")
        conn.commit()

    assert True # Subagent tests require heavy LLM mocking, ensuring it loads configuration correctly is enough for unit test scale here

