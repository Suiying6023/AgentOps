import json
import asyncio
import httpx
from uuid import uuid4
from fastapi import APIRouter, Depends, HTTPException
from fastapi.responses import StreamingResponse

from db.chat_history import chat_history_store
from core.guardrails import judge_injection_async
from schemas.api_models import ChatMessage, StreamInput, UserInput
from agents.graph_agent import GraphAgent

router = APIRouter(prefix="/chat")

# 单例化全局 GraphAgent (不再需要 factory / registry 模式)
agent = GraphAgent()

@router.post("/invoke")
async def invoke_agent(user_input: UserInput) -> ChatMessage:
    thread_id = user_input.thread_id or str(uuid4())
    
    from core.lock import ThreadConcurrencyLock
    async with ThreadConcurrencyLock(thread_id):
        history = await chat_history_store.get_messages(thread_id)

    human_message = ChatMessage(
        type="human",
        content=user_input.message,
        metadata={
            "thread_id": thread_id,
            "user_id": user_input.user_id,
        },
    )

    reply_chunks = []
    try:
        async for chunk in agent.invoke(user_input, history):
            reply_chunks.append(chunk)
    except Exception as e:
        error_msg = str(e)
        if "insufficient" in error_msg.lower() or "balance" in error_msg.lower():
            reply_chunks.append("\n\n⚠️ **[API 错误]** 该大模型提供商账号余额不足，请在提供商控制台充值或在右下角切换到其他可用模型节点。")
        else:
            reply_chunks.append(f"\n\n⚠️ **[系统异常]** 调用模型服务失败: {error_msg}")
    reply_text = "".join(reply_chunks)

    ai_message = ChatMessage(
        type="ai",
        content=reply_text,
        run_id=str(uuid4()),
        metadata={
            "thread_id": thread_id,
            "user_id": user_input.user_id,
        },
    )

    await chat_history_store.append_messages(thread_id, [human_message, ai_message])
    return ai_message

@router.post("/stream")
async def stream_agent(user_input: StreamInput):
    thread_id = user_input.thread_id or str(uuid4())
    
    from core.lock import ThreadConcurrencyLock
    lock = ThreadConcurrencyLock(thread_id)
    await lock.acquire()

    history = await chat_history_store.get_messages(thread_id)

    human_message = ChatMessage(
        type="human",
        content=user_input.message,
        metadata={
            "thread_id": thread_id,
            "user_id": user_input.user_id,
        },
    )
    await chat_history_store.append_messages(thread_id, [human_message])

    async def generate():
        try:
            reply_chunks = []
            run_id = str(uuid4())
            
            from db.config_dao import get_system_config
            review_mode = await get_system_config("review_mode", "sequential")
            
            is_malicious = False
            judge_task = None
            is_blocked = False
            
            if review_mode == "sequential":
                try:
                    is_malicious = await judge_injection_async(user_input.message)
                except Exception:
                    is_malicious = False
            elif review_mode == "parallel":
                judge_task = asyncio.create_task(judge_injection_async(user_input.message))

            if is_malicious:
                warning_msg = "\n\n🚨 **[安全拦截] 检测到恶意注入，连接已断开**"
                if user_input.stream_tokens:
                    yield f"data: {json.dumps({'type': 'token', 'content': warning_msg}, ensure_ascii=False)}\n\n"
                reply_chunks.append(warning_msg)
                
                # 保存拦截信息并直接返回
                reply_text = "".join(reply_chunks)
                ai_message = ChatMessage(
                    type="ai",
                    content=reply_text,
                    run_id=run_id,
                    metadata={"thread_id": thread_id, "user_id": user_input.user_id},
                )
                await chat_history_store.append_messages(thread_id, [ai_message])
                yield f"data: {json.dumps({'type': 'done', 'content': ''})}\n\n"
                return

            try:
                async for chunk in agent.invoke(user_input, history):
                    if review_mode == "parallel" and judge_task and judge_task.done() and not is_blocked:
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
                            break

                    reply_chunks.append(chunk)
                    if user_input.stream_tokens:
                        yield f"data: {json.dumps({'type': 'token', 'content': chunk}, ensure_ascii=False)}\n\n"
            except Exception as e:
                error_msg = str(e)
                if "insufficient" in error_msg.lower() or "balance" in error_msg.lower():
                    friendly_error = "\n\n⚠️ **[API 错误]** 该大模型提供商账号余额不足，请在提供商控制台充值或在右下角切换到其他可用模型节点。"
                elif "403" in error_msg or "Permission" in error_msg:
                    friendly_error = "\n\n⚠️ **[API 错误]** 无权限访问该模型，可能是余额不足或 API Key 权限不够。"
                else:
                    friendly_error = f"\n\n⚠️ **[系统异常]** 调用模型服务失败: {error_msg}"
                
                if user_input.stream_tokens:
                    yield f"data: {json.dumps({'type': 'token', 'content': friendly_error}, ensure_ascii=False)}\n\n"
                reply_chunks.append(friendly_error)
            
            reply_text = "".join(reply_chunks)
            ai_message = ChatMessage(
                type="ai",
                content=reply_text,
                run_id=run_id,
                metadata={
                    "thread_id": thread_id,
                    "user_id": user_input.user_id,
                },
            )
            await chat_history_store.append_messages(thread_id, [ai_message])
            yield f"data: {json.dumps({'type': 'done', 'content': ''})}\n\n"

        finally:
            await lock.release()

    return StreamingResponse(generate(), media_type="text/event-stream")

@router.get("/models")
async def get_available_models():
    """探测可用模型。如果没有配置显示列表，则返回所有探测到的模型，防止无模型可用。"""
    from core.settings import settings
    from db.config_dao import get_system_config
    
    display_models = await get_system_config("display_models", [])
    display_set = set(display_models) if display_models else None
    
    api_key = settings.LLM_API_KEY.get_secret_value() if settings.LLM_API_KEY else ""
    base_url = settings.LLM_BASE_URL
    url = base_url.rstrip("/") + "/models"
    
    available_models = []
    
    try:
        async with httpx.AsyncClient(timeout=3.0) as client:
            resp = await client.get(url, headers={"Authorization": f"Bearer {api_key}"})
            resp.raise_for_status()
            data = resp.json()
            models = data.get("data", [])
            for m in models:
                model_id = m.get("id")
                if model_id:
                    # 严格遵守白名单：只有开启的模型才能显示。如果没开启任何模型，全量返回。
                    if display_set and model_id not in display_set:
                        continue
                    available_models.append({
                        "id": model_id,
                        "name": model_id,
                        "provider": "default"
                    })
    except Exception as e:
        print(f"[Chat 探测失败] 无法获取模型列表: {e}")
    
    fetched_ids = {m["id"] for m in available_models}
    
    # 兜底：如果设置了显示模型，但因为网络原因没探测到，强行加上
    if display_models:
        for model_id in display_models:
            if model_id not in fetched_ids:
                available_models.append({
                    "id": model_id,
                    "name": model_id,
                    "provider": "default"
                })
    
    available_models.sort(key=lambda x: (x["provider"], x["name"]))
    return {"data": available_models}
