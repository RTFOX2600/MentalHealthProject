from django.urls import path
from . import views, api

app_name = 'ai_counselor'

urlpatterns = [
    # 页面路由
    path('', views.chat_view, name='chat'),
    
    # API 路由
    path('api/sessions/', api.get_sessions, name='api_get_sessions'),
    path('api/sessions/create/', api.create_session, name='api_create_session'),
    path('api/sessions/<int:session_id>/', api.get_session_messages, name='api_get_session_messages'),
    path('api/sessions/<int:session_id>/delete/', api.delete_session, name='api_delete_session'),
    path('api/sessions/<int:session_id>/rename/', api.rename_session, name='api_rename_session'),
    path('api/chat/stream/', api.chat_stream, name='api_chat_stream'),
]
