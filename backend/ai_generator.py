import os
from dotenv import load_dotenv
from openai import OpenAI

# 加载环境变量
load_dotenv()

api_key = os.getenv("DASHSCOPE_API_KEY")
if not api_key:
    raise ValueError("请设置 DASHSCOPE_API_KEY 环境变量或在 .env 文件中配置")

client = OpenAI(
    api_key=api_key,
    base_url="https://dashscope.aliyuncs.com/compatible-mode/v1"
)

def generate_documentation(prompt: str) -> str:
    """
    根据 prompt 生成文档
    """
    try:
        response = client.chat.completions.create(
            model="deepseek-v3",  # 可换成 deepseek-r1 或其它模型
            messages=[{"role": "user", "content": prompt}]
        )
        return response.choices[0].message.content
    except Exception as e:
        return f"生成失败：{str(e)}"