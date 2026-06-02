import sys
import asyncio

if sys.platform == "win32":
    asyncio.set_event_loop_policy(asyncio.WindowsSelectorEventLoopPolicy())

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from contextlib import asynccontextmanager

from core.schema import ServiceMetadata
from routers.admin import router as admin_router
from routers.knowledge import router as knowledge_router
from routers.history import router as history_router
from routers.chat import router as chat_router

@asynccontextmanager
async def lifespan(app: FastAPI):
    from core.config_manager import init_db, load_configs
    # 初始化配置表并加载
    init_db()
    load_configs()
    
    # 初始化全局 LangGraph Checkpointer
    from core.memory import init_global_checkpointer, close_global_checkpointer
    await init_global_checkpointer()
    
    yield
    
    # 清理
    await close_global_checkpointer()

app = FastAPI(title="My Agent Service", lifespan=lifespan)

# 允许跨域
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

@app.get("/health")
async def health_check() -> dict[str, str]:
    return {"status": "ok"}

@app.get("/info")
async def info() -> ServiceMetadata:
    return ServiceMetadata(
        agents=[{"key": "graph_agent", "description": "核心图智能体"}],
        default_agent="graph_agent",
    )

# 挂载独立路由
app.include_router(chat_router)
app.include_router(admin_router)
app.include_router(knowledge_router)
app.include_router(history_router)