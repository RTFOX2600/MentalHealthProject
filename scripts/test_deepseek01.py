from openai import OpenAI
from typing import Dict, List, Optional
import uuid
from datetime import datetime


class AICounselor:
    def __init__(self, api_key: str):
        """初始化 AI 辅导员系统"""
        self.client = OpenAI(
            api_key=api_key,
            base_url="https://api.deepseek.com"
        )

        # 存储结构：{user_id: {session_id: {"messages": [...], "created_at": "..."}}}
        self.user_sessions: Dict[str, Dict[str, Dict]] = {}

    def create_user(self, user_id: str) -> None:
        """创建新用户"""
        if user_id not in self.user_sessions:
            self.user_sessions[user_id] = {}

    def create_session(self, user_id: str, system_prompt: str = "") -> str:
        """为用户创建新会话，返回 session_id"""
        if user_id not in self.user_sessions:
            self.create_user(user_id)

        session_id = str(uuid.uuid4())[:8]  # 生成简短会话ID

        # 初始化会话
        messages = []
        if system_prompt:
            messages.append({"role": "system", "content": system_prompt})

        self.user_sessions[user_id][session_id] = {
            "messages": messages,
            "created_at": datetime.now().isoformat(),
            "system_prompt": system_prompt
        }

        return session_id

    def chat(
            self,
            user_id: str,
            session_id: str,
            user_message: str,
            model: str = "deepseek-chat",
            temperature: float = 1.3
    ) -> str:
        """在指定会话中聊天"""
        if user_id not in self.user_sessions:
            raise ValueError(f"用户 {user_id} 不存在")

        if session_id not in self.user_sessions[user_id]:
            raise ValueError(f"会话 {session_id} 不存在")

        # 获取会话
        session = self.user_sessions[user_id][session_id]

        # 添加用户消息
        session["messages"].append({"role": "user", "content": user_message})

        try:
            # 调用 DeepSeek
            response = self.client.chat.completions.create(
                model=model,
                messages=session["messages"],
                temperature=temperature,
                stream=False
            )

            # 获取 AI 回复
            ai_response = response.choices[0].message.content

            # 添加到会话历史
            session["messages"].append({"role": "assistant", "content": ai_response})

            return ai_response

        except Exception as e:
            # 移除失败的用户消息
            session["messages"].pop()
            raise Exception(f"API调用失败: {str(e)}")

    def get_sessions(self, user_id: str) -> List[Dict]:
        """获取用户的所有会话"""
        if user_id not in self.user_sessions:
            return []

        sessions = []
        for sid, data in self.user_sessions[user_id].items():
            sessions.append({
                "session_id": sid,
                "created_at": data["created_at"],
                "message_count": len(data["messages"]),
                "system_prompt": data.get("system_prompt", "")
            })

        return sessions

    def clear_session(self, user_id: str, session_id: str) -> None:
        """清空指定会话的历史"""
        if (user_id in self.user_sessions and
                session_id in self.user_sessions[user_id]):
            # 重置消息，保留系统提示
            system_prompt = self.user_sessions[user_id][session_id].get("system_prompt", "")
            self.user_sessions[user_id][session_id]["messages"] = [
                {"role": "system", "content": system_prompt}
            ] if system_prompt else []


# 使用示例
if __name__ == "__main__":
    print("=" * 50)
    # 初始化
    counselor = AICounselor(api_key="sk-22aebe4114294886bd14e0029de559a4")

    # 用户1创建学习辅导会话
    user1_id = "Alpha00001"
    session1_id = counselor.create_session(
        user1_id,
        system_prompt="""你是一位武汉轻工大学的 AI 辅导员。

回答风格：
- 回答多要正面积极
- 复杂概念简单化解释
- 不确定的问题建议咨询相关人员
- 重要事项提醒以官方通知为准

请用中文回复，保持专业且亲切的辅导员形象。"""
    )

    message = "我今天早上睡过了，早八没有上，会有影响吗？"
    print(f"用户 1: {message}")
    print("-" * 50)
    # 用户1聊天
    response1 = counselor.chat(
        user1_id,
        session1_id,
        message
    )
    print(f"DS 回复: {response1}")

    print()
    print("=" * 50)

    # 用户2创建编程辅导会话
    user2_id = "Beta00001"
    session2_id = counselor.create_session(
        user2_id,
        system_prompt="你是一位资深 Python 工程师。",
    )

    message = "简要介绍一下 Python 吧，它与 C++ 有什么不同？我是初学者。"
    print(f"用户 2: {message}")
    print("-" * 50)
    # 用户2的会话完全独立
    response2 = counselor.chat(
        user2_id,
        session2_id,
        message
    )
    print(f"DS 回复: {response2}")
    print("-" * 50)

    message = "缩进是啥，感觉好麻烦，在 C 里面都不是硬性要求"
    print(f"用户 2: {message}")
    print("-" * 50)
    # 用户2继续对话（历史会被记住）
    response2 = counselor.chat(
        user2_id,
        session2_id,
        message
    )
    print(f"DS 回复: {response2}")
    print("=" * 50)

    # 查看用户2的所有会话
    print(f"用户 2 的会话列表: {counselor.get_sessions(user2_id)}")
