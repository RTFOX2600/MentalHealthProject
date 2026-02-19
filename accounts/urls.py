from django.urls import path
from . import views

urlpatterns = [
    path('login/', views.custom_login, name='login'),
    path('logout/', views.CustomLogoutView.as_view(), name='logout'),
    path('register/', views.register, name='register'),
    path('password-change/', views.CustomPasswordChangeView.as_view(), name='password_change'),
    path('delete-account/', views.delete_account, name='delete_account'),
    path('profile/', views.profile_update, name='profile_update'),
    path('cancel-request/', views.cancel_request, name='cancel_request'),
    path('api/majors/<int:college_id>/', views.get_majors_by_college, name='get_majors_by_college'),
]
