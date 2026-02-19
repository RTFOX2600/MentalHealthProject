from django.http import HttpResponse
from django.shortcuts import render, redirect
from django.contrib.auth.decorators import login_required
from django.contrib import messages


def check_staff_permission(user) -> bool:
    """检查用户是否为工作人员（辅导员或管理员）"""
    return user.role in ['counselor', 'admin']


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
    
    context = {
        'current_page': 'data_analysis',
        'navbar_page': 'dashboard',
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
