from collections.abc import AsyncGenerator
from typing import Annotated, TypedDict

from langchain_core.messages import BaseMessage, HumanMessage
from langchain_core.tools import tool
from langgraph.graph import END, START, StateGraph
from langgraph.graph.message import add_messages
from langgraph.prebuilt import ToolNode, tools_condition

import sys
import asyncio

from langgraph.checkpoint.postgres.aio import AsyncPostgresSaver

from agents.base import BaseAgent
from core.llm import get_model
from schema import ChatMessage, UserInput

# 这里原本是静态导入本地 tool，现在我们准备全面拥抱 MCP
# 我们将会在 invoke 时动态挂载外部的微服务工具。


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

    def _build_graph(self, memory_saver, tools: list):
        from langgraph.types import Command
        from langgraph.prebuilt import create_react_agent
        from langchain_core.messages import SystemMessage

        # 实例化图画板，并绑定我们定义好的 State
        workflow = StateGraph(AgentState)

        # ---------------------------------------------------------
        # Phase 12: 多智能体 (Multi-Agent) 路由主管架构
        # ---------------------------------------------------------
        
        # 1. 定义主管用来分发任务的虚拟工具
        @tool
        def transfer_to_researcher():
            """当遇到需要查询知识库、内部文档、或者查天气的需求时，必须调用此工具将任务移交给研究专员(Researcher)。"""
            pass

        # 2. 初始化 Researcher 子图 (Sub-Agent)
        # 这是标准的 Manager-Worker 模式，Researcher 本身是一个具备 MCP 工具的 ReAct 闭环
        researcher_model = get_model() # 搬砖智能体默认使用快速主力模型
        researcher_agent = create_react_agent(
            researcher_model,
            tools=tools,
            state_modifier=SystemMessage(content="你是资深的调研专员(Researcher)。你有权限使用外部 MCP 微服务工具来检索信息和获取天气。拿到数据后，请直接向用户输出客观、精炼的事实总结，不要废话。")
        )

        async def researcher_node(state: AgentState) -> Command:
            """调研专员节点"""
            # 将主状态的对话历史透传给子图执行
            result = await researcher_agent.ainvoke({"messages": state["messages"]})
            # 仅提取子图中新生成的回复或工具日志，避免历史重复
            new_messages = result["messages"][len(state["messages"]):]
            # 执行完毕后，命令流控交还给主管进行审查
            return Command(
                goto="supervisor",
                update={"messages": new_messages}
            )

        # 3. 初始化 Supervisor 主管节点
        async def supervisor_node(state: AgentState) -> Command:
            """中枢路由主管节点"""
            messages = state["messages"]
            model_name = state.get("model_name")
            
            # 主管挂载转移工具，并且只看最后几轮对话避免被干扰
            supervisor_model = get_model(model_name).bind_tools([transfer_to_researcher])
            sys_msg = SystemMessage(content="""你是系统的大管家(Supervisor)。
如果用户向你提问涉及实时天气、专业知识、内部档按等需要检索的数据，你必须立即调用 transfer_to_researcher 工具。
如果用户只是在和你闲聊，或者 researcher 已经回答了用户的问题，请选择合适的话语直接回复用户。""")
            
            response = await supervisor_model.ainvoke([sys_msg] + messages)
            
            # 如果主管决定委派任务
            if response.tool_calls and response.tool_calls[0]["name"] == "transfer_to_researcher":
                # 注意：为了让 Researcher 能看到用户最原始的问题，我们这里不把带有 tool_call 的 response 存入状态，而是直接进行跳转
                return Command(goto="researcher")
                
            # 如果主管决定亲自回答（包含寒暄或结语）
            return Command(
                goto=END,
                update={"messages": [response]}
            )

        # ---------------------------------------------------------
        # 构建拓扑结构
        # ---------------------------------------------------------
        workflow.add_node("supervisor", supervisor_node)
        workflow.add_node("researcher", researcher_node)

        # 起始入口始终是主管
        workflow.add_edge(START, "supervisor")

        # 编译出炉 (挂载 Checkpointer 还原历史状态)
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


        # 动态编译，将数据库完全切换至企业级的 PostgreSQL
        postgres_uri = settings.postgres_uri.replace("+psycopg", "")
        
        # 🌟 Phase 12: 动态拉取外部的 MCP 微服务工具
        from core.mcp_client import get_mcp_tools
        mcp_tools = await get_mcp_tools()
        
        async with AsyncPostgresSaver.from_conn_string(postgres_uri) as memory_saver:
            # setup() 首次运行会自动在 pg 里创建 checkpoints 相关表，如果表存在则无视
            await memory_saver.setup()
            graph = self._build_graph(memory_saver, mcp_tools)
            
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
