from django.http import HttpResponse, JsonResponse
from django.shortcuts import render, redirect
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from django.db.models import Q, Count
from django.utils import timezone
from django.core.cache import cache
from .models import Student
from accounts.models import College, Major, Grade
from .core import (
    calculate_canteen_stats_realtime,
    calculate_gate_stats_realtime,
    calculate_dormitory_stats_realtime,
    calculate_network_stats_realtime,
    calculate_academic_stats_realtime,
)
import hashlib
import json


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
def data_analysis_help(request) -> HttpResponse:
    """数据分析帮助页面"""
    if not check_staff_permission(request.user):
        messages.error(request, '您没有权限访问工作台')
        return redirect('home')
    
    context = {
        'current_page': 'data_analysis',
        'navbar_page': 'dashboard',
    }
    return render(request, 'staff_dashboard/data_analysis_help.html', context)


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
    - grade: 筛选年纭 ID
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


@login_required
def api_data_statistics(request) -> JsonResponse:
    """
    实时计算数据统计API
    GET参数：
    - college: 学院ID
    - major: 专业ID
    - grade: 年级ID
    - search: 搜索关键词（姓名或学号）
    - data_table: 数据表类型 (canteen, school_gate, dormitory, network, academic)
    - start_date: 开始日期
    - end_date: 结束日期
    - page: 页码
    - page_size: 每页数量
    """
    if not check_staff_permission(request.user):
        return JsonResponse({'error': '无权限访问'}, status=403)

    # from .models import (
    #     CanteenConsumptionRecord, SchoolGateAccessRecord,
    #     DormitoryAccessRecord, NetworkAccessRecord, AcademicRecord
    # )
    from datetime import datetime, timedelta
    # from django.db.models import Avg, Sum
    
    # 获取基础查询集（带权限过滤）
    students_queryset = filter_students_by_permission(request.user)
    
    # 筛选条件
    college_id = request.GET.get('college')
    if college_id:
        students_queryset = students_queryset.filter(college_id=college_id)
    
    major_id = request.GET.get('major')
    if major_id:
        students_queryset = students_queryset.filter(major_id=major_id)
    
    grade_id = request.GET.get('grade')
    if grade_id:
        students_queryset = students_queryset.filter(grade_id=grade_id)
    
    search = request.GET.get('search', '').strip()
    if search:
        students_queryset = students_queryset.filter(
            Q(name__icontains=search) | Q(student_id__icontains=search)
        )
    
    # 获取数据表类型
    data_table = request.GET.get('data_table', 'canteen')
    
    # 调试日志
    # print(f"DEBUG: Received data_table parameter: {data_table}")
    # print(f"DEBUG: All GET parameters: {dict(request.GET)}")
    
    data_type_map = {
        'canteen': 'canteen',
        'school_gate': 'school_gate',
        'dormitory': 'dormitory',
        'network': 'network',
        'academic': 'academic'
    }
    data_type = data_type_map.get(data_table)
    if not data_type:
        return JsonResponse({'error': f'无效的数据表类型: {data_table}'}, status=400)
    
    # 日期范围
    start_date_str = request.GET.get('start_date')
    end_date_str = request.GET.get('end_date')
    
    if end_date_str:
        end_date = datetime.strptime(end_date_str, '%Y-%m-%d').date()
    else:
        end_date = timezone.now().date()
    
    if start_date_str:
        start_date = datetime.strptime(start_date_str, '%Y-%m-%d').date()
    else:
        start_date = end_date - timedelta(days=30)
    
    # 获取排序参数
    order_by = request.GET.get('order_by', 'student_id')
    order = request.GET.get('order', 'asc')
    
    # 生成缓存键（基于所有影响统计结果的参数，排序参数不影响统计结果）
    cache_key_data = {
        'version': 'v3',  # 版本号：修改统计字段时增加版本号
        'user_id': request.user.id,
        'college': college_id,
        'major': major_id,
        'grade': grade_id,
        'search': search,
        'data_table': data_table,
        'start_date': start_date.isoformat(),
        'end_date': end_date.isoformat(),
        # 注意：order_by 和 order 不包含在缓存键中，因为排序不需要重新计算统计
    }
    cache_key = 'data_stats_' + hashlib.md5(
        json.dumps(cache_key_data, sort_keys=True).encode()
    ).hexdigest()
    
    # 尝试从缓存获取
    cached_data = cache.get(cache_key)
    if cached_data:
        # 使用缓存的数据（未排序）
        data_with_stats = cached_data
    else:
        # 缓存未命中，需要重新计算
        
        # 获取所有符合条件的学生（用于全局排序）
        all_students = students_queryset.select_related('college', 'major', 'grade')
        
        # 实时计算所有学生的统计数据
        data_with_stats = []
        for student in all_students:
            result = {
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
            }
            
            # 根据数据类型实时计算统计
            if data_type == 'canteen':
                stat_data = calculate_canteen_stats_realtime(student, start_date, end_date)
                result['avg_expense'] = stat_data.get('avg_expense', 0)
                result['min_expense'] = stat_data.get('min_expense', 0)
                result['expense_trend'] = stat_data.get('expense_trend', 0)
            elif data_type == 'school_gate':
                stat_data = calculate_gate_stats_realtime(student, start_date, end_date)
                result['night_in_out_count'] = stat_data.get('night_in_out_count', 0)
                result['late_night_in_out_count'] = stat_data.get('late_night_in_out_count', 0)
                result['total_count'] = stat_data.get('total_count', 0)
            elif data_type == 'dormitory':
                stat_data = calculate_dormitory_stats_realtime(student, start_date, end_date)
                result['night_in_out_count'] = stat_data.get('night_in_out_count', 0)
                result['late_night_in_out_count'] = stat_data.get('late_night_in_out_count', 0)
                result['total_count'] = stat_data.get('total_count', 0)
            elif data_type == 'network':
                stat_data = calculate_network_stats_realtime(student, start_date, end_date)
                result['vpn_usage_rate'] = f"{stat_data.get('vpn_usage_rate', 0)}%"
                result['night_usage_rate'] = f"{stat_data.get('night_usage_rate', 0)}%"
                result['late_night_usage_rate'] = f"{stat_data.get('late_night_usage_rate', 0)}%"
                result['avg_duration'] = f"{stat_data.get('avg_duration', 0)}小时"
                result['max_duration'] = f"{stat_data.get('max_duration', 0)}小时"
                result['_vpn_usage_rate_raw'] = stat_data.get('vpn_usage_rate', 0)
                result['_night_usage_rate_raw'] = stat_data.get('night_usage_rate', 0)
                result['_late_night_usage_rate_raw'] = stat_data.get('late_night_usage_rate', 0)
                result['_avg_duration_raw'] = stat_data.get('avg_duration', 0)
                result['_max_duration_raw'] = stat_data.get('max_duration', 0)
            elif data_type == 'academic':
                stat_data = calculate_academic_stats_realtime(student, start_date, end_date)
                result['avg_score'] = stat_data.get('avg_score', 0)
                result['score_trend'] = stat_data.get('score_trend', 0)
            
            data_with_stats.append(result)
        
        # 缓存未排序的结果（60分钟）
        cache.set(cache_key, data_with_stats, 3600)
    
    # 对数据进行排序（无论是否来自缓存）
    sort_key_map = {
        'student_id': lambda x: x['student_id'],
        'name': lambda x: x['name'],
        'avg_expense': lambda x: x.get('avg_expense', 0),
        'min_expense': lambda x: x.get('min_expense', 0),
        'expense_trend': lambda x: x.get('expense_trend', 0),
        'night_in_out_count': lambda x: x.get('night_in_out_count', 0),
        'late_night_in_out_count': lambda x: x.get('late_night_in_out_count', 0),
        'total_count': lambda x: x.get('total_count', 0),
        'vpn_usage_rate': lambda x: x.get('_vpn_usage_rate_raw', 0),
        'night_usage_rate': lambda x: x.get('_night_usage_rate_raw', 0),
        'late_night_usage_rate': lambda x: x.get('_late_night_usage_rate_raw', 0),
        'avg_duration': lambda x: x.get('_avg_duration_raw', 0),
        'max_duration': lambda x: x.get('_max_duration_raw', 0),
        'avg_score': lambda x: x.get('avg_score', 0),
        'score_trend': lambda x: x.get('score_trend', 0),
    }
    
    if order_by in sort_key_map:
        data_with_stats.sort(key=sort_key_map[order_by], reverse=(order == 'desc'))
    
    # 总数
    total_students = len(data_with_stats)
    
    # 分页
    try:
        page = int(request.GET.get('page', 1))
        page_size = int(request.GET.get('page_size', 20))
    except ValueError:
        page = 1
        page_size = 20
    
    page_size = min(max(page_size, 10), 100)
    start_idx = (page - 1) * page_size
    end_idx = start_idx + page_size
    
    # 获取当前页数据并移除临时字段
    data = []
    for item in data_with_stats[start_idx:end_idx]:
        item.pop('_vpn_usage_rate_raw', None)
        item.pop('_night_usage_rate_raw', None)
        item.pop('_late_night_usage_rate_raw', None)
        item.pop('_avg_duration_raw', None)
        item.pop('_max_duration_raw', None)
        data.append(item)
    
    return JsonResponse({
        'success': True,
        'data': data,
        'total': total_students,
        'page': page,
        'page_size': page_size,
        'total_pages': (total_students + page_size - 1) // page_size,
    })
