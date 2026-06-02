import asyncio
import httpx
from fastapi import APIRouter, Depends
from pydantic import BaseModel
from typing import Any

from core.auth import verify_bearer
from core.config_manager import get_all_system_configs, update_system_config

router = APIRouter(prefix="/admin/config", dependencies=[Depends(verify_bearer)])

class ConfigUpdateRequest(BaseModel):
    key: str
    value: Any

@router.get("")
async def get_config():
    return get_all_system_configs()

@router.post("")
async def update_config(req: ConfigUpdateRequest):
    update_system_config(req.key, req.value)
    return {"status": "success"}

@router.get("/fetch-models")
async def fetch_remote_models():
    """并发探测已配置环境变量的厂商的可用模型列表"""
    from core.settings import settings
    
    providers = []
    if settings.OPENAI_API_KEY:
        providers.append({"provider": "openai", "api_key": settings.OPENAI_API_KEY.get_secret_value(), "base_url": settings.OPENAI_BASE_URL})
    if settings.DEEPSEEK_API_KEY:
        providers.append({"provider": "deepseek", "api_key": settings.DEEPSEEK_API_KEY.get_secret_value(), "base_url": settings.DEEPSEEK_BASE_URL})
    if settings.SILICONFLOW_PRIMARY_KEY:
        providers.append({"provider": "siliconflow", "api_key": settings.SILICONFLOW_PRIMARY_KEY.get_secret_value(), "base_url": settings.SILICONFLOW_BASE_URL})

    available_models = []
    
    async def fetch_models(provider_cfg):
        provider_name = provider_cfg["provider"]
        api_key = provider_cfg["api_key"]
        base_url = provider_cfg["base_url"]
                
        url = base_url.rstrip("/") + "/models"
        
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
                            "id": f"{provider_name}/{model_id}",
                            "name": model_id,
                            "provider": provider_name
                        })
        except Exception as e:
            print(f"[探测失败] 无法获取 {provider_name} 的模型列表: {e}")

    await asyncio.gather(*(fetch_models(p) for p in providers))
    available_models.sort(key=lambda x: (x["provider"], x["name"]))
    return {"data": available_models}
