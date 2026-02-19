from django.contrib import admin
from django.contrib.auth.admin import UserAdmin
from django.utils.html import format_html
from django.utils import timezone
import json
from .models import User, College, Major, Grade, ProfileChangeRequest


class CustomUserAdmin(UserAdmin):
    model = User
    list_display = ['username', 'get_full_name_display', 'email', 'role', 'get_organization_info', 'phone_number', 'is_staff']
    list_filter = ['role', 'student_college', 'student_major', 'student_grade', 'is_staff', 'is_superuser']
    fieldsets = (
        (None, {'fields': ('username', 'password')}),
        ('个人信息', {'fields': ('last_name', 'first_name', 'email', 'role', 'phone_number')}),
        ('学生组织信息', {'fields': ('student_college', 'student_major', 'student_grade'), 'description': '学生所属的学院、专业、年级'}),
        ('管理组组织信息', {'fields': ('managed_colleges', 'managed_majors', 'managed_grades'), 'description': '辅导员/管理员负责的学院、专业、年级'}),
        ('权限', {'fields': ('is_active', 'is_staff', 'is_superuser', 'groups', 'user_permissions')}),
        ('重要日期', {'fields': ('last_login', 'date_joined')}),
    )
    add_fieldsets = UserAdmin.add_fieldsets + (
        ('个人信息', {'fields': ('last_name', 'first_name', 'email', 'role', 'phone_number')}),
        ('学生组织信息', {'fields': ('student_college', 'student_major', 'student_grade')}),
    )
    filter_horizontal = ('managed_colleges', 'managed_majors', 'managed_grades', 'groups', 'user_permissions')
    actions = []
    
    def get_full_name_display(self, obj):
        """显示完整姓名"""
        full_name = f"{obj.last_name}{obj.first_name}".strip()
        if full_name:
            return full_name
        return '-'
    get_full_name_display.short_description = '姓名'
    
    def get_organization_info(self, obj):
        """显示组织信息"""
        if obj.role == 'student':
            if obj.student_college or obj.student_major or obj.student_grade:
                info = []
                if obj.student_college:
                    info.append(obj.student_college.name)
                if obj.student_major:
                    info.append(obj.student_major.name)
                if obj.student_grade:
                    info.append(obj.student_grade.name)
                return ' / '.join(info)
        else:
            colleges_count = obj.managed_colleges.count()
            majors_count = obj.managed_majors.count()
            grades_count = obj.managed_grades.count()
            if colleges_count or majors_count or grades_count:
                return f'负责 {colleges_count}学院/{majors_count}专业/{grades_count}年级'
        return '-'
    get_organization_info.short_description = '组织信息'


@admin.register(College)
class CollegeAdmin(admin.ModelAdmin):
    list_display = ['code', 'name']
    search_fields = ['name', 'code']
    ordering = ['code']


@admin.register(Major)
class MajorAdmin(admin.ModelAdmin):
    list_display = ['code', 'name', 'college']
    list_filter = ['college']
    search_fields = ['name', 'code']
    ordering = ['code']


@admin.register(Grade)
class GradeAdmin(admin.ModelAdmin):
    list_display = ['year', 'name']
    search_fields = ['name', 'year']
    ordering = ['-year']


@admin.register(ProfileChangeRequest)
class ProfileChangeRequestAdmin(admin.ModelAdmin):
    list_display = ['get_user_display', 'change_type', 'status', 'get_change_summary', 'created_at', 'reviewed_by']
    list_filter = ['status', 'change_type', 'created_at']
    search_fields = ['user__username', 'user__last_name', 'user__first_name', 'user__email']
    readonly_fields = ['user', 'change_type', 'created_at', 'get_current_info', 'get_requested_info']
    actions = ['approve_change', 'reject_change']
    ordering = ['-created_at']
    
    fieldsets = (
        ('申请信息', {
            'fields': ('user', 'change_type', 'status', 'created_at')
        }),
        ('当前信息', {
            'fields': ('get_current_info',),
            'description': '用户当前的组织信息'
        }),
        ('申请变更信息', {
            'fields': ('get_requested_info',),
            'description': '用户申请变更的组织信息'
        }),
        ('审核信息', {
            'fields': ('reviewed_at', 'reviewed_by', 'review_comment')
        }),
    )
    
    def get_user_display(self, obj):
        """显示用户名和姓名"""
        full_name = f"{obj.user.last_name}{obj.user.first_name}".strip()
        if full_name:
            return f"{full_name} ({obj.user.username})"
        return obj.user.username
    get_user_display.short_description = '用户'
    
    def get_change_summary(self, obj):
        """显示变更摘要"""
        if obj.change_type == 'role_change':
            role_choices = dict(User.ROLE_CHOICES)
            current_role = role_choices.get(obj.user.role, '未知')
            requested_role = role_choices.get(obj.requested_role, '未知')
            return f"{current_role} → {requested_role}"
        elif obj.change_type == 'student_info':
            parts = []
            if obj.requested_student_college:
                parts.append(f"学院→{obj.requested_student_college.name}")
            if obj.requested_student_major:
                parts.append(f"专业→{obj.requested_student_major.name}")
            if obj.requested_student_grade:
                parts.append(f"年级→{obj.requested_student_grade.name}")
            return ' | '.join(parts) if parts else '-'
        else:
            parts = []
            if obj.requested_managed_colleges:
                try:
                    college_ids = json.loads(obj.requested_managed_colleges)
                    parts.append(f"学院×{len(college_ids)}")
                except:
                    pass
            if obj.requested_managed_majors:
                try:
                    major_ids = json.loads(obj.requested_managed_majors)
                    parts.append(f"专业×{len(major_ids)}")
                except:
                    pass
            if obj.requested_managed_grades:
                try:
                    grade_ids = json.loads(obj.requested_managed_grades)
                    parts.append(f"年级×{len(grade_ids)}")
                except:
                    pass
            return ' | '.join(parts) if parts else '-'
    get_change_summary.short_description = '变更摘要'
    
    def get_current_info(self, obj):
        """显示当前信息"""
        user = obj.user
        if obj.change_type == 'role_change':
            role_choices = dict(User.ROLE_CHOICES)
            return f"当前角色: {role_choices.get(user.role, '未知')}"
        elif obj.change_type == 'student_info':
            current = []
            if user.student_college:
                current.append(f"学院: {user.student_college.name}")
            if user.student_major:
                current.append(f"专业: {user.student_major.name}")
            if user.student_grade:
                current.append(f"年级: {user.student_grade.name}")
            return '\n'.join(current) if current else '未设置'
        else:
            current = []
            colleges = list(user.managed_colleges.all())
            if colleges:
                current.append(f"负责学院: {', '.join([c.name for c in colleges])}")
            majors = list(user.managed_majors.all())
            if majors:
                current.append(f"负责专业: {', '.join([m.name for m in majors])}")
            grades = list(user.managed_grades.all())
            if grades:
                current.append(f"负责年级: {', '.join([g.name for g in grades])}")
            return '\n'.join(current) if current else '未设置'
    get_current_info.short_description = '当前信息'
    
    def get_requested_info(self, obj):
        """显示申请信息"""
        if obj.change_type == 'role_change':
            role_choices = dict(User.ROLE_CHOICES)
            return f"申请角色: {role_choices.get(obj.requested_role, '未知')}"
        elif obj.change_type == 'student_info':
            requested = []
            if obj.requested_student_college:
                requested.append(f"学院: {obj.requested_student_college.name}")
            if obj.requested_student_major:
                requested.append(f"专业: {obj.requested_student_major.name}")
            if obj.requested_student_grade:
                requested.append(f"年级: {obj.requested_student_grade.name}")
            return '\n'.join(requested) if requested else '未设置'
        else:
            requested = []
            if obj.requested_managed_colleges:
                try:
                    college_ids = json.loads(obj.requested_managed_colleges)
                    colleges = College.objects.filter(id__in=college_ids)
                    requested.append(f"负责学院: {', '.join([c.name for c in colleges])}")
                except:
                    pass
            if obj.requested_managed_majors:
                try:
                    major_ids = json.loads(obj.requested_managed_majors)
                    majors = Major.objects.filter(id__in=major_ids)
                    requested.append(f"负责专业: {', '.join([m.name for m in majors])}")
                except:
                    pass
            if obj.requested_managed_grades:
                try:
                    grade_ids = json.loads(obj.requested_managed_grades)
                    grades = Grade.objects.filter(id__in=grade_ids)
                    requested.append(f"负责年级: {', '.join([g.name for g in grades])}")
                except:
                    pass
            return '\n'.join(requested) if requested else '未设置'
    get_requested_info.short_description = '申请变更信息'
    
    def approve_change(self, request, queryset):
        """批量审核通过"""
        updated = 0
        for change_request in queryset.filter(status='pending'):
            user = change_request.user
            
            if change_request.change_type == 'role_change':
                # 更新角色
                if change_request.requested_role:
                    user.role = change_request.requested_role
                    user.save()
            elif change_request.change_type == 'student_info':
                # 更新学生信息
                if change_request.requested_student_college:
                    user.student_college = change_request.requested_student_college
                if change_request.requested_student_major:
                    user.student_major = change_request.requested_student_major
                if change_request.requested_student_grade:
                    user.student_grade = change_request.requested_student_grade
                user.save()
            else:
                # 更新辅导员/管理员信息
                if change_request.requested_managed_colleges:
                    try:
                        college_ids = json.loads(change_request.requested_managed_colleges)
                        user.managed_colleges.set(college_ids)
                    except:
                        pass
                if change_request.requested_managed_majors:
                    try:
                        major_ids = json.loads(change_request.requested_managed_majors)
                        user.managed_majors.set(major_ids)
                    except:
                        pass
                if change_request.requested_managed_grades:
                    try:
                        grade_ids = json.loads(change_request.requested_managed_grades)
                        user.managed_grades.set(grade_ids)
                    except:
                        pass
            
            change_request.status = 'approved'
            change_request.reviewed_at = timezone.now()
            change_request.reviewed_by = request.user
            change_request.save()
            updated += 1
        
        self.message_user(request, f'已审核通过 {updated} 个变更申请。')
    approve_change.short_description = '✔ 批准所选申请'
    
    def reject_change(self, request, queryset):
        """批量拒绝申请"""
        updated = 0
        for change_request in queryset.filter(status='pending'):
            change_request.status = 'rejected'
            change_request.reviewed_at = timezone.now()
            change_request.reviewed_by = request.user
            change_request.save()
            updated += 1
        
        self.message_user(request, f'已拒绝 {updated} 个变更申请。', level='warning')
    reject_change.short_description = '❌ 拒绝所选申请'


admin.site.register(User, CustomUserAdmin)
