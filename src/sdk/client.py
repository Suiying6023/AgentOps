import json
import os
from typing import Any, AsyncGenerator, Generator

import httpx

import sys
sys.path.append(os.path.join(os.path.dirname(__file__), '../src'))

from schemas.api_models import (
    ChatHistory,
    ChatHistoryInput,
    ChatMessage,
    ClearHistoryResponse,
    ServiceMetadata,
    UserInput,
)


class AgentClientError(Exception):
    """AgentClient 调用服务失败时抛出的异常。"""


class AgentClient:
    """调用 Agent Service 的最小 Python 客户端。"""

    def __init__(
        self,
        base_url: str = "http://localhost:8080",
        timeout: float = 30.0,
    ) -> None:
        self.base_url = base_url.rstrip("/")
        self.timeout = timeout

    def get_info(self) -> ServiceMetadata:
        try:
            response = httpx.get(
                f"{self.base_url}/info",
                timeout=self.timeout,
            )
            response.raise_for_status()
        except httpx.HTTPError as exc:
            raise AgentClientError(f"获取服务信息失败：{exc}") from exc

        return ServiceMetadata.model_validate(response.json())

    def invoke(
        self,
        message: str,
        agent_id: str = "chatbot",
        thread_id: str | None = None,
        user_id: str | None = None,
        agent_config: dict[str, Any] | None = None,
    ) -> ChatMessage:
        request = UserInput(
            message=message,
            thread_id=thread_id,
            user_id=user_id,
            agent_config=agent_config or {},
        )

        try:
            response = httpx.post(
                f"{self.base_url}/{agent_id}/invoke",
                json=request.model_dump(),
                timeout=self.timeout,
            )
            response.raise_for_status()
        except httpx.HTTPError as exc:
            raise AgentClientError(f"调用 Agent 失败：{exc}") from exc

        return ChatMessage.model_validate(response.json())

    def stream(
        self,
        message: str,
        agent_id: str = "chatbot",
        thread_id: str | None = None,
        user_id: str | None = None,
        agent_config: dict[str, Any] | None = None,
    ) -> Generator[str, None, None]:
        """流式调用 Agent，返回一个生成器，逐字 yield 字符串"""
        request = {
            "message": message,
            "stream_tokens": True,
            "thread_id": thread_id,
            "user_id": user_id,
            "agent_config": agent_config or {},
        }
        
        try:
            with httpx.stream(
                "POST",
                f"{self.base_url}/{agent_id}/stream",
                json=request,
                timeout=self.timeout,
            ) as response:
                response.raise_for_status()
                for line in response.iter_lines():
                    if line.startswith("data: "):
                        data_str = line[6:]
                        try:
                            data_json = json.loads(data_str)
                            if data_json.get("type") == "token":
                                yield data_json.get("content", "")
                            elif data_json.get("type") == "done":
                                break
                        except json.JSONDecodeError:
                            continue
        except httpx.HTTPError as exc:
            raise AgentClientError(f"流式调用 Agent 失败：{exc}") from exc

    def get_history(self, thread_id: str) -> ChatHistory:
        request = ChatHistoryInput(thread_id=thread_id)

        try:
            response = httpx.post(
                f"{self.base_url}/history",
                json=request.model_dump(),
                timeout=self.timeout,
            )
            response.raise_for_status()
        except httpx.HTTPError as exc:
            raise AgentClientError(f"获取历史记录失败：{exc}") from exc

        return ChatHistory.model_validate(response.json())

    def clear_history(self, thread_id: str) -> ClearHistoryResponse:
        request = ChatHistoryInput(thread_id=thread_id)

        try:
            response = httpx.post(
                f"{self.base_url}/history/clear",
                json=request.model_dump(),
                timeout=self.timeout,
            )
            response.raise_for_status()
        except httpx.HTTPError as exc:
            raise AgentClientError(f"清空历史记录失败：{exc}") from exc

        return ClearHistoryResponse.model_validate(response.json())


class AsyncAgentClient:
    """调用 Agent Service 的异步 Python 客户端。"""

    def __init__(
        self,
        base_url: str = "http://localhost:8080",
        timeout: float = 30.0,
    ) -> None:
        self.base_url = base_url.rstrip("/")
        self.timeout = timeout

    async def aget_info(self) -> ServiceMetadata:
        try:
            async with httpx.AsyncClient(timeout=self.timeout) as client:
                response = await client.get(
                    f"{self.base_url}/info",
                    )
            response.raise_for_status()
        except httpx.HTTPError as exc:
            raise AgentClientError(f"获取服务信息（异步）失败：{exc}") from exc

        return ServiceMetadata.model_validate(response.json())

    async def ainvoke(
        self,
        message: str,
        agent_id: str = "chatbot",
        thread_id: str | None = None,
        user_id: str | None = None,
        agent_config: dict[str, Any] | None = None,
    ) -> ChatMessage:
        request = UserInput(
            message=message,
            thread_id=thread_id,
            user_id=user_id,
            agent_config=agent_config or {},
        )

        try:
            async with httpx.AsyncClient(timeout=self.timeout) as client:
                response = await client.post(
                    f"{self.base_url}/{agent_id}/invoke",
                    json=request.model_dump(),
                    )
            response.raise_for_status()
        except httpx.HTTPError as exc:
            raise AgentClientError(f"调用 Agent（异步）失败：{exc}") from exc

        return ChatMessage.model_validate(response.json())

    async def astream(
        self,
        message: str,
        agent_id: str = "chatbot",
        thread_id: str | None = None,
        user_id: str | None = None,
        agent_config: dict[str, Any] | None = None,
    ) -> AsyncGenerator[str, None]:
        """流式调用 Agent（异步），返回一个异步生成器，逐字 yield 字符串"""
        request = {
            "message": message,
            "stream_tokens": True,
            "thread_id": thread_id,
            "user_id": user_id,
            "agent_config": agent_config or {},
        }
        
        try:
            async with httpx.AsyncClient(timeout=self.timeout) as client:
                async with client.stream(
                    "POST",
                    f"{self.base_url}/{agent_id}/stream",
                    json=request,
                    ) as response:
                    response.raise_for_status()
                    async for line in response.aiter_lines():
                        if line.startswith("data: "):
                            data_str = line[6:]
                            try:
                                data_json = json.loads(data_str)
                                if data_json.get("type") == "token":
                                    yield data_json.get("content", "")
                                elif data_json.get("type") == "done":
                                    break
                            except json.JSONDecodeError:
                                continue
        except httpx.HTTPError as exc:
            raise AgentClientError(f"流式调用 Agent（异步）失败：{exc}") from exc

    async def aget_history(self, thread_id: str) -> ChatHistory:
        request = ChatHistoryInput(thread_id=thread_id)

        try:
            async with httpx.AsyncClient(timeout=self.timeout) as client:
                response = await client.post(
                    f"{self.base_url}/history",
                    json=request.model_dump(),
                    )
            response.raise_for_status()
        except httpx.HTTPError as exc:
            raise AgentClientError(f"获取历史记录（异步）失败：{exc}") from exc

        return ChatHistory.model_validate(response.json())

    async def aclear_history(self, thread_id: str) -> ClearHistoryResponse:
        request = ChatHistoryInput(thread_id=thread_id)

        try:
            async with httpx.AsyncClient(timeout=self.timeout) as client:
                response = await client.post(
                    f"{self.base_url}/history/clear",
                    json=request.model_dump(),
                    )
            response.raise_for_status()
        except httpx.HTTPError as exc:
            raise AgentClientError(f"清空历史记录（异步）失败：{exc}") from exc

        return ClearHistoryResponse.model_validate(response.json())