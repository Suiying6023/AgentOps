import asyncio
import time

from langchain_openai import OpenAIEmbeddings

# 将要测试的多个 API 节点放入列表，这里自动补充了 OpenAI 协议规范的 /v1 后缀
urls_to_test = [
    "https://api.gemai.cc/v1",
    "https://api.gemapi.ai/v1"
]
api_key = "sk-fake-key-for-testing"
model_name = "qwen3-embedding-8b"

async def test_batch(embeddings, batch_size: int) -> bool:
    print(f"  [{time.strftime('%H:%M:%S')}] 🚀 尝试并发量: {batch_size}")
    texts = [f"企业级稳定性测试文本，编号 {i}。" for i in range(batch_size)]
    start_time = time.time()
    
    try:
        vectors = await embeddings.aembed_documents(texts)
        elapsed = time.time() - start_time
        print(f"  ✅ 成功! 耗时: {elapsed:.2f}秒 | 吞吐: {batch_size/elapsed:.2f}条/s")
        return True
    except Exception as e:
        error_msg = str(e)[:150].replace('\n', ' ')
        print(f"  ❌ 失败! 错误: {error_msg}...")
        return False

async def main():
    # 阶梯并发数
    steps = [1, 2, 5, 10, 20, 50]
    
    for url in urls_to_test:
        print(f"\n" + "="*50)
        print(f"🌐 开始评测节点: {url}")
        print("="*50)
        
        embeddings = OpenAIEmbeddings(
            model=model_name,
            api_key=api_key,
            base_url=url,
            # dimensions 取消强制指定，防止该节点模型不支持 dimensions 参数
        )
        
        for batch_size in steps:
            success = await test_batch(embeddings, batch_size)
            if not success:
                print(f"  ⚠️ 该节点在并发 {batch_size} 时服务异常，终止对此节点的测试。")
                break
            
            # 成功后暂停1秒
            await asyncio.sleep(1)

if __name__ == "__main__":
    asyncio.run(main())
