from collections.abc import AsyncGenerator
from typing import Annotated, TypedDict

from langchain_core.messages import BaseMessage, HumanMessage
from langchain_core.tools import tool
from langgraph.graph import END, START, StateGraph
from langgraph.graph.message import add_messages
from langgraph.prebuilt import ToolNode, tools_condition

import sqlite3
from langgraph.checkpoint.sqlite.aio import AsyncSqliteSaver

from agents.base import BaseAgent
from core.llm import get_model
from schema import ChatMessage, UserInput
from tools.rag import search_knowledge_base
from tools.weather import get_weather

# 将工具放入列表
tools = [get_weather, search_knowledge_base]


# 2. 定义图的“状态” (State)
# State 是图流转过程中的“全局白板”。所有节点都会读取并修改这个白板。
class AgentState(TypedDict):
    # Annotated 与 add_messages：表示这不只是一个简单的列表替换，而是遇到新消息时“追加”进去
    messages: Annotated[list[BaseMessage], add_messages]
    # 我们把用户选择的模型名也放进状态里，供后续的 Node 读取
    model_name: str


class GraphAgent(BaseAgent):
    """基于 LangGraph 编排的智能体 (Phase 4 引入 ReAct 工具调用核心)。"""

    def __init__(self):
        super().__init__()

    def _build_graph(self, memory_saver):
        # 实例化图画板，并绑定我们定义好的 State
        workflow = StateGraph(AgentState)

        # 4. 初始化工具节点
        # ToolNode 是 LangGraph 预置的节点，专门用来执行模型请求调用的工具
        tool_node = ToolNode(tools)

        # 5. 定义图中的“模型节点” (Node)
        async def call_model(state: AgentState):
            """大模型推理节点"""
            # 从状态里读取需要用的参数
            messages = state["messages"]
            model_name = state.get("model_name")
            
            # 向模型工厂申请带有容灾兜底的大模型实例，并“绑定”工具
            # bind_tools 会告诉模型：你可以使用这些工具，模型判断需要时会返回包含 tool_calls 的特殊消息
            model = get_model(model_name).bind_tools(tools)
            
            # 触发模型思考 (注意：在 LangGraph 中，我们写 ainvoke，但外层仍然可以截获流式！)
            response = await model.ainvoke(messages)
            
            # 返回的结果会被 LangGraph 根据我们在 AgentState 中定义的规则更新到全局状态中
            return {"messages": [response]}

        # 6. 把节点添加到画板上
        workflow.add_node("call_model", call_model)
        workflow.add_node("tools", tool_node)  # 添加工具执行节点

        # 7. 画“边线” (Edge)，定义流程怎么走 (ReAct 循环)
        workflow.add_edge(START, "call_model")
        
        # 条件边：模型节点结束后，判断是否需要调用工具
        workflow.add_conditional_edges(
            "call_model",
            tools_condition,  # 预置条件判断：如果有 tool_calls 则流向 "tools" 节点，否则流向 END
        )
        
        # 闭环：从工具节点回到模型节点，让模型根据工具执行的观察结果继续思考
        workflow.add_edge("tools", "call_model")

        # 8. 编译出炉 (挂载 Checkpointer 还原历史状态)
        return workflow.compile(checkpointer=memory_saver)

    async def invoke(
        self, user_input: UserInput, history: list[ChatMessage] = None
    ) -> AsyncGenerator[str, None]:
        """执行图流转，并接管底层的流式输出事件。"""

        # 构建图流转的初始数据
        inputs = {
            "messages": [HumanMessage(content=user_input.message)],
            "model_name": user_input.model,
        }
        
        # Phase 7: Langfuse 监控接入与 Thread ID 注入
        from core.settings import settings
        
        callbacks = []
        if settings.LANGFUSE_ENABLED:
            from langfuse.langchain import CallbackHandler
            langfuse_handler = CallbackHandler()
            callbacks.append(langfuse_handler)
        
        tags = [t for t in ["AgentOps", user_input.model] if t]
        
        config = {
            "configurable": {"thread_id": user_input.thread_id or "default_thread"},
            "callbacks": callbacks,
            "tags": tags,
            "metadata": {
                "langfuse_session_id": user_input.thread_id or "default_thread",
                "langfuse_user_id": user_input.user_id or "anonymous"
            }
        }


        import os
        os.makedirs("data", exist_ok=True)

        # 动态编译，完美解决 async sqlite 数据库生命周期管理和 get_running_loop 运行时错误
        async with AsyncSqliteSaver.from_conn_string("data/checkpoints.db") as memory_saver:
            graph = self._build_graph(memory_saver)
            
            # 见证奇迹的时刻：astream_events 可以深入到图的毛细血管里
            # 把图内部大模型的“逐字流事件”给直接截获出来！
            async for event in graph.astream_events(inputs, config=config, version="v2"):
                kind = event["event"]
                if kind == "on_chat_model_stream":
                    # 提取大模型刚刚吐出的碎片文字
                    chunk_content = event["data"]["chunk"].content
                    if chunk_content:
                        yield str(chunk_content)
                elif kind == "on_tool_start":
                    # 截获工具开始调用事件
                    tool_name = event["name"]
                    tool_input = event["data"].get("input", {})
                    yield f"\n\n> ⚙️ **[系统日志] 正在调用工具**: `{tool_name}`\n> **参数**: `{tool_input}`\n\n"
                elif kind == "on_tool_end":
                    # 截获工具结束事件
                    yield f"> ✅ **[系统日志] 工具执行完毕**\n\n"
