from django.urls import path
from . import views

app_name = 'mental_health'

urlpatterns = [
    path('demo/', views.demo_page, name='demo'),
    path('upload/<str:file_type>/', views.upload_file, name='upload'),
    path('analyze/<str:analysis_type>/', views.analyze_data, name='analyze'),
]
