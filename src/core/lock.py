import redis.asyncio as redis
from core.settings import settings
from fastapi import HTTPException
import logging

logger = logging.getLogger(__name__)

# 全局 Redis 客户端
_redis_client = None

def get_redis() -> redis.Redis:
    global _redis_client
    if _redis_client is None:
        _redis_client = redis.from_url(settings.redis_uri, decode_responses=True)
    return _redis_client

class ThreadConcurrencyLock:
    """基于 Redis 的多用户会话并发锁。
    防止同一用户 (thread_id) 的重复点击或同时发送多个请求导致的 LangGraph 状态污染。
    """
    
    def __init__(self, thread_id: str, timeout: int = 120):
        self.thread_id = thread_id
        self.lock_key = f"agentops:lock:thread:{thread_id}"
        self.timeout = timeout
        self.redis = get_redis()
        self.acquired = False

    async def acquire(self):
        """显式获取锁，如果已被占用则直接抛出 409 异常。"""
        self.acquired = await self.redis.set(self.lock_key, "locked", nx=True, ex=self.timeout)
        if not self.acquired:
            raise HTTPException(
                status_code=409, 
                detail="当前会话正在处理上一个问题，请稍候再试。"
            )

    async def release(self):
        """释放锁。"""
        if self.acquired:
            await self.redis.delete(self.lock_key)
            self.acquired = False

    async def __aenter__(self):
        await self.acquire()
        return self

    async def __aexit__(self, exc_type, exc_val, exc_tb):
        await self.release()
