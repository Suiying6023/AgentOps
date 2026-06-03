from functools import cache
from typing import cast
from langchain_core.language_models import FakeListChatModel
from langchain_core.language_models.chat_models import BaseChatModel
from langchain_core.embeddings import Embeddings
from langchain_core.outputs import ChatResult
from langchain_openai import ChatOpenAI, OpenAIEmbeddings
import asyncio
import sys
import httpx

from core.settings import settings

class ToolAwareFakeModel(FakeListChatModel):
    def bind_tools(self, tools, **kwargs):
        return self

class UnifiedChatOpenAI(ChatOpenAI):
    """
    为不支持 n > 1 的模型提供并发降级支持。
    自动拦截 n>1 的请求，拆解为 n 个独立请求并并发执行，最后合并结果。
    """
    async def _agenerate(self, messages, stop=None, run_manager=None, **kwargs) -> ChatResult:
        # 适配 Ragas 框架：拦截外部修改的 self.n 属性
        target_n = kwargs.get("n", getattr(self, "n", 1))
        
        if target_n is not None and target_n > 1:
            kwargs["n"] = 1
            old_n = getattr(self, "n", 1)
            if hasattr(self, "n"):
                self.n = 1  # 临时屏蔽 self.n，防止 super()._agenerate 继续读取到 3
                
            try:
                # 利用 asyncio.gather 并发发送 n 个独立请求
                tasks = [super()._agenerate(messages, stop, run_manager, **kwargs) for _ in range(target_n)]
                results = await asyncio.gather(*tasks)
            finally:
                # 恢复原状
                if hasattr(self, "n"):
                    self.n = old_n
            
            combined_generations = []
            total_tokens = {"prompt_tokens": 0, "completion_tokens": 0, "total_tokens": 0}
            
            for res in results:
                combined_generations.extend(res.generations)
                if res.llm_output and "token_usage" in res.llm_output:
                    usage = res.llm_output["token_usage"]
                    total_tokens["prompt_tokens"] += usage.get("prompt_tokens", 0)
                    total_tokens["completion_tokens"] += usage.get("completion_tokens", 0)
                    total_tokens["total_tokens"] += usage.get("total_tokens", 0)
                    
            # 伪造合并后的 llm_output，保留账单追踪的精准度
            merged_llm_output = results[0].llm_output.copy() if results[0].llm_output else {}
            merged_llm_output["token_usage"] = total_tokens
            
            return ChatResult(generations=combined_generations, llm_output=merged_llm_output)
            
        return await super()._agenerate(messages, stop, run_manager, **kwargs)

    def _generate(self, messages, stop=None, run_manager=None, **kwargs) -> ChatResult:
        target_n = kwargs.get("n", getattr(self, "n", 1))
        
        if target_n is not None and target_n > 1:
            kwargs["n"] = 1
            old_n = getattr(self, "n", 1)
            if hasattr(self, "n"):
                self.n = 1
                
            try:
                results = [super()._generate(messages, stop, run_manager, **kwargs) for _ in range(target_n)]
            finally:
                if hasattr(self, "n"):
                    self.n = old_n
            
            combined_generations = []
            total_tokens = {"prompt_tokens": 0, "completion_tokens": 0, "total_tokens": 0}
            
            for res in results:
                combined_generations.extend(res.generations)
                if res.llm_output and "token_usage" in res.llm_output:
                    usage = res.llm_output["token_usage"]
                    total_tokens["prompt_tokens"] += usage.get("prompt_tokens", 0)
                    total_tokens["completion_tokens"] += usage.get("completion_tokens", 0)
                    total_tokens["total_tokens"] += usage.get("total_tokens", 0)
                    
            merged_llm_output = results[0].llm_output.copy() if results[0].llm_output else {}
            merged_llm_output["token_usage"] = total_tokens
            
            return ChatResult(generations=combined_generations, llm_output=merged_llm_output)
            
        return super()._generate(messages, stop, run_manager, **kwargs)

@cache
def get_model(model_name: str | None = None) -> BaseChatModel:
    """根据传入的模型名称动态实例化并返回对应的 LangChain ChatModel。"""
    # 如果没有指定模型，则使用 settings 中的默认模型
    target_model = model_name or settings.DEFAULT_MODEL
    
    api_key = settings.LLM_API_KEY.get_secret_value() if settings.LLM_API_KEY else ""
    base_url = settings.LLM_BASE_URL

    return UnifiedChatOpenAI(
        model=target_model,
        api_key=cast(str, api_key) if api_key else "empty",
        base_url=base_url,
        temperature=0.6,
    )


@cache
def get_embeddings() -> Embeddings:
    """获取文本嵌入模型 (支持本地 BGE-M3 与在线 Qwen 动态切换)"""
    from core.settings import settings
    
    if settings.USE_LOCAL_EMBEDDING:
        # 使用本地私有化部署 BGE-M3 模型 (支持 CUDA)
        import os
        import torch
        from langchain_huggingface import HuggingFaceEmbeddings
        
        os.environ["HF_ENDPOINT"] = "https://hf-mirror.com"
        device = "cuda" if torch.cuda.is_available() else "cpu"
        print(f"🔧 初始化本地 Embedding 模型 (BAAI/bge-m3) - Device: {device}", file=sys.stderr)
        
        return HuggingFaceEmbeddings(
            model_name="BAAI/bge-m3",
            model_kwargs={'device': device},
            encode_kwargs={'normalize_embeddings': True}
        )
    else:
        # 使用在线大厂模型 (Qwen)
        from langchain_openai import OpenAIEmbeddings
        from typing import cast
        
        api_key = cast(str, settings.EMBEDDING_API_KEY.get_secret_value() if settings.EMBEDDING_API_KEY else "")
        print(f"🔧 初始化在线 Embedding 模型 ({settings.EMBEDDING_MODEL})", file=sys.stderr)
        
        return OpenAIEmbeddings(
            model=settings.EMBEDDING_MODEL,
            api_key=api_key,
            base_url=settings.EMBEDDING_BASE_URL,
            dimensions=1536,
            chunk_size=10,  # 严格限制单次请求的文本数 (Batch Size)，避免 Payload 过大被 WAF 阻断
            max_retries=3,  # 遇到 429/502 等问题时，利用 Langchain 原生机制进行指数退避重试
        )

_fallback_cache = None

async def get_fallback_model_id() -> str:
    global _fallback_cache
    if _fallback_cache:
        return _fallback_cache
    
    from core.settings import settings
    api_key = settings.LLM_API_KEY.get_secret_value() if settings.LLM_API_KEY else ""
    base_url = settings.LLM_BASE_URL
    url = base_url.rstrip("/") + "/models"
    
    try:
        import httpx
        async with httpx.AsyncClient(timeout=3.0) as client:
            resp = await client.get(url, headers={"Authorization": f"Bearer {api_key}"})
            resp.raise_for_status()
            models = [m["id"] for m in resp.json().get("data", [])]
            if models:
                if settings.DEFAULT_MODEL in models:
                    _fallback_cache = settings.DEFAULT_MODEL
                else:
                    _fallback_cache = models[0]
                return _fallback_cache
    except Exception:
        pass
    _fallback_cache = settings.DEFAULT_MODEL or "Qwen/Qwen2.5-7B-Instruct"
    return _fallback_cache

