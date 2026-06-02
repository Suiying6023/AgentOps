# test_llm.py
from core.llm import get_model
from langchain_openai import ChatOpenAI

def test_fake_model():
    print("=== 测试开始 ===")
    
    # 1. 实例化模拟模型
    model = get_model("fake")
    
    # 2. 检查模型类型和参数
    print("正在检查模型配置...")
    assert isinstance(model, ChatOpenAI)
    assert model.model_name == "fake"
    
    print("=== 测试结束 ===")

if __name__ == "__main__":
    test_fake_model()
