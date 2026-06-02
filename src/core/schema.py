from typing import Any, Literal
from pydantic import BaseModel, Field
from enum import StrEnum
from typing import TypeAlias

class Provider(StrEnum):
    OPENAI = "openai"
    DEEPSEEK = "deepseek"
    SILICONFLOW = "siliconflow"
    FAKE = "fake"

class AgentInfo(BaseModel):
    """一个可用 Agent 的基本信息。"""

    key: str = Field(
        description="Agent 的唯一标识，例如 chatbot、research-assistant。",
        examples=["chatbot"],
    )
    description: str = Field(
        description="Agent 的能力描述。",
        examples=["A simple chatbot."],
    )


class ServiceMetadata(BaseModel):
    """服务元信息，用于 /info 接口。"""

    agents: list[AgentInfo] = Field(
        description="当前服务可用的 Agent 列表。",
    )
    default_agent: str = Field(
        description="默认 Agent。",
        examples=["chatbot"],
    )


class UserInput(BaseModel):
    """普通非流式请求。"""

    message: str = Field(
        description="用户输入。",
        examples=["你好，请介绍一下你自己。"],
    )
    model: str | None = Field(
        default=None,
        description="本次请求使用的大模型名称（例如 'openai/gpt-4o'）。如果为空，则使用系统默认模型。",
    )
    thread_id: str | None = Field(
        default=None,
        description="会话 ID。相同 thread_id 用于继续同一轮多轮对话。",
    )
    user_id: str | None = Field(
        default=None,
        description="用户 ID。相同 user_id 可用于跨会话长期记忆。",
    )
    agent_config: dict[str, Any] = Field(
        default_factory=dict,
        description="传给 Agent 的额外配置。",
        examples=[{"temperature": 0.3}],
    )


class StreamInput(UserInput):
    """流式请求。"""

    stream_tokens: bool = Field(
        default=True,
        description="是否逐 token 返回模型输出。",
    )


class ChatMessage(BaseModel):
    """服务统一返回的聊天消息格式。"""

    type: Literal["human", "ai", "tool", "custom"] = Field(
        description="消息类型。",
        examples=["ai"],
    )
    content: str = Field(
        description="消息正文。",
        examples=["你好，我是一个 Agent。"],
    )
    run_id: str | None = Field(
        default=None,
        description="本次运行 ID，后续可用于反馈、追踪和观测。",
    )
    metadata: dict[str, Any] = Field(
        default_factory=dict,
        description="额外元信息。",
    )


class ChatHistoryInput(BaseModel):
    """查询历史消息的请求。"""

    thread_id: str = Field(
        description="要查询的会话 ID。",
    )


class ChatHistory(BaseModel):
    """历史消息返回。"""

    messages: list[ChatMessage]

class ClearHistoryResponse(BaseModel):
    """清空历史后的响应。"""

    status: Literal["success"] = "success"
    thread_id: str