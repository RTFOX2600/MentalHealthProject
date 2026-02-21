from django.http import HttpResponse, JsonResponse
from django.shortcuts import render, redirect
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from django.db.models import Q, Count
from .models import Student
from accounts.models import College, Major, Grade


def check_staff_permission(user) -> bool:
    """检查用户是否为工作人员（辅导员或管理员）"""
    return user.role in ['counselor', 'admin']


def filter_students_by_permission(user, queryset=None):
    """
    根据用户权限过滤学生数据
    - 管理员：可以查看所有学生
    - 辅导员：只能查看同时满足负责学院/专业/年级的学生（交集逻辑）
    """
    if queryset is None:
        queryset = Student.objects.all()
    
    # 管理员可以查看所有数据
    if user.role == 'admin':
        return queryset
    
    # 辅导员只能查看自己负责的数据（交集逻辑）
    if user.role == 'counselor':
        managed_colleges = user.managed_colleges.all()
        managed_majors = user.managed_majors.all()
        managed_grades = user.managed_grades.all()
        
        # 使用交集逻辑：必须同时满足所有已分配的负责范围
        if managed_colleges.exists():
            queryset = queryset.filter(college__in=managed_colleges)
        
        if managed_majors.exists():
            queryset = queryset.filter(major__in=managed_majors)
        
        if managed_grades.exists():
            queryset = queryset.filter(grade__in=managed_grades)
        
        # 如果没有分配任何责任范围，返回空查询集
        if not (managed_colleges.exists() or managed_majors.exists() or managed_grades.exists()):
            return queryset.none()
        
        return queryset.distinct()
    
    # 其他角色无权限
    return queryset.none()


@login_required
def dashboard_home(request) -> HttpResponse:
    """工作台首页，默认跳转到数据上传"""
    if not check_staff_permission(request.user):
        messages.error(request, '您没有权限访问工作台')
        return redirect('home')
    return redirect('staff_dashboard:data_upload')


@login_required
def data_upload(request) -> HttpResponse:
    """数据上传页面"""
    if not check_staff_permission(request.user):
        messages.error(request, '您没有权限访问工作台')
        return redirect('home')
    
    context = {
        'current_page': 'data_upload',
        'navbar_page': 'dashboard',
    }
    return render(request, 'staff_dashboard/data_upload.html', context)


@login_required
def data_analysis(request) -> HttpResponse:
    """数据分析页面"""
    if not check_staff_permission(request.user):
        messages.error(request, '您没有权限访问工作台')
        return redirect('home')
    
    # 获取用户有权限的数据的筛选选项
    students = filter_students_by_permission(request.user)
    
    # 获取所有可用的筛选项（基于权限）
    colleges = College.objects.filter(data_students__in=students).distinct().order_by('code')
    majors = Major.objects.filter(data_students__in=students).distinct().order_by('code')
    grades = Grade.objects.filter(data_students__in=students).distinct().order_by('-year')
    
    context = {
        'current_page': 'data_analysis',
        'navbar_page': 'dashboard',
        'colleges': colleges,
        'majors': majors,
        'grades': grades,
        'total_students': students.count(),
    }
    return render(request, 'staff_dashboard/data_analysis.html', context)


@login_required
def public_opinion(request) -> HttpResponse:
    """舆论监控页面"""
    if not check_staff_permission(request.user):
        messages.error(request, '您没有权限访问工作台')
        return redirect('home')
    
    context = {
        'current_page': 'public_opinion',
        'navbar_page': 'dashboard',
    }
    return render(request, 'staff_dashboard/public_opinion.html', context)


@login_required
def api_student_list(request) -> JsonResponse:
    """
    学生列表API，支持筛选、排序、分页
    GET参数：
    - college: 学院ID
    - major: 专业ID
    - grade: 年级ID
    - search: 搜索关键词（姓名或学号）
    - order_by: 排序字段 (student_id, name, college, major, grade)
    - order: 排序方向 (asc, desc)
    - page: 页码
    - page_size: 每页数量
    """
    if not check_staff_permission(request.user):
        return JsonResponse({'error': '无权限访问'}, status=403)
    
    # 获取基础查询集（带权限过滤）
    queryset = filter_students_by_permission(request.user)
    
    # 筛选条件
    college_id = request.GET.get('college')
    if college_id:
        queryset = queryset.filter(college_id=college_id)
    
    major_id = request.GET.get('major')
    if major_id:
        queryset = queryset.filter(major_id=major_id)
    
    grade_id = request.GET.get('grade')
    if grade_id:
        queryset = queryset.filter(grade_id=grade_id)
    
    search = request.GET.get('search', '').strip()
    if search:
        queryset = queryset.filter(
            Q(name__icontains=search) | Q(student_id__icontains=search)
        )
    
    # 排序
    order_by = request.GET.get('order_by', 'student_id')
    order = request.GET.get('order', 'asc')
    
    # 映射排序字段
    order_mapping = {
        'student_id': 'student_id',
        'name': 'name',
        'college': 'college__code',
        'major': 'major__code',
        'grade': 'grade__year',
    }
    
    order_field = order_mapping.get(order_by, 'student_id')
    if order == 'desc':
        order_field = '-' + order_field
    
    queryset = queryset.order_by(order_field)
    
    # 统计总数
    total = queryset.count()
    
    # 分页
    try:
        page = int(request.GET.get('page', 1))
        page_size = int(request.GET.get('page_size', 20))
    except ValueError:
        page = 1
        page_size = 20
    
    # 限制每页数量
    page_size = min(max(page_size, 10), 100)
    
    start = (page - 1) * page_size
    end = start + page_size
    
    students = queryset.select_related('college', 'major', 'grade')[start:end]
    
    # 构建返回数据
    data = []
    for student in students:
        data.append({
            'id': student.id,
            'student_id': student.student_id,
            'name': student.name,
            'college': {
                'id': student.college.id,
                'name': student.college.name,
                'code': student.college.code,
            },
            'major': {
                'id': student.major.id,
                'name': student.major.name,
                'code': student.major.code,
            },
            'grade': {
                'id': student.grade.id,
                'name': student.grade.name,
                'year': student.grade.year,
            },
        })
    
    return JsonResponse({
        'success': True,
        'data': data,
        'total': total,
        'page': page,
        'page_size': page_size,
        'total_pages': (total + page_size - 1) // page_size,
    })


@login_required
def api_student_statistics(request) -> JsonResponse:
    """
    学生统计API，按学院/专业/年级统计人数
    GET参数：
    - group_by: 分组字段 (college, major, grade)
    - college: 筛选学院ID
    - major: 筛选专业ID
    - grade: 筛选年纭ID
    """
    if not check_staff_permission(request.user):
        return JsonResponse({'error': '无权限访问'}, status=403)
    
    # 获取基础查询集（带权限过滤）
    queryset = filter_students_by_permission(request.user)
    
    # 筛选条件
    college_id = request.GET.get('college')
    if college_id:
        queryset = queryset.filter(college_id=college_id)
    
    major_id = request.GET.get('major')
    if major_id:
        queryset = queryset.filter(major_id=major_id)
    
    grade_id = request.GET.get('grade')
    if grade_id:
        queryset = queryset.filter(grade_id=grade_id)
    
    # 分组统计
    group_by = request.GET.get('group_by', 'college')
    
    if group_by == 'college':
        stats = queryset.values(
            'college__id', 'college__name', 'college__code'
        ).annotate(
            count=Count('id')
        ).order_by('college__code')
        
        data = [{
            'id': item['college__id'],
            'name': item['college__name'],
            'code': item['college__code'],
            'count': item['count'],
        } for item in stats]
        
    elif group_by == 'major':
        stats = queryset.values(
            'major__id', 'major__name', 'major__code', 'major__college__name'
        ).annotate(
            count=Count('id')
        ).order_by('major__code')
        
        data = [{
            'id': item['major__id'],
            'name': item['major__name'],
            'code': item['major__code'],
            'college': item['major__college__name'],
            'count': item['count'],
        } for item in stats]
        
    elif group_by == 'grade':
        stats = queryset.values(
            'grade__id', 'grade__name', 'grade__year'
        ).annotate(
            count=Count('id')
        ).order_by('-grade__year')
        
        data = [{
            'id': item['grade__id'],
            'name': item['grade__name'],
            'year': item['grade__year'],
            'count': item['count'],
        } for item in stats]
    else:
        return JsonResponse({'error': '无效的分组字段'}, status=400)
    
    return JsonResponse({
        'success': True,
        'data': data,
        'total': queryset.count(),
        'group_by': group_by,
    })
