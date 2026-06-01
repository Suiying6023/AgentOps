import sys
import os
# 把 src 目录加入环境变量，防止依赖导入失败
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from mcp.server.fastmcp import FastMCP
from tools.rag import search_knowledge_base
from tools.weather import get_weather

# 1. 初始化 FastMCP 实例
mcp = FastMCP("AgentOps_Microservice")

# 2. 暴露知识库检索为 MCP Tool
@mcp.tool()
def search_knowledge(query: str) -> str:
    """当你被问到任何需要查阅资料、事实核查或你不确定的问题时，必须调用此工具检索本地资料库。
    如果你无法通过常识回答，或者需要引用权威资料，请使用此工具。
    """
    try:
        from tools.rag import search_knowledge_base
        return search_knowledge_base.invoke({"query": query})
    except Exception as e:
        return f"检索失败，原因: {str(e)}"

@mcp.tool()
def search_compiled_wiki(query: str) -> str:
    """【实验功能】当你被明确要求搜索“维基”、“精华知识”或你需要获取高度提炼的结构化实体信息时，必须调用此工具。
    它会遍历并读取经过后台 LLM 深度编译后的完整 Markdown 页面，而不是零碎的切片片段。
    """
    try:
        from tools.wiki_compiler import search_llm_wiki
        return search_llm_wiki.invoke({"query": query})
    except Exception as e:
        return f"Wiki检索失败，原因: {str(e)}"

# 3. 暴露天气查询为 MCP Tool
@mcp.tool()
def get_current_weather(city: str) -> str:
    """获取指定城市的天气情况。必须是中文的城市名称，例如：北京、上海。不能带'市'字。"""
    try:
        return get_weather.invoke({"city": city})
    except Exception as e:
        # 异常原样抛出，以便利用 LangGraph 的纠错机制
        return str(e)

if __name__ == "__main__":
    # 以 stdio 模式启动服务，专供本地 Agent (或者外部的 Cursor IDE) 通过子进程挂载使用
    print("Starting FastMCP Server over stdio...", file=sys.stderr)
    mcp.run(transport='stdio')
