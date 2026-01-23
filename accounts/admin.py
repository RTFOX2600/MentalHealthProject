from django.contrib import admin
from django.contrib.auth.admin import UserAdmin
from .models import User


class CustomUserAdmin(UserAdmin):
    model = User
    list_display = ['username', 'email', 'position', 'phone_number', 'is_staff']
    fieldsets = (
        (None, {'fields': ('username', 'password')}),
        ('个人信息', {'fields': ('last_name', 'first_name', 'email', 'position', 'phone_number')}),
        ('权限', {'fields': ('is_active', 'is_staff', 'is_superuser', 'groups', 'user_permissions')}),
        ('重要日期', {'fields': ('last_login', 'date_joined')}),
    )
    add_fieldsets = UserAdmin.add_fieldsets + (
        ('个人信息', {'fields': ('last_name', 'first_name', 'email', 'position', 'phone_number')}),
    )


admin.site.register(User, CustomUserAdmin)
