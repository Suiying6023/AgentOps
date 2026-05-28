from abc import ABC, abstractmethod
from collections.abc import AsyncGenerator
from schema import ChatMessage, UserInput

class BaseAgent(ABC):
    """所有 Agent 的基础接口。"""

    @abstractmethod
    async def invoke(
        self,
        user_input: UserInput,
        history: list[ChatMessage] = None,
    ) -> AsyncGenerator[str, None]:
        """执行 Agent，并以流式（Streaming）形式不断产出文本。"""
        yield ""  # 使用 yield 替代 raise NotImplementedError 以满足生成器语法
