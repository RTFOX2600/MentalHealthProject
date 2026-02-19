from django.http import HttpResponse
from django.shortcuts import render
from django.contrib.auth.decorators import login_required

@login_required
def demo_page(request) -> HttpResponse:
    """
    心理健康分析系统演示页面。
    
    渲染并返回演示主页 (demo.html)，该页面包含文件上传区域和分析启动按钮。
    """
    return render(request, 'mental_health/demo.html')
