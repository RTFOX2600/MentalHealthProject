from django.urls import path
from . import views

app_name = 'mental_health'

urlpatterns = [
    path('demo/', views.demo_page, name='demo'),
]
