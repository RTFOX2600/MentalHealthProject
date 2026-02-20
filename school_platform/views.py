from django.shortcuts import render


def home_view(request):
    """首页视图"""
    context = {
        'current_page': 'home',
    }
    
    # 如果用户已登录，检查是否有待审核的变更请求
    if request.user.is_authenticated:
        from accounts.models import ProfileChangeRequest
        import json
        
        # 获取所有待审核的请求
        pending_requests = ProfileChangeRequest.objects.filter(
            user=request.user,
            status='pending'
        )
        
        if pending_requests.exists():
            # 收集所有请求的详细信息
            request_details = []
            
            for req in pending_requests:
                if req.change_type == 'role_change':
                    # 角色变更请求
                    role_choices = dict(request.user.ROLE_CHOICES)
                    requested_role_name = role_choices.get(req.requested_role, '未知')
                    request_details.append({
                        'type': '角色变更',
                        'items': [f"请求身份：{requested_role_name}"]
                    })
                
                elif req.change_type == 'student_info':
                    # 学生信息变更
                    items = []
                    if req.requested_student_college:
                        items.append(f"学院：{req.requested_student_college.name}")
                    if req.requested_student_major:
                        items.append(f"专业：{req.requested_student_major.name}")
                    if req.requested_student_grade:
                        items.append(f"年级：{req.requested_student_grade.name}")
                    if items:
                        request_details.append({
                            'type': '组织信息变更',
                            'items': items
                        })
                
                elif req.change_type == 'manager_info':
                    # 辅导员/管理员信息变更
                    items = []
                    try:
                        if req.requested_managed_colleges:
                            college_ids = json.loads(req.requested_managed_colleges)
                            from accounts.models import College
                            colleges = College.objects.filter(id__in=college_ids)
                            if colleges:
                                items.append(f"负责学院：{', '.join([c.name for c in colleges])}")
                        
                        if req.requested_managed_majors:
                            major_ids = json.loads(req.requested_managed_majors)
                            from accounts.models import Major
                            majors = Major.objects.filter(id__in=major_ids)
                            if majors:
                                items.append(f"负责专业：{', '.join([m.name for m in majors])}")
                        
                        if req.requested_managed_grades:
                            grade_ids = json.loads(req.requested_managed_grades)
                            from accounts.models import Grade
                            grades = Grade.objects.filter(id__in=grade_ids)
                            if grades:
                                items.append(f"负责年级：{', '.join([g.name for g in grades])}")
                    except (json.JSONDecodeError, ValueError):
                        pass
                    
                    if items:
                        request_details.append({
                            'type': '组织信息变更',
                            'items': items
                        })
            
            context['pending_requests'] = request_details
    
    return render(request, 'home.html', context)


def about_view(request):
    """关于页面视图"""
    context = {
        'current_page': 'about',
    }
    return render(request, 'about.html', context)
