import json
import asyncio
from core import settings
from typing import Annotated
from uuid import uuid4

from fastapi import APIRouter, Depends, FastAPI, HTTPException, status
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import StreamingResponse
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer

from agents import DEFAULT_AGENT, get_agent, get_all_agent_info
from memory import chat_history_store
from guardrails import judge_injection_async
from schema import (
    ChatHistory,
    ChatHistoryInput,
    ChatMessage,
    ClearHistoryResponse,
    ServiceMetadata,
    StreamInput,
    UserInput,
)


from contextlib import asynccontextmanager

@asynccontextmanager
async def lifespan(app: FastAPI):
    from core.config_manager import init_db, load_configs
    # 初始化配置表并加载
    init_db()
    load_configs()
    yield

app = FastAPI(title="My Agent Service", lifespan=lifespan)


# 允许跨域，方便 Next.js 前端调用
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # 生产环境请修改为具体的域名
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


def verify_bearer(
    http_auth: Annotated[
        HTTPAuthorizationCredentials | None,
        Depends(HTTPBearer(auto_error=False)),
    ],
) -> None:
    """最小 Bearer Token 鉴权。

    如果没有设置 AUTH_SECRET，则跳过鉴权。
    如果设置了 AUTH_SECRET，则请求必须携带：
    Authorization: Bearer <AUTH_SECRET>
    """
    if not settings.AUTH_SECRET:
        return

    auth_secret = settings.AUTH_SECRET.get_secret_value()

    if not http_auth or http_auth.credentials != auth_secret:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED)

protected_router = APIRouter(dependencies=[Depends(verify_bearer)])


@app.get("/health")
async def health_check() -> dict[str, str]:
    return {"status": "ok"}


@protected_router.get("/info")
async def info() -> ServiceMetadata:
    return ServiceMetadata(
        agents=get_all_agent_info(),
        default_agent=DEFAULT_AGENT,
    )


@protected_router.post("/invoke")
async def invoke_default_agent(user_input: UserInput) -> ChatMessage:
    return await invoke_agent(DEFAULT_AGENT, user_input)


@protected_router.post("/{agent_id}/invoke")
async def invoke_agent(agent_id: str, user_input: UserInput) -> ChatMessage:
    try:
        agent = get_agent(agent_id)
    except KeyError:
        raise HTTPException(status_code=404, detail=f"Agent not found: {agent_id}")

    thread_id = user_input.thread_id or str(uuid4())
    
    from core.lock import ThreadConcurrencyLock
    async with ThreadConcurrencyLock(thread_id):
        history = chat_history_store.get_messages(thread_id)

    human_message = ChatMessage(
        type="human",
        content=user_input.message,
        metadata={
            "agent_id": agent_id,
            "thread_id": thread_id,
            "user_id": user_input.user_id,
        },
    )

    reply_chunks = []
    async for chunk in agent.invoke(user_input, history):
        reply_chunks.append(chunk)
    reply_text = "".join(reply_chunks)

    ai_message = ChatMessage(
        type="ai",
        content=reply_text,
        run_id=str(uuid4()),
        metadata={
            "agent_id": agent_id,
            "thread_id": thread_id,
            "user_id": user_input.user_id,
        },
    )

    chat_history_store.append_messages(thread_id, [human_message, ai_message])

    return ai_message

@protected_router.post("/{agent_id}/stream")
async def stream_agent(agent_id: str, user_input: StreamInput):
    try:
        agent = get_agent(agent_id)
    except KeyError:
        raise HTTPException(status_code=404, detail=f"Agent not found: {agent_id}")

    thread_id = user_input.thread_id or str(uuid4())
    
    # 获取分布式锁，防止并发冲突
    from core.lock import ThreadConcurrencyLock
    lock = ThreadConcurrencyLock(thread_id)
    await lock.acquire()

    history = chat_history_store.get_messages(thread_id)

    human_message = ChatMessage(
        type="human",
        content=user_input.message,
        metadata={
            "agent_id": agent_id,
            "thread_id": thread_id,
            "user_id": user_input.user_id,
        },
    )
    # 流式返回前记录人类消息
    chat_history_store.append_messages(thread_id, [human_message])

    async def generate():
        try:
            reply_chunks = []
            run_id = str(uuid4())
            
            # 启动异步安全检测
            judge_task = asyncio.create_task(judge_injection_async(user_input.message))
            is_blocked = False
            
            # 流式输出
            async for chunk in agent.invoke(user_input, history):
                # 检查安全拦截结果
                if judge_task.done():
                    try:
                        is_malicious = judge_task.result()
                    except Exception:
                        is_malicious = False
                    
                    if is_malicious:
                        warning_msg = "\n\n🚨 **[安全拦截] 检测到恶意注入，连接已断开**"
                        if user_input.stream_tokens:
                            yield f"data: {json.dumps({'type': 'token', 'content': warning_msg}, ensure_ascii=False)}\n\n"
                        reply_chunks.append(warning_msg)
                        is_blocked = True
                        break  # 中断流

                reply_chunks.append(chunk)
                
                # 严格按照 SSE 规范往外吐数据
                if user_input.stream_tokens:
                    yield f"data: {json.dumps({'type': 'token', 'content': chunk}, ensure_ascii=False)}\n\n"
            
            # 结束生成
            reply_text = "".join(reply_chunks)
            ai_message = ChatMessage(
                type="ai",
                content=reply_text,
                run_id=run_id,
                metadata={
                    "agent_id": agent_id,
                    "thread_id": thread_id,
                    "user_id": user_input.user_id,
                },
            )
            chat_history_store.append_messages(thread_id, [ai_message])
            
            # 发送结束信号，通知前端断开连接
            yield f"data: {json.dumps({'type': 'done', 'content': ''})}\n\n"

        finally:
            # 释放锁
            await lock.release()

    # 使用 FastAPI 内置的 StreamingResponse 返回生成器
    return StreamingResponse(generate(), media_type="text/event-stream")


@protected_router.post("/history")
async def get_history(input_data: ChatHistoryInput) -> ChatHistory:
    messages = chat_history_store.get_messages(input_data.thread_id)
    return ChatHistory(messages=messages)


@protected_router.post("/history/clear")
async def clear_history(input_data: ChatHistoryInput) -> ClearHistoryResponse:
    chat_history_store.clear_thread(input_data.thread_id)
    return ClearHistoryResponse(thread_id=input_data.thread_id)

@protected_router.get("/threads")
async def get_threads() -> list[str]:
    return chat_history_store.get_all_threads()





# ==========================================
# Phase 13: 动态模型网关 Admin API 
# ==========================================
from pydantic import BaseModel

class ProviderConfigRequest(BaseModel):
    provider: str
    api_key: str
    model_type: str = ""
    base_url: str | None = None

@protected_router.get("/admin/providers")
async def get_providers():
    from core.config_manager import get_all_providers
    return get_all_providers()

@protected_router.post("/admin/providers")
async def update_provider(req: ProviderConfigRequest):
    from core.config_manager import upsert_provider
    upsert_provider(req.provider, req.api_key, req.model_type, req.base_url)
    return {"status": "success"}

@protected_router.delete("/admin/providers/{provider}")
async def remove_provider(provider: str):
    from core.config_manager import delete_provider
    delete_provider(provider)
    return {"status": "success"}

# ==========================================
# Phase 9 & 13: 文档知识库解析与切分 (Agentic RAG)
# ==========================================
from fastapi import UploadFile, File, BackgroundTasks
import shutil
import os

@protected_router.post("/knowledge/upload")
async def upload_knowledge(background_tasks: BackgroundTasks, file: UploadFile = File(...)):
    """RAG 向量库上传解析"""
    upload_dir = "data/uploads"
    os.makedirs(upload_dir, exist_ok=True)
    file_path = os.path.join(upload_dir, file.filename)
    
    with open(file_path, "wb") as buffer:
        shutil.copyfileobj(file.file, buffer)
        
    def process_rag_doc(path: str, filename: str):
        try:
            from tools.rag import ingest_document
            ingest_document(path)
            print(f"[后台任务] 文件 {filename} 解析并灌库成功！")
        except Exception as e:
            print(f"[后台任务] 文件 {filename} 灌库失败: {e}")
        finally:
            if os.path.exists(path): os.remove(path)

    # 提交到后台线程池处理，绝不阻塞主线程
    background_tasks.add_task(process_rag_doc, file_path, file.filename)
    return {"status": "success", "message": f"文件 {file.filename} 已进入后台队列，系统正在安静为您灌库，您可继续聊天！"}

@protected_router.post("/knowledge/upload_wiki")
async def upload_wiki(background_tasks: BackgroundTasks, file: UploadFile = File(...)):
    """Wiki 知识编译上传"""
    upload_dir = "data/uploads_wiki"
    os.makedirs(upload_dir, exist_ok=True)
    file_path = os.path.join(upload_dir, file.filename)
    
    with open(file_path, "wb") as buffer:
        shutil.copyfileobj(file.file, buffer)
        
    def process_wiki_doc(path: str, filename: str):
        try:
            from tools.wiki_compiler import compile_document_to_wiki
            compile_document_to_wiki(path)
            print(f"[后台任务] 文件 {filename} Wiki 编译成功！")
        except Exception as e:
            print(f"[后台任务] 文件 {filename} Wiki 编译失败: {e}")
        finally:
            if os.path.exists(path): os.remove(path)

    background_tasks.add_task(process_wiki_doc, file_path, file.filename)
    return {"status": "success", "message": f"文件 {file.filename} 已进入后台 Wiki 编译队列，大模型正在通读，您可继续聊天！"}

app.include_router(protected_router)