import json
import logging
import psycopg
from psycopg.rows import dict_row
import asyncio
from core.settings import settings

logger = logging.getLogger(__name__)

SYSTEM_CONFIG_CACHE = {}
_cache_lock = asyncio.Lock()

async def init_db():
    """初始化系统配置表"""
    conn_str = settings.postgres_uri.replace("+psycopg", "")
    try:
        async with await psycopg.AsyncConnection.connect(conn_str) as conn:
            async with conn.cursor() as cur:
                await cur.execute("""
                    CREATE TABLE IF NOT EXISTS system_configs (
                        key VARCHAR(50) PRIMARY KEY,
                        value TEXT NOT NULL
                    )
                """)
                
                # 初始化默认的显示模型列表
                await cur.execute("SELECT COUNT(*) FROM system_configs WHERE key = 'display_models'")
                if (await cur.fetchone())[0] == 0:
                    default_models = []
                    await cur.execute("INSERT INTO system_configs (key, value) VALUES (%s, %s)", 
                               ("display_models", json.dumps(default_models, ensure_ascii=False)))
                
                # 初始化默认的裁判模型
                await cur.execute("SELECT COUNT(*) FROM system_configs WHERE key = 'review_model'")
                if (await cur.fetchone())[0] == 0:
                    await cur.execute("INSERT INTO system_configs (key, value) VALUES (%s, %s)", 
                               ("review_model", ""))

                # 初始化子智能体低中高配置
                sub_defaults = {
                    "subagent_model_low": "deepseek-ai/DeepSeek-V3.2",
                    "subagent_model_medium": "deepseek-ai/DeepSeek-V3.2",
                    "subagent_model_high": "deepseek-ai/DeepSeek-V3.2",
                    "review_mode": "sequential"
                }
                for skey, sval in sub_defaults.items():
                    await cur.execute("SELECT COUNT(*) FROM system_configs WHERE key = %s", (skey,))
                    if (await cur.fetchone())[0] == 0:
                        await cur.execute("INSERT INTO system_configs (key, value) VALUES (%s, %s)", (skey, sval))
                               
            await conn.commit()
    except Exception as e:
        logger.error(f"Failed to init system_configs table: {e}")

async def load_configs():
    """从数据库加载最新配置到内存"""
    global SYSTEM_CONFIG_CACHE
    conn_str = settings.postgres_uri.replace("+psycopg", "")
    try:
        async with await psycopg.AsyncConnection.connect(conn_str, row_factory=dict_row) as conn:
            async with conn.cursor() as cur:
                await cur.execute("SELECT * FROM system_configs")
                rows = await cur.fetchall()
                
                new_cache = {}
                for row in rows:
                    if row["key"] == "display_models":
                        try:
                            new_cache[row["key"]] = json.loads(row["value"])
                        except json.JSONDecodeError:
                            new_cache[row["key"]] = []
                    else:
                        new_cache[row["key"]] = row["value"]
                
                async with _cache_lock:
                    SYSTEM_CONFIG_CACHE = new_cache
                
        logger.info(f"Loaded system configs from PostgreSQL.")
    except Exception as e:
        logger.error(f"Failed to load system configs: {e}")

async def get_system_config(key: str, default=None):
    async with _cache_lock:
        is_empty = not SYSTEM_CONFIG_CACHE
    if is_empty:
        await load_configs()
    return SYSTEM_CONFIG_CACHE.get(key, default)

async def get_all_system_configs():
    async with _cache_lock:
        is_empty = not SYSTEM_CONFIG_CACHE
    if is_empty:
        await load_configs()
    return dict(SYSTEM_CONFIG_CACHE)

async def update_system_config(key: str, value: any):
    conn_str = settings.postgres_uri.replace("+psycopg", "")
    
    if isinstance(value, list) or isinstance(value, dict):
        value_str = json.dumps(value, ensure_ascii=False)
    else:
        value_str = str(value)
        
    async with await psycopg.AsyncConnection.connect(conn_str) as conn:
        async with conn.cursor() as cur:
            await cur.execute("""
                INSERT INTO system_configs (key, value)
                VALUES (%s, %s)
                ON CONFLICT (key) DO UPDATE 
                SET value = EXCLUDED.value
            """, (key, value_str))
        await conn.commit()
    await load_configs()
