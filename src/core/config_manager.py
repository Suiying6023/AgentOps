import logging
import psycopg
from psycopg.rows import dict_row
from core.settings import settings

logger = logging.getLogger(__name__)

# 内存缓存，降低 get_model() 耗时并简化同步调用
PROVIDER_CACHE = {}

def init_db():
    """初始化数据库表"""
    conn_str = settings.postgres_uri.replace("+psycopg", "")
    try:
        with psycopg.connect(conn_str) as conn:
            with conn.cursor() as cur:
                cur.execute("""
                    CREATE TABLE IF NOT EXISTS provider_configs (
                        provider VARCHAR(50) PRIMARY KEY,
                        api_key TEXT NOT NULL,
                        base_url TEXT,
                        model_type TEXT,
                        status VARCHAR(20) DEFAULT 'connected',
                        latency INTEGER DEFAULT 0,
                        updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                    )
                """)
            conn.commit()
    except Exception as e:
        logger.error(f"Failed to init provider_configs table: {e}")

def load_configs():
    """从数据库加载最新配置到内存"""
    global PROVIDER_CACHE
    conn_str = settings.postgres_uri.replace("+psycopg", "")
    try:
        with psycopg.connect(conn_str, row_factory=dict_row) as conn:
            with conn.cursor() as cur:
                cur.execute("SELECT * FROM provider_configs")
                rows = cur.fetchall()
                
                # 刷新整个字典
                new_cache = {}
                for row in rows:
                    new_cache[row["provider"]] = row
                PROVIDER_CACHE.clear()
                PROVIDER_CACHE.update(new_cache)
                
        logger.info(f"Loaded {len(PROVIDER_CACHE)} provider configs from PostgreSQL.")
    except Exception as e:
        logger.error(f"Failed to load provider configs: {e}")

def get_provider_key(provider: str) -> str | None:
    """获取厂商 API Key，优先读库，读不到返回 None (触发 fallback 到 .env)"""
    config = PROVIDER_CACHE.get(provider)
    if config:
        return config["api_key"]
    return None

def upsert_provider(provider: str, api_key: str, model_type: str = "", base_url: str | None = None):
    """Admin 控制台保存/更新 Key 的接口"""
    conn_str = settings.postgres_uri.replace("+psycopg", "")
    with psycopg.connect(conn_str) as conn:
        with conn.cursor() as cur:
            cur.execute("""
                INSERT INTO provider_configs (provider, api_key, model_type, base_url, updated_at)
                VALUES (%s, %s, %s, %s, CURRENT_TIMESTAMP)
                ON CONFLICT (provider) DO UPDATE 
                SET api_key = EXCLUDED.api_key,
                    model_type = EXCLUDED.model_type,
                    base_url = EXCLUDED.base_url,
                    status = 'connected',
                    updated_at = CURRENT_TIMESTAMP
            """, (provider, api_key, model_type, base_url))
        conn.commit()
    # 写完库马上热更新缓存
    load_configs()

def delete_provider(provider: str):
    conn_str = settings.postgres_uri.replace("+psycopg", "")
    with psycopg.connect(conn_str) as conn:
        with conn.cursor() as cur:
            cur.execute("DELETE FROM provider_configs WHERE provider = %s", (provider,))
        conn.commit()
    load_configs()

def get_all_providers() -> list[dict]:
    return list(PROVIDER_CACHE.values())
