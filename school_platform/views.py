from django.shortcuts import render


def home_view(request):
    """首页视图"""
    context = {
        'current_page': 'home',
    }
    
    # 如果用户已登录，检查是否有待审核的角色变更请求
    if request.user.is_authenticated:
        from accounts.models import ProfileChangeRequest
        pending_role_request = ProfileChangeRequest.objects.filter(
            user=request.user,
            change_type='role_change',
            status='pending'
        ).first()
        
        if pending_role_request:
            # 添加 requested_role_display 属性以便模板使用
            role_choices = dict(request.user.ROLE_CHOICES)
            pending_role_request.requested_role_display = role_choices.get(
                pending_role_request.requested_role, '未知'
            )
            context['pending_role_request'] = pending_role_request
    
    return render(request, 'home.html', context)


def about_view(request):
    """关于页面视图"""
    context = {
        'current_page': 'about',
    }
    return render(request, 'about.html', context)
