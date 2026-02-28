import os
from openai import OpenAI

client = OpenAI(
    api_key='sk-22aebe4114294886bd14e0029de559a4',
    base_url="https://api.deepseek.com")

# noinspection PyTypeChecker
response = client.chat.completions.create(
    model="deepseek-chat",
    messages=[
        {"role": "system", "content": "你是一位乐于助人的助手，武汉轻工大学的 AI 辅导员"},
        {"role": "user", "content": "你是谁？"},
    ],
    stream=False
)

if __name__ == "__main__":
    print(response.choices[0].message.content)
