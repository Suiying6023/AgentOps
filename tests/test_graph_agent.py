import sys
import os
import asyncio

sys.path.append(os.path.join(os.path.dirname(__file__), '..', 'src'))

from agents.graph_agent import GraphAgent
from core.schema import UserInput

import pytest

@pytest.mark.asyncio
async def test_graph_agent():
    print("============= 实例化 GraphAgent =============")
    agent = GraphAgent()
    
    user_input = UserInput(
        message="我去二线城市出差，和客户吃了一顿 400 块钱的晚饭，可以全额报销吗？",
        user_id="test_user"
    )
    
    print(f"\nUser: {user_input.message}")
    print("Agent 流式输出: ", end="")
    
    chunks = []
    async for chunk in agent.invoke(user_input):
        print(chunk, end="", flush=True)
        chunks.append(chunk)
        
    assert len(chunks) > 0, "未能获取到有效的流式输出"
    print("\n\n============= 测试完成 =============")
