import sqlite3
import json
from pathlib import Path
from schema import ChatMessage

DB_PATH = Path("data/chat_history.db")
DB_PATH.parent.mkdir(parents=True, exist_ok=True)

class SqliteChatHistory:
    """基于 SQLite 的持久化会话历史存储 (Phase 7)。"""

    def __init__(self) -> None:
        # check_same_thread=False 允许在 FastAPI 的多个协程中共享连接
        self.conn = sqlite3.connect(DB_PATH, check_same_thread=False)
        self._init_db()

    def _init_db(self):
        with self.conn:
            self.conn.execute("""
                CREATE TABLE IF NOT EXISTS messages (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    thread_id TEXT NOT NULL,
                    type TEXT NOT NULL,
                    content TEXT NOT NULL,
                    run_id TEXT,
                    metadata TEXT,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                )
            """)
            self.conn.execute("CREATE INDEX IF NOT EXISTS idx_thread_id ON messages(thread_id)")

    def get_messages(self, thread_id: str) -> list[ChatMessage]:
        cursor = self.conn.cursor()
        cursor.execute(
            "SELECT type, content, run_id, metadata FROM messages WHERE thread_id = ? ORDER BY id ASC",
            (thread_id,)
        )
        rows = cursor.fetchall()
        
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
        with self.conn:
            for message in messages:
                metadata_str = json.dumps(message.metadata) if message.metadata else None
                self.conn.execute(
                    "INSERT INTO messages (thread_id, type, content, run_id, metadata) VALUES (?, ?, ?, ?, ?)",
                    (thread_id, message.type, message.content, message.run_id, metadata_str)
                )

    def get_all_threads(self) -> list[str]:
        cursor = self.conn.cursor()
        cursor.execute(
            "SELECT thread_id FROM messages GROUP BY thread_id ORDER BY MAX(created_at) DESC"
        )
        rows = cursor.fetchall()
        return [row[0] for row in rows]

    def clear_thread(self, thread_id: str) -> None:
        with self.conn:
            self.conn.execute("DELETE FROM messages WHERE thread_id = ?", (thread_id,))
    def get_all_threads(self) -> list[str]:
        cursor = self.conn.cursor()
        # 使用 GROUP BY 去重，并按照最大（最新）的 created_at 时间倒序排序
        cursor.execute(
            "SELECT thread_id FROM messages GROUP BY thread_id ORDER BY MAX(created_at) DESC"
        )
        rows = cursor.fetchall()
        return [row[0] for row in rows]

# 暴露单例
chat_history_store = SqliteChatHistory()