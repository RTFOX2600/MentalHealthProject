import os
import json
from django.db import models
from django.http import StreamingHttpResponse, JsonResponse
from django.views.decorators.http import require_http_methods
from django.contrib.auth.decorators import login_required
from django.views.decorators.csrf import csrf_exempt
from openai import OpenAI
from .models import ChatSession, ChatMessage, estimate_tokens


# 系统提示词
SYSTEM_PROMPT = """你是一位专业的武汉轻工大学的 AI 辅导员，名字叫"小智"。
回答风格：回答多要正面积极，复杂概念简单化解释，不确定的问题建议咨询相关人员、查询相关网站，重要事项提醒以官方通知为准。
"""


@login_required
@require_http_methods(["POST"])
def create_session(request):
    """创建新的聊天会话"""
    try:
        session = ChatSession.objects.create(
            user=request.user,
            title="新对话"
        )
        return JsonResponse({
            'status': 'success',
            'session_id': session.id,
            'message': '会话创建成功'
        })
    except Exception as e:
        return JsonResponse({
            'status': 'error',
            'message': f'创建会话失败: {str(e)}'
        }, status=500)


@login_required
@require_http_methods(["GET"])
def get_sessions(request):
    """获取用户的所有会话列表"""
    try:
        sessions = ChatSession.objects.filter(user=request.user)
        data = [{
            'id': s.id,
            'title': s.title or '新对话',
            'total_tokens': s.total_tokens,
            'created_at': s.created_at.strftime('%Y-%m-%d %H:%M'),
            'updated_at': s.updated_at.strftime('%Y-%m-%d %H:%M')
        } for s in sessions]
        
        return JsonResponse({
            'status': 'success',
            'sessions': data
        })
    except Exception as e:
        return JsonResponse({
            'status': 'error',
            'message': f'获取会话列表失败: {str(e)}'
        }, status=500)


@login_required
@require_http_methods(["GET"])
def get_session_messages(request, session_id):
    """获取指定会话的所有消息"""
    try:
        session = ChatSession.objects.get(id=session_id, user=request.user)
        messages = session.messages.all()
        
        data = [{
            'role': m.role,
            'content': m.content,
            'created_at': m.created_at.strftime('%Y-%m-%d %H:%M:%S')
        } for m in messages]
        
        return JsonResponse({
            'status': 'success',
            'messages': data
        })
    except ChatSession.DoesNotExist:
        return JsonResponse({
            'status': 'error',
            'message': '会话不存在'
        }, status=404)
    except Exception as e:
        return JsonResponse({
            'status': 'error',
            'message': f'获取消息失败: {str(e)}'
        }, status=500)


@login_required
@require_http_methods(["POST"])
def chat_stream(request):
    """流式聊天接口"""
    try:
        # 解析请求
        data = json.loads(request.body)
        session_id = data.get('session_id')
        user_message = data.get('message', '').strip()
        
        if not user_message:
            return JsonResponse({
                'status': 'error',
                'message': '消息内容不能为空'
            }, status=400)
        
        # 获取或创建会话
        if session_id:
            try:
                session = ChatSession.objects.get(id=session_id, user=request.user)
            except ChatSession.DoesNotExist:
                return JsonResponse({
                    'status': 'error',
                    'message': '会话不存在'
                }, status=404)
        else:
            session = ChatSession.objects.create(
                user=request.user,
                title=user_message[:50]  # 使用前50个字符作为标题
            )
        
        # 保存用户消息，并计算 token
        user_tokens = estimate_tokens(user_message)
        ChatMessage.objects.create(
            session=session,
            role='user',
            content=user_message,
            token_count=user_tokens
        )
                
        # 获取历史消息（最近 20 条非 system 消息，用于上下文）
        history_messages = list(
            session.messages
            .exclude(role='system')
            .order_by('-created_at')[:20]
        )
        history_messages.reverse()
        
        # 构建消息列表
        messages = [{"role": "system", "content": SYSTEM_PROMPT}]
        for msg in history_messages:
            if msg.role != 'system':
                messages.append({
                    "role": msg.role,
                    "content": msg.content
                })
        
        # 调用 DeepSeek API
        api_key = os.getenv('DEEPSEEK_API_KEY')
        if not api_key:
            return JsonResponse({
                'status': 'error',
                'message': 'DeepSeek API Key 未配置'
            }, status=500)
        
        client = OpenAI(
            api_key=api_key,
            base_url="https://api.deepseek.com"
        )
        
        def event_stream():
            """生成 SSE 事件流"""
            try:
                # 先发送会话 ID
                yield f"data: {json.dumps({'type': 'session_id', 'session_id': session.id})}\n\n"
                
                assistant_message = ""
                # noinspection PyTypeChecker
                response = client.chat.completions.create(
                    model="deepseek-chat",
                    messages=messages,
                    stream=True,
                    temperature=0.7,
                    max_tokens=2000
                )
                
                for chunk in response:
                    if chunk.choices[0].delta.content:
                        content = chunk.choices[0].delta.content
                        assistant_message += content
                        yield f"data: {json.dumps({'type': 'content', 'content': content})}\n\n"
                
                # 保存助手消息，并更新会话 token 用量
                assistant_tokens = estimate_tokens(assistant_message)
                ChatMessage.objects.create(
                    session=session,
                    role='assistant',
                    content=assistant_message,
                    token_count=assistant_tokens
                )
                # 累加 token 到会话（用户消息 + 助手消息）
                ChatSession.objects.filter(pk=session.pk).update(
                    total_tokens=models.F('total_tokens') + user_tokens + assistant_tokens
                )
                
                # 发送完成信号
                yield f"data: {json.dumps({'type': 'done'})}\n\n"
                
            except Exception as e:
                yield f"data: {json.dumps({'type': 'error', 'message': str(e)})}\n\n"
        
        response = StreamingHttpResponse(
            event_stream(),
            content_type='text/event-stream'
        )
        response['Cache-Control'] = 'no-cache'
        response['X-Accel-Buffering'] = 'no'
        return response
        
    except json.JSONDecodeError:
        return JsonResponse({
            'status': 'error',
            'message': '请求格式错误'
        }, status=400)
    except Exception as e:
        return JsonResponse({
            'status': 'error',
            'message': f'处理请求失败: {str(e)}'
        }, status=500)


@login_required
@require_http_methods(["DELETE"])
def delete_session(request, session_id):
    """删除指定会话"""
    try:
        session = ChatSession.objects.get(id=session_id, user=request.user)
        session.delete()
        return JsonResponse({
            'status': 'success',
            'message': '会话删除成功'
        })
    except ChatSession.DoesNotExist:
        return JsonResponse({
            'status': 'error',
            'message': '会话不存在'
        }, status=404)
    except Exception as e:
        return JsonResponse({
            'status': 'error',
            'message': f'删除会话失败: {str(e)}'
        }, status=500)


@login_required
@require_http_methods(["POST"])
def rename_session(request, session_id):
    """重命名指定会话"""
    try:
        data = json.loads(request.body)
        new_title = data.get('title', '').strip()
        if not new_title:
            return JsonResponse({'status': 'error', 'message': '标题不能为空'}, status=400)
        session = ChatSession.objects.get(id=session_id, user=request.user)
        session.title = new_title[:100]
        session.save(update_fields=['title'])
        return JsonResponse({'status': 'success', 'title': session.title})
    except ChatSession.DoesNotExist:
        return JsonResponse({'status': 'error', 'message': '会话不存在'}, status=404)
    except Exception as e:
        return JsonResponse({'status': 'error', 'message': f'重命名失败: {str(e)}'}, status=500)
