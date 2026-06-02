import json
import psycopg
from psycopg.rows import dict_row
from core.schema import ChatMessage
from core.settings import settings

class PostgresChatHistory:
    """基于 PostgreSQL 的持久化会话历史存储 (替代原先的 SQLite)。"""

    def __init__(self) -> None:
        self.conn_str = settings.postgres_uri.replace("+psycopg", "")
        self._init_db()

    def _init_db(self):
        try:
            with psycopg.connect(self.conn_str) as conn:
                with conn.cursor() as cur:
                    # 创建会话元数据表
                    cur.execute("""
                        CREATE TABLE IF NOT EXISTS threads (
                            id TEXT PRIMARY KEY,
                            name TEXT NOT NULL
                        )
                    """)
                    # 创建消息存储表
                    cur.execute("""
                        CREATE TABLE IF NOT EXISTS messages (
                            id SERIAL PRIMARY KEY,
                            thread_id TEXT NOT NULL,
                            type TEXT NOT NULL,
                            content TEXT NOT NULL,
                            run_id TEXT,
                            metadata TEXT,
                            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                        )
                    """)
                    cur.execute("CREATE INDEX IF NOT EXISTS idx_messages_thread_id ON messages(thread_id)")
                conn.commit()
        except Exception as e:
            print(f"Failed to init PostgresChatHistory: {e}")

    def get_messages(self, thread_id: str) -> list[ChatMessage]:
        with psycopg.connect(self.conn_str) as conn:
            with conn.cursor() as cur:
                cur.execute(
                    "SELECT type, content, run_id, metadata FROM messages WHERE thread_id = %s ORDER BY id ASC",
                    (thread_id,)
                )
                rows = cur.fetchall()
        
        messages = []
        for row in rows:
            msg_type, content, run_id, metadata_str = row
            metadata = json.loads(metadata_str) if metadata_str else {}
            messages.append(ChatMessage(
                type=msg_type,
                content=content,
                run_id=run_id,
                metadata=metadata
            ))
        return messages

    def append_message(self, thread_id: str, message: ChatMessage) -> None:
        self.append_messages(thread_id, [message])

    def append_messages(self, thread_id: str, messages: list[ChatMessage]) -> None:
        with psycopg.connect(self.conn_str) as conn:
            with conn.cursor() as cur:
                for message in messages:
                    metadata_str = json.dumps(message.metadata, ensure_ascii=False) if message.metadata else None
                    cur.execute(
                        "INSERT INTO messages (thread_id, type, content, run_id, metadata) VALUES (%s, %s, %s, %s, %s)",
                        (thread_id, message.type, message.content, message.run_id, metadata_str)
                    )
            conn.commit()

    def get_all_threads(self) -> list[dict]:
        with psycopg.connect(self.conn_str, row_factory=dict_row) as conn:
            with conn.cursor() as cur:
                cur.execute("""
                    SELECT m.thread_id AS id, COALESCE(t.name, m.thread_id) AS name 
                    FROM messages m 
                    LEFT JOIN threads t ON m.thread_id = t.id 
                    GROUP BY m.thread_id, t.name 
                    ORDER BY MAX(m.created_at) DESC
                """)
                return cur.fetchall()

    def rename_thread(self, thread_id: str, name: str) -> None:
        with psycopg.connect(self.conn_str) as conn:
            with conn.cursor() as cur:
                cur.execute(
                    "INSERT INTO threads (id, name) VALUES (%s, %s) ON CONFLICT (id) DO UPDATE SET name = EXCLUDED.name",
                    (thread_id, name)
                )
            conn.commit()

    def delete_thread(self, thread_id: str) -> None:
        with psycopg.connect(self.conn_str) as conn:
            with conn.cursor() as cur:
                cur.execute("DELETE FROM messages WHERE thread_id = %s", (thread_id,))
                cur.execute("DELETE FROM threads WHERE id = %s", (thread_id,))
            conn.commit()

    def clear_thread(self, thread_id: str) -> None:
        with psycopg.connect(self.conn_str) as conn:
            with conn.cursor() as cur:
                cur.execute("DELETE FROM messages WHERE thread_id = %s", (thread_id,))
            conn.commit()

# 暴露单例
chat_history_store = PostgresChatHistory()

from langgraph.checkpoint.postgres.aio import AsyncPostgresSaver
from core.settings import settings

global_checkpointer: AsyncPostgresSaver | None = None
_checkpointer_cm = None

async def init_global_checkpointer():
    """初始化全局 LangGraph PostgreSQL Checkpointer。供 FastAPI lifespan 使用。"""
    global global_checkpointer, _checkpointer_cm
    postgres_uri = settings.postgres_uri.replace("+psycopg", "")
    _checkpointer_cm = AsyncPostgresSaver.from_conn_string(postgres_uri)
    global_checkpointer = await _checkpointer_cm.__aenter__()
    await global_checkpointer.setup()

async def close_global_checkpointer():
    """关闭全局 LangGraph PostgreSQL Checkpointer"""
    global global_checkpointer, _checkpointer_cm
    if _checkpointer_cm:
        await _checkpointer_cm.__aexit__(None, None, None)
    global_checkpointer = None
    _checkpointer_cm = None