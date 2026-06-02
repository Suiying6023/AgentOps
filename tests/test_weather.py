import httpx
import json

def test_weather_stream():
    url = "http://127.0.0.1:8080/graph_agent/stream"
    # 测试包含工具意图的问题
    payload = {
        "message": "北京今天天气怎么样？"
    }
    
    headers = {
        # 如果你有在 service.py 设置 token 的话，记得带上
        # "Authorization": "Bearer your_token_here"
    }

    print(f"📡 正在向 {url} 发送天气查询...")
    
    # 建立流式连接
    with httpx.stream("POST", url, json=payload, headers=headers, timeout=30.0) as response:
        if response.status_code != 200:
            print(f"❌ 请求失败，状态码: {response.status_code}")
            print(response.read().decode())
            return
            
        print("💡 模型开始回复：", end="", flush=True)
        
        # 逐行读取 SSE 数据
        for line in response.iter_lines():
            if line.startswith("data: "):
                data_str = line[6:] # 去掉前缀
                try:
                    data = json.loads(data_str)
                    if data["type"] == "token":
                        # 实时打印出来的碎片
                        print(data["content"], end="", flush=True)
                    elif data["type"] == "done":
                        print("\n\n✅ [流式传输结束]")
                except json.JSONDecodeError:
                    pass

if __name__ == "__main__":
    test_weather_stream()
