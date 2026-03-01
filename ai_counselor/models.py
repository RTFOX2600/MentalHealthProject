from django.db import models
from django.conf import settings


class ChatSession(models.Model):
    """AI 聊天会话"""
    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name='chat_sessions',
        verbose_name='用户'
    )
    title = models.CharField('会话标题', max_length=200, default='新对话')
    # 用量统计：记录该会话累计消耗的近似 Token 数，便于多用户用量监控
    total_tokens = models.PositiveIntegerField('Token 用量', default=0)
    created_at = models.DateTimeField('创建时间', auto_now_add=True)
    updated_at = models.DateTimeField('更新时间', auto_now=True)

    class Meta:
        db_table = 'ai_counselor_session'
        verbose_name = 'AI 聊天会话'
        verbose_name_plural = verbose_name
        ordering = ['-updated_at']
        indexes = [
            # 多用户会话列表查询：按用户过滤 + 按更新时间排序
            models.Index(fields=['user', '-updated_at'], name='session_user_updated_idx'),
        ]

    def __str__(self):
        return f"{self.user.username} - {self.title}"


class ChatMessage(models.Model):
    """AI 聊天消息"""
    ROLE_CHOICES = [
        ('user', '用户'),
        ('assistant', '助手'),
        ('system', '系统'),
    ]

    session = models.ForeignKey(
        ChatSession,
        on_delete=models.CASCADE,
        related_name='messages',
        verbose_name='会话'
    )
    role = models.CharField('角色', max_length=20, choices=ROLE_CHOICES)
    content = models.TextField('消息内容')
    # 近似 Token 数：中文按字数计算，英文按 4 字符/token 估算
    token_count = models.PositiveIntegerField('Token 数', default=0)
    created_at = models.DateTimeField('创建时间', auto_now_add=True)

    class Meta:
        db_table = 'ai_counselor_message'
        verbose_name = 'AI 聊天消息'
        verbose_name_plural = verbose_name
        ordering = ['created_at']
        indexes = [
            # 会话消息历史查询：按会话过滤 + 按时间排序
            models.Index(fields=['session', 'created_at'], name='message_session_time_idx'),
        ]

    def __str__(self):
        return f"{self.get_role_display()}: {self.content[:50]}"


def estimate_tokens(text: str) -> int:
    """估算文本的 Token 数（中文按 1 字/token，英文按 4 字符/token）"""
    chinese_count = sum(1 for c in text if '\u4e00' <= c <= '\u9fff')
    other_count = len(text) - chinese_count
    return chinese_count + max(1, other_count // 4)
