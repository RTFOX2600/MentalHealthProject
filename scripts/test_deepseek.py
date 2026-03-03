import os
from openai import OpenAI

if __name__ == "__main__":
    input("DS?")
    # 初始化Openai客户端，从环境变量中读取您的API Key
    client = OpenAI(
        # 此为默认路径，您可根据业务所在地域进行配置
        base_url="https://ark.cn-beijing.volces.com/api/v3/bots",
        # 您的 API Key
        api_key="798382b6-3708-4bf7-82ba-80b0bfc30359",
    )

    # Streaming:
    print("----- streaming request -----")
    stream = client.chat.completions.create(
        model="bot-20260302112753-hzrqw",
        messages=[
            {"role": "system", "content": "你是人工智能助手"},
            {"role": "user", "content": "武汉轻工大学的所有学院和专业"},
        ],
        # 响应内容是否流式返回
        stream=True,
    )
    for chunk in stream:
        if not chunk.choices:
            continue
        print(chunk.choices[0].delta.content, end="")
    print()
