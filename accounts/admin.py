from django.contrib import admin
from django.contrib.auth.admin import UserAdmin
from django.utils.html import format_html
from .models import User


class CustomUserAdmin(UserAdmin):
    model = User
    list_display = ['username', 'email', 'role', 'requested_role_status', 'phone_number', 'is_staff']
    list_filter = ['role', 'requested_role', 'is_staff', 'is_superuser']
    fieldsets = (
        (None, {'fields': ('username', 'password')}),
        ('个人信息', {'fields': ('last_name', 'first_name', 'email', 'role', 'phone_number')}),
        ('请求身份', {'fields': ('requested_role',), 'description': '用户请求变更的目标身份'}),
        ('权限', {'fields': ('is_active', 'is_staff', 'is_superuser', 'groups', 'user_permissions')}),
        ('重要日期', {'fields': ('last_login', 'date_joined')}),
    )
    add_fieldsets = UserAdmin.add_fieldsets + (
        ('个人信息', {'fields': ('last_name', 'first_name', 'email', 'role', 'phone_number')}),
    )
    actions = ['approve_request', 'reject_request']
    
    def requested_role_status(self, obj):
        """显示请求身份状态"""
        if obj.requested_role:
            return format_html('<span style="color: orange;">{} → {}</span>', 
                             obj.role_display, obj.requested_role_display)
        return format_html('<span style="color: green;">{}</span>', '无请求')
    requested_role_status.short_description = '请求身份'
    
    def approve_request(self, request, queryset):
        """批量审核通过"""
        updated = 0
        for user in queryset:
            if user.requested_role:
                user.role = user.requested_role
                user.requested_role = None
                user.save()
                updated += 1
        self.message_user(request, f'已审核通过 {updated} 个用户的请求。')
    approve_request.short_description = '✔ 批准所选请求'
    
    def reject_request(self, request, queryset):
        """批量拒绝请求"""
        updated = queryset.exclude(requested_role__isnull=True).update(requested_role=None)
        self.message_user(request, f'已拒绝 {updated} 个用户的请求。', level='warning')
    reject_request.short_description = '❌ 拒绝所选请求'


admin.site.register(User, CustomUserAdmin)
