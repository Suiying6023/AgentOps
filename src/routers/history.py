from fastapi import APIRouter, Depends
from pydantic import BaseModel
from core.auth import verify_bearer
from core.memory import chat_history_store
from core.schema import ChatHistory, ChatHistoryInput, ClearHistoryResponse

router = APIRouter(prefix="/history", dependencies=[Depends(verify_bearer)])

class RenameThreadInput(BaseModel):
    name: str

@router.post("")
async def get_history(input_data: ChatHistoryInput) -> ChatHistory:
    messages = chat_history_store.get_messages(input_data.thread_id)
    return ChatHistory(messages=messages)

@router.post("/clear")
async def clear_history(input_data: ChatHistoryInput) -> ClearHistoryResponse:
    chat_history_store.clear_thread(input_data.thread_id)
    return ClearHistoryResponse(thread_id=input_data.thread_id)

@router.get("/threads")
async def get_threads() -> list[dict]:
    return chat_history_store.get_all_threads()

@router.put("/{thread_id}/rename")
async def rename_thread(thread_id: str, payload: RenameThreadInput):
    chat_history_store.rename_thread(thread_id, payload.name)
    return {"status": "success", "thread_id": thread_id, "name": payload.name}

@router.delete("/{thread_id}")
async def delete_thread(thread_id: str):
    chat_history_store.delete_thread(thread_id)
    return {"status": "success", "thread_id": thread_id}
