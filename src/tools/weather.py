from pydantic import BaseModel, Field
from langchain_core.tools import tool
import httpx

# 1. 定义输入结构
class WeatherInput(BaseModel):
    city: str = Field(
        ...,
        description="必须是中文的城市名称，例如：北京、上海。不要带'市'字。"
    )

# 2. 将参数挂载到工具上
@tool(args_schema=WeatherInput)
def get_weather(city: str) -> str:
    """获取指定城市的实时天气情况与温度。"""
    
    if "市" in city:
        city = city.replace("市", "")

    url = f"https://wttr.in/{city}?format=j1"
    try:
        # 使用 httpx 获取真实数据
        with httpx.Client(timeout=10.0) as client:
            resp = client.get(url)
            resp.raise_for_status()
            data = resp.json()
            
            current_condition = data['current_condition'][0]
            temp = current_condition['temp_C']
            desc = current_condition['lang_zh'][0]['value'] if 'lang_zh' in current_condition else current_condition['weatherDesc'][0]['value']
            humidity = current_condition['humidity']
            wind = current_condition['windspeedKmph']
            
            return f"{city}当前天气：{desc}，气温 {temp}℃，湿度 {humidity}%，风速 {wind} km/h。"
    except Exception as e:
        # 异常将反馈给大模型进行纠错重试
        return f"无法获取 {city} 的天气数据，错误信息：{str(e)}。可能是城市名称不支持或者网络异常。"

