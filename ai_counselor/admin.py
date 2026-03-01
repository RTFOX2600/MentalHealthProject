from django.contrib import admin
from .models import ChatSession, ChatMessage


@admin.register(ChatSession)
class ChatSessionAdmin(admin.ModelAdmin):
    list_display = ['id', 'user', 'title', 'total_tokens', 'message_count_display', 'created_at', 'updated_at']
    list_filter = ['created_at', 'updated_at']
    search_fields = ['user__username', 'title']
    date_hierarchy = 'created_at'
    readonly_fields = ['total_tokens', 'created_at', 'updated_at']

    def message_count_display(self, obj):
        return obj.messages.count()
    message_count_display.short_description = '消息数'


@admin.register(ChatMessage)
class ChatMessageAdmin(admin.ModelAdmin):
    list_display = ['id', 'session', 'role', 'token_count', 'content_preview', 'created_at']
    list_filter = ['role', 'created_at']
    search_fields = ['content', 'session__user__username']
    date_hierarchy = 'created_at'
    readonly_fields = ['token_count', 'created_at']
    
    def content_preview(self, obj):
        return obj.content[:50] + '...' if len(obj.content) > 50 else obj.content
    content_preview.short_description = '消息预览'
