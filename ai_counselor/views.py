from django.shortcuts import render
from django.contrib.auth.decorators import login_required


@login_required
def chat_view(request):
    """AI 辅导员聊天页面"""
    return render(request, 'ai_counselor/chat.html', {
        'current_page': 'ai_counselor'
    })
