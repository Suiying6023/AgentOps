from functools import cache
from typing import cast
from langchain_community.chat_models import FakeListChatModel
from langchain_core.language_models.chat_models import BaseChatModel
from langchain_core.embeddings import Embeddings
from langchain_core.outputs import ChatResult
from langchain_openai import ChatOpenAI, OpenAIEmbeddings
import asyncio

from core.settings import settings
from schema import DeepseekModelName, FakeModelName, ModelName, OpenAIModelName, SiliconFlowModelName

class ToolAwareFakeModel(FakeListChatModel):
    def bind_tools(self, tools, **kwargs):
        return self

class SiliconFlowChatOpenAI(ChatOpenAI):
    """
    专门为 SiliconFlow 等不支持 n > 1 的模型提供并发/串行降级支持的工业级补丁类。
    核心能力：自动拦截 n>1 的请求，拆解为 n 个独立请求并并发执行，最后伪装合并 Token 计算。
    """
    async def _agenerate(self, messages, stop=None, run_manager=None, **kwargs) -> ChatResult:
        # Ragas 的巨坑：它不会把 n 传在 kwargs 里，而是直接强行修改 self.n 属性！
        target_n = kwargs.get("n", getattr(self, "n", 1))
        
        if target_n is not None and target_n > 1:
            kwargs["n"] = 1
            old_n = getattr(self, "n", 1)
            if hasattr(self, "n"):
                self.n = 1  # 临时屏蔽 self.n，防止 super()._agenerate 继续读取到 3
                
            try:
                # 核心机制：利用 asyncio.gather 并发发送 n 个独立请求
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
def get_model(model_name: ModelName | None = None) -> BaseChatModel:
    """根据传入的模型名称动态实例化并返回对应的 LangChain ChatModel。
    （已恢复 @cache，并使用 LangChain 原生 with_fallbacks 机制实现主备 Key 切换）
    """
    # 如果没有指定模型，则使用 settings 中的默认模型
    target_model = model_name or settings.DEFAULT_MODEL

    # 1. 处理模拟模型 (用于无网本地快速测试)
    if target_model == FakeModelName.FAKE:
        return ToolAwareFakeModel(responses=["这是一条来自 FakeModel 的模拟测试回复。"])

    # 2. 处理 OpenAI 模型
    if target_model in list(OpenAIModelName):
        return ChatOpenAI(
            model=target_model,
            api_key=cast(str, settings.OPENAI_API_KEY.get_secret_value() if settings.OPENAI_API_KEY else ""),
            temperature=0.5,
        )

    # 3. 处理 DeepSeek 模型 (兼容 OpenAI 接口格式)
    if target_model in list(DeepseekModelName):
        return ChatOpenAI(
            model=target_model,
            api_key=cast(str, settings.DEEPSEEK_API_KEY.get_secret_value() if settings.DEEPSEEK_API_KEY else ""),
            base_url="https://api.deepseek.com/v1",
            temperature=0.5,
        )

    # 4. 处理硅基流动 (SiliconFlow) 模型，加入主备 fallback 机制
    if target_model in list(SiliconFlowModelName):
        primary_model = SiliconFlowChatOpenAI(
            model=target_model,
            api_key=cast(str, settings.SILICONFLOW_PRIMARY_KEY.get_secret_value() if settings.SILICONFLOW_PRIMARY_KEY else ""),
            base_url="https://api.siliconflow.cn/v1",
            temperature=0.6,
        )
        
        if settings.SILICONFLOW_FALLBACK_KEY:
            fallback_model = SiliconFlowChatOpenAI(
                model=target_model,
                api_key=cast(str, settings.SILICONFLOW_FALLBACK_KEY.get_secret_value() if settings.SILICONFLOW_FALLBACK_KEY else ""),
                base_url="https://api.siliconflow.cn/v1",
                temperature=0.6,
            )
            # 使用 LangChain 的原生 fallbacks 机制：主模型报错时，自动降级到备用模型
            return primary_model.with_fallbacks([fallback_model])
            
        return primary_model

    # 兜底报错机制（理论上在 schema 层就会被拦截，但工厂内部保留防御性编程）
    raise ValueError(f"不受支持的模型名称: {target_model}")


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
        print(f"🔧 初始化本地 Embedding 模型 (BAAI/bge-m3) - Device: {device}")
        
        return HuggingFaceEmbeddings(
            model_name="BAAI/bge-m3",
            model_kwargs={'device': device},
            encode_kwargs={'normalize_embeddings': True}
        )
    else:
        # 使用在线大厂模型 (Qwen)
        from langchain_openai import OpenAIEmbeddings
        from typing import cast
        
        api_key = cast(str, settings.GEMAI_API_KEY.get_secret_value() if settings.GEMAI_API_KEY else "sk-NoCIP2lKzL1SxctciLVOF6W0Jsp5qs1UxZ09Wvi8kPQY73rK")
        print("🔧 初始化在线 Embedding 模型 (qwen3-embedding-8b)")
        
        return OpenAIEmbeddings(
            model="qwen3-embedding-8b",
            api_key=api_key,
            base_url=settings.GEMAI_BASE_URL,
            dimensions=1536,
            chunk_size=10,  # 严格限制单次请求的文本数 (Batch Size)，避免 Payload 过大被 WAF 阻断
            max_retries=3,  # 遇到 429/502 等问题时，利用 Langchain 原生机制进行指数退避重试
        )
