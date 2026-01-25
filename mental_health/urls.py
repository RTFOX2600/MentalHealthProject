from django.urls import path
from . import views

app_name = 'mental_health'

urlpatterns = [
    path('demo/', views.demo_page, name='demo'),
    path('upload/<str:file_type>/', views.upload_file, name='upload'),
    path('upload-status/<str:task_id>/', views.check_upload_status, name='upload_status'),  # 新增
    path('analyze/<str:analysis_type>/', views.analyze_data, name='analyze'),
    path('task-status/<str:task_id>/', views.check_task_status, name='task_status'),
    path('download-result/<str:task_id>/', views.download_result, name='download_result'),
]
