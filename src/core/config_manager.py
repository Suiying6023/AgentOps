import json
import logging
import psycopg
from psycopg.rows import dict_row
from core.settings import settings

logger = logging.getLogger(__name__)

SYSTEM_CONFIG_CACHE = {}

def init_db():
    """初始化系统配置表"""
    conn_str = settings.postgres_uri.replace("+psycopg", "")
    try:
        with psycopg.connect(conn_str) as conn:
            with conn.cursor() as cur:
                cur.execute("""
                    CREATE TABLE IF NOT EXISTS system_configs (
                        key VARCHAR(50) PRIMARY KEY,
                        value TEXT NOT NULL
                    )
                """)
                
                # 初始化默认的显示模型列表
                cur.execute("SELECT COUNT(*) FROM system_configs WHERE key = 'display_models'")
                if cur.fetchone()[0] == 0:
                    default_models = [
                        "siliconflow/deepseek-ai/DeepSeek-V3",
                        "siliconflow/deepseek-ai/DeepSeek-R1",
                        "siliconflow/Qwen/Qwen2.5-7B-Instruct"
                    ]
                    cur.execute("INSERT INTO system_configs (key, value) VALUES (%s, %s)", 
                               ("display_models", json.dumps(default_models, ensure_ascii=False)))
                
                # 初始化默认的裁判模型
                cur.execute("SELECT COUNT(*) FROM system_configs WHERE key = 'review_model'")
                if cur.fetchone()[0] == 0:
                    cur.execute("INSERT INTO system_configs (key, value) VALUES (%s, %s)", 
                               ("review_model", "siliconflow/Qwen/Qwen2.5-7B-Instruct"))

                # 初始化子智能体低中高配置
                sub_defaults = {
                    "subagent_model_low": "siliconflow/Qwen/Qwen2.5-7B-Instruct",
                    "subagent_model_medium": "siliconflow/deepseek-ai/DeepSeek-V3",
                    "subagent_model_high": "siliconflow/deepseek-ai/DeepSeek-R1",
                    "review_mode": "sequential"
                }
                for skey, sval in sub_defaults.items():
                    cur.execute("SELECT COUNT(*) FROM system_configs WHERE key = %s", (skey,))
                    if cur.fetchone()[0] == 0:
                        cur.execute("INSERT INTO system_configs (key, value) VALUES (%s, %s)", (skey, sval))
                               
            conn.commit()
    except Exception as e:
        logger.error(f"Failed to init system_configs table: {e}")

def load_configs():
    """从数据库加载最新配置到内存"""
    global SYSTEM_CONFIG_CACHE
    conn_str = settings.postgres_uri.replace("+psycopg", "")
    try:
        with psycopg.connect(conn_str, row_factory=dict_row) as conn:
            with conn.cursor() as cur:
                cur.execute("SELECT * FROM system_configs")
                rows = cur.fetchall()
                
                new_cache = {}
                for row in rows:
                    if row["key"] == "display_models":
                        try:
                            new_cache[row["key"]] = json.loads(row["value"])
                        except json.JSONDecodeError:
                            new_cache[row["key"]] = []
                    else:
                        new_cache[row["key"]] = row["value"]
                
                SYSTEM_CONFIG_CACHE.clear()
                SYSTEM_CONFIG_CACHE.update(new_cache)
                
        logger.info(f"Loaded system configs from PostgreSQL.")
    except Exception as e:
        logger.error(f"Failed to load system configs: {e}")

def get_system_config(key: str, default=None):
    if not SYSTEM_CONFIG_CACHE:
        load_configs()
    return SYSTEM_CONFIG_CACHE.get(key, default)

def get_all_system_configs():
    if not SYSTEM_CONFIG_CACHE:
        load_configs()
    return dict(SYSTEM_CONFIG_CACHE)

def update_system_config(key: str, value: any):
    conn_str = settings.postgres_uri.replace("+psycopg", "")
    
    # 格式化存储
    if isinstance(value, list) or isinstance(value, dict):
        value_str = json.dumps(value, ensure_ascii=False)
    else:
        value_str = str(value)
        
    with psycopg.connect(conn_str) as conn:
        with conn.cursor() as cur:
            cur.execute("""
                INSERT INTO system_configs (key, value)
                VALUES (%s, %s)
                ON CONFLICT (key) DO UPDATE 
                SET value = EXCLUDED.value
            """, (key, value_str))
        conn.commit()
    load_configs()
