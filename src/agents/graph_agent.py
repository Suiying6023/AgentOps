from collections.abc import AsyncGenerator
from typing import Annotated, TypedDict, Literal, NotRequired

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

# 动态挂载外部的微服务工具。


# 2. 定义图的状态 (State)
class AgentState(TypedDict):
    # 消息追加机制
    messages: Annotated[list[BaseMessage], add_messages]
    # 我们把用户选择的模型名也放进状态里，供后续的 Node 读取
    model_name: str
    # 由主管动态决定的子智能体复杂度级别
    subagent_complexity: NotRequired[Literal["simple", "complex"]]


class GraphAgent(BaseAgent):
    """基于 LangGraph 编排的智能体"""

    def __init__(self):
        super().__init__()

    def _build_graph(self, memory_saver, tools: list):
        from langgraph.types import Command
        from langchain_core.messages import SystemMessage, HumanMessage
        from pydantic import BaseModel, Field

        workflow = StateGraph(AgentState)


        class SubagentArgs(BaseModel):
            task: str = Field(description="子智能体需要执行的具体任务指令")
            complexity: Literal["simple", "complex"] = Field(
                default="simple",
                description="任务复杂度。简单查询填 'simple'，复杂推理填 'complex'。"
            )

        @tool(args_schema=SubagentArgs)
        async def create_subagent(task: str, complexity: str) -> str:
            """创建一个独立的后台子智能体来处理特定任务（如耗时检索、深入推理、并行子任务），并返回其执行结果报告。"""
            from langgraph.prebuilt import create_react_agent
            
            sub_model_name = "deepseek-ai/DeepSeek-R1" if complexity == "complex" else "deepseek-ai/DeepSeek-V3.2"
            sub_model = get_model(sub_model_name)
            
            sub_agent = create_react_agent(
                sub_model,
                tools=tools,
                prompt=SystemMessage(content="你是后台子智能体。请使用工具执行分配给你的任务，并返回客观的事实结果。排版要求紧凑，严禁在非必要情况下使用空行！")
            )
            
            print(f"[系统日志] 派生后台子智能体 (模型: {sub_model_name}) 任务: {task[:30]}...", file=sys.stderr)
            # 给子智能体分配全新的空白状态流执行任务，并打上特殊 tag 以便在外层进行事件拦截
            result = await sub_agent.ainvoke(
                {"messages": [HumanMessage(content=task)]},
                config={"tags": ["subagent_run"]}
            )
            
            return f"【子智能体汇报】:\n{result['messages'][-1].content}"

        # 把创建 Subagent 的能力作为工具，与物理工具一并装载
        all_tools = tools + [create_subagent]

        # 1. 主模型推理节点
        async def agent_node(state: AgentState):
            model_name = state.get("model_name")
            model = get_model(model_name).bind_tools(all_tools)
            
            sys_msg = SystemMessage(content="""你是主智能体 AgentOps。
拥有外部 MCP 微服务工具调用权限，直接解答用户问题。
【机制】：遇到多任务、长推理或并行探索需求时，请调用 create_subagent 工具创建子智能体进行后台处理，并基于其汇报生成总结。
【排版】：排版保持极致紧凑，段落与列表间最多保留一个换行符，严禁在非必要情况下使用空行！""")
            
            response = await model.ainvoke([sys_msg] + state["messages"])
            return {"messages": [response]}

        # 2. 工具执行节点
        tool_node = ToolNode(all_tools)

        # 构建拓扑结构
        workflow.add_node("agent", agent_node)
        workflow.add_node("tools", tool_node)

        workflow.add_edge(START, "agent")
        # 如果模型调用了工具，则走向 tools；如果没调，则走向 END
        workflow.add_conditional_edges("agent", tools_condition)
        workflow.add_edge("tools", "agent")

        return workflow.compile(checkpointer=memory_saver)

    async def invoke(
        self, user_input: UserInput, history: list[ChatMessage] = None
    ) -> AsyncGenerator[str, None]:
        """执行图流转并输出流式结果"""

        # 构建图流转的初始数据
        inputs = {
            "messages": [HumanMessage(content=user_input.message)],
            "model_name": user_input.model,
        }
        
        # Langfuse 监控接入与 Thread ID 注入
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


        # 配置 PostgreSQL URI
        postgres_uri = settings.postgres_uri.replace("+psycopg", "")
        
        # 动态拉取外部 MCP 工具
        from core.mcp_client import get_mcp_tools
        mcp_tools = await get_mcp_tools()
        
        async with AsyncPostgresSaver.from_conn_string(postgres_uri) as memory_saver:
            # setup() 首次运行会自动在 pg 里创建 checkpoints 相关表，如果表存在则无视
            await memory_saver.setup()
            graph = self._build_graph(memory_saver, mcp_tools)
            
            # 截获模型内部生成的事件流
            async for event in graph.astream_events(inputs, config=config, version="v2"):
                kind = event["event"]
                tags = event.get("tags", [])
                
                if kind == "on_chat_model_stream":
                    # 屏蔽子智能体内部的自言自语（防止在前端和主模型的话重复），仅透传主智能体
                    if "subagent_run" in tags:
                        continue
                        
                    chunk_content = event["data"]["chunk"].content
                    if chunk_content:
                        yield str(chunk_content)
                elif kind == "on_tool_start":
                    tool_name = event["name"]
                    tool_input = event["data"].get("input", {})
                    
                    if "subagent_run" in tags:
                        yield f"\n\n> ⚙️ [子进程] 调用工具: `{tool_name}`\n\n"
                    else:
                        yield f"\n\n> ⚙️ [主进程] 调用工具: `{tool_name}`\n> 参数: `{tool_input}`\n\n"
                elif kind == "on_tool_end":
                    if "subagent_run" in tags:
                        yield f"> ✓ [子进程] 执行完毕\n\n"
                    else:
                        yield f"> ✓ [主进程] 执行完毕\n\n"
