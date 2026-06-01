from pydantic import BaseModel, Field
from langchain_core.tools import tool

# 1. 定义输入结构
class WeatherInput(BaseModel):
    city: str = Field(
        ...,
        description="必须是中文的城市名称，例如：北京、上海。不能带'市'字。"
    )

# 2. 将参数挂载到工具上
@tool(args_schema=WeatherInput)
def get_weather(city: str) -> str:
    """获取指定城市的天气情况。"""
    
    # 模拟业务逻辑拦截
    if "市" in city:
        # 异常将反馈给大模型进行纠错重试
        raise ValueError("参数错误：城市名称不能包含'市'字，请修改后重试。")
        
    return f"{city}今天天气晴朗，气温25度，微风。"
