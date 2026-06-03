import asyncio
import httpx
from fastapi import APIRouter, Depends
from pydantic import BaseModel
from typing import Any

from db.config_dao import get_all_system_configs, update_system_config

router = APIRouter(prefix="/admin/config")

class ConfigUpdateRequest(BaseModel):
    key: str
    value: Any

@router.get("")
async def get_config():
    return await get_all_system_configs()

@router.post("")
async def update_config(req: ConfigUpdateRequest):
    await update_system_config(req.key, req.value)
    return {"status": "success"}

@router.get("/fetch-models")
async def fetch_remote_models():
    """探测已配置的大模型接口的可用模型列表"""
    from core.settings import settings
    
    api_key = settings.LLM_API_KEY.get_secret_value() if settings.LLM_API_KEY else ""
    base_url = settings.LLM_BASE_URL
    url = base_url.rstrip("/") + "/models"
    
    available_models = []
    
    try:
        async with httpx.AsyncClient(timeout=5.0) as client:
            resp = await client.get(url, headers={"Authorization": f"Bearer {api_key}"})
            resp.raise_for_status()
            data = resp.json()
            models = data.get("data", [])
            for m in models:
                model_id = m.get("id")
                if model_id:
                    available_models.append({
                        "id": model_id,
                        "name": model_id,
                        "provider": "default"
                    })
    except Exception as e:
        print(f"[探测失败] 无法获取模型列表: {e}")

    available_models.sort(key=lambda x: (x["provider"], x["name"]))
    return {"data": available_models}
