import sys
import os
import asyncio

# 将 src 目录加入 Python 路径
sys.path.append(os.path.join(os.path.dirname(__file__), '..', 'src'))

from agents.graph_agent import GraphAgent
from schemas.api_models import UserInput

import pytest

@pytest.mark.skip(reason="需要真实大模型及有效的 API Key 才能触发自我纠错，暂不参与 CI 测试。")
@pytest.mark.asyncio
async def test_self_correction():
    print("============= 实例化 GraphAgent (自我纠错测试) =============")
    agent = GraphAgent()
    
    # 故意传带有 "市" 的参数，触发我们的 ValueError 业务拦截
    user_input = UserInput(
        message="帮我查一下北京市的天气怎么样？",
        user_id="test_user",
        thread_id="test_self_correction_thread"
    )
    
    print(f"\nUser: {user_input.message}")
    print("\n============= 开始流式调用 =============")
    
    # 直接调用 invoke 观察我们的系统日志输出
    async for chunk in agent.invoke(user_input):
        print(chunk, end="", flush=True)
    
    print("\n============= 测试完成 =============")

if __name__ == "__main__":
    asyncio.run(test_self_correction())
