import os
import sys
from langchain_mcp_adapters.client import MultiServerMCPClient

async def get_mcp_tools():
    """获取所有挂载在 MCP Server 上的外部微服务工具。
    返回的工具数组可以直接被 LangChain/LangGraph 引擎加载使用。
    """
    
    # 动态获取 mcp_server.py 的绝对路径，保证启动路径无忧
    current_dir = os.path.dirname(os.path.abspath(__file__))
    src_dir = os.path.dirname(current_dir)
    mcp_script_path = os.path.join(src_dir, "mcp_server.py")
    
    # 按照 MCP 规范配置客户端连接参数
    mcp_server_config = {
        "agentops_microservice": {
            "transport": "stdio",
            "command": sys.executable,  # 自动使用当前系统的 python 解释器
            "args": [mcp_script_path],
        }
    }
    
    # 建立 Multi-Server MCP 客户端连接
    client = MultiServerMCPClient(mcp_server_config)
    
    # 从外接的 MCP Server 动态探测可用工具，并转换为 LangChain 的 BaseTool 数组
    tools = await client.get_tools()
    
    return tools
