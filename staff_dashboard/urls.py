from django.urls import path
from . import views

app_name = 'staff_dashboard'

urlpatterns = [
    path('', views.dashboard_home, name='home'),
    path('data-upload/', views.data_upload, name='data_upload'),
    path('data-analysis/', views.data_analysis, name='data_analysis'),
    path('public-opinion/', views.public_opinion, name='public_opinion'),
    
    # API接口
    path('api/student-list/', views.api_student_list, name='api_student_list'),
    path('api/student-statistics/', views.api_student_statistics, name='api_student_statistics'),
]
