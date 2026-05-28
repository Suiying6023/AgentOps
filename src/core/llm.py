from functools import cache
from typing import cast
from langchain_community.chat_models import FakeListChatModel
from langchain_core.language_models.chat_models import BaseChatModel
from langchain_core.embeddings import Embeddings
from langchain_openai import ChatOpenAI, OpenAIEmbeddings

from core.settings import settings
from schema import DeepseekModelName, FakeModelName, ModelName, OpenAIModelName, SiliconFlowModelName

class ToolAwareFakeModel(FakeListChatModel):
    def bind_tools(self, tools, **kwargs):
        return self

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
        primary_model = ChatOpenAI(
            model=target_model,
            api_key=cast(str, settings.SILICONFLOW_PRIMARY_KEY.get_secret_value() if settings.SILICONFLOW_PRIMARY_KEY else ""),
            base_url="https://api.siliconflow.cn/v1",
            temperature=0.6,
        )
        
        if settings.SILICONFLOW_FALLBACK_KEY:
            fallback_model = ChatOpenAI(
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
    """获取文本嵌入模型 (默认使用 SiliconFlow 的 BGE-M3 模型)"""
    return OpenAIEmbeddings(
        model="BAAI/bge-m3",
        api_key=cast(str, settings.SILICONFLOW_PRIMARY_KEY.get_secret_value() if settings.SILICONFLOW_PRIMARY_KEY else ""),
        base_url="https://api.siliconflow.cn/v1",
    )
