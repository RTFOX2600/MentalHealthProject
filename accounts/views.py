from django.contrib import messages
from django.contrib.auth import login, logout, authenticate
from django.contrib.auth.decorators import login_required
from django.contrib.auth.views import PasswordChangeView, LogoutView
from django.shortcuts import render, redirect
from django.urls import reverse_lazy
from django.http import JsonResponse
import json

from .forms import RegisterForm, UserProfileForm, OrganizationInfoForm, DeleteAccountForm
from .models import ProfileChangeRequest, Major


def register(request):
    """
    用户注册接口。
    
    支持 GET 和 POST 请求：
    - GET: 返回注册页面。
    - POST: 提交注册表单，验证成功后保存用户并自动登录，跳转至首页。
    注：如果选择非学生角色，将设置为请求身份，实际角色为学生，等待审核。
    """
    if request.method == 'POST':
        form = RegisterForm(request.POST)
        if form.is_valid():
            user = form.save(commit=False)
            selected_role = user.role
            
            # 如果选择的是非学生角色，创建角色变更请求
            if selected_role != 'student':
                user.role = 'student'  # 实际角色设为学生
                user.save()
                
                # 创建角色变更请求
                ProfileChangeRequest.objects.create(
                    user=user,
                    change_type='role_change',
                    requested_role=selected_role
                )
                
                login(request, user)  # 以学生身份登录
                messages.info(request, f'您的账号已创建，当前以「学生」身份登录。您的「{dict(user.ROLE_CHOICES).get(selected_role)}」身份请求正在等待管理员审核。')
                return redirect('home')
            else:
                # 选择学生角色，直接登录
                user.save()
                login(request, user)
                return redirect('home')
    else:
        form = RegisterForm()
    return render(request, 'accounts/register.html', {'form': form})


@login_required
def delete_account(request):
    """
    用户注销账号接口。
    
    需要登录。支持 GET 和 POST 请求：
    - GET: 返回注销确认页面。
    - POST: 提交注销表单，验证密码正确后执行注销逻辑，删除用户并重定向至首页。
    """
    if request.method == 'POST':
        form = DeleteAccountForm(request.POST)
        if form.is_valid():
            password = form.cleaned_data.get('password')
            user = request.user
            if user.check_password(password):
                logout(request)
                user.delete()
                messages.success(request, "您的账号已成功注销。")
                return redirect('home')
            else:
                messages.error(request, '密码错误，请重新输入。')
        else:
            # 将表单错误转换为消息提示
            for field, errors in form.errors.items():
                for error in errors:
                    messages.error(request, error)
    else:
        form = DeleteAccountForm()
    return render(request, 'accounts/delete_account_confirm.html', {'form': form})


@login_required
def profile_update(request):
    """
    更新用户信息接口。
    
    需要登录。支持 GET 和 POST 请求：
    - GET: 返回个人信息修改页面，表单预填当前用户信息。
    - POST: 提交修改后的用户信息，验证通过后保存并重定向至首页。
    注：任何角色变更都会创建变更请求，需要管理员审核。
    注：学院、专业、年级信息的修改需要管理员审核。
    """
    if request.method == 'POST':
        # ✅ 保存原始基本信息值
        old_role = request.user.role
        original_first_name = request.user.first_name
        original_last_name = request.user.last_name
        original_email = request.user.email
        original_phone_number = request.user.phone_number
            
        # ✅ 保存原始组织信息值
        original_college_id, original_major_id, original_grade_id = None, None, None
        original_colleges, original_majors, original_grades = set(), set(), set()
            
        if request.user.role == 'student':
            original_college_id = request.user.student_college.id if request.user.student_college else None
            original_major_id = request.user.student_major.id if request.user.student_major else None
            original_grade_id = request.user.student_grade.id if request.user.student_grade else None
        elif request.user.role in ['counselor', 'admin']:
            original_colleges = set(request.user.managed_colleges.all())
            original_majors = set(request.user.managed_majors.all())
            original_grades = set(request.user.managed_grades.all())
            
        # 创建表单实例
        basic_form = UserProfileForm(request.POST, instance=request.user)
        org_form = OrganizationInfoForm(request.POST, instance=request.user)
            
        # 验证表单
        if basic_form.is_valid() and org_form.is_valid():
            new_role = basic_form.cleaned_data.get('role')
                
            # ✅ 步骤 1：检测所有变更类型
            role_changed = (old_role != new_role)
            basic_info_changed = False
            org_info_changed = False
            change_type = None
                            
            # 检测基本信息变更
            if (basic_form.cleaned_data.get('first_name') != original_first_name or
                basic_form.cleaned_data.get('last_name') != original_last_name or
                basic_form.cleaned_data.get('email') != original_email or
                basic_form.cleaned_data.get('phone_number') != original_phone_number):
                basic_info_changed = True
                            
            # 检测组织信息变更
            if request.user.role == 'student':
                new_college = org_form.cleaned_data.get('student_college')
                new_major = org_form.cleaned_data.get('student_major')
                new_grade = org_form.cleaned_data.get('student_grade')
                                
                new_college_id = new_college.id if new_college else None
                new_major_id = new_major.id if new_major else None
                new_grade_id = new_grade.id if new_grade else None
                                
                if (original_college_id != new_college_id or
                    original_major_id != new_major_id or
                    original_grade_id != new_grade_id):
                    org_info_changed = True
                    change_type = 'student_info'
            elif request.user.role in ['counselor', 'admin']:
                new_colleges = set(org_form.cleaned_data.get('managed_colleges', []))
                new_majors = set(org_form.cleaned_data.get('managed_majors', []))
                new_grades = set(org_form.cleaned_data.get('managed_grades', []))
                                
                if (original_colleges != new_colleges or
                    original_majors != new_majors or
                    original_grades != new_grades):
                    org_info_changed = True
                    change_type = 'manager_info'
                            
            # ✅ 步骤 2：独立处理每个变更（不互相阻断）
            messages_list = []
                        
            # 处理基本信息变更
            if basic_info_changed:
                user = basic_form.save(commit=False)
                user.save(update_fields=['first_name', 'last_name', 'email', 'phone_number'])
                messages_list.append(('基本信息已成功更新。', 'success'))
                        
            # 处理角色变更
            if role_changed:
                ProfileChangeRequest.objects.create(
                    user=request.user,
                    change_type='role_change',
                    requested_role=new_role
                )
                messages_list.append((f'您的身份变更请求已提交（「{dict(request.user.ROLE_CHOICES).get(old_role)}」→「{dict(request.user.ROLE_CHOICES).get(new_role)}」），请等待管理员审核。', 'info'))
                        
            # 处理组织信息变更
            if org_info_changed:
                _create_profile_change_request(request.user, change_type, org_form)
                messages_list.append(('您的组织信息变更请求已提交，请等待管理员审核。', 'info'))
                        
            # 显示所有消息
            if messages_list:
                for msg, level in messages_list:
                    if level == 'success':
                        messages.success(request, msg)
                    elif level == 'info':
                        messages.info(request, msg)
                    elif level == 'warning':
                        messages.warning(request, msg)
            else:
                messages.info(request, '信息未发生变化。')
                        
            return redirect('profile_update')
    else:
        basic_form = UserProfileForm(instance=request.user)
        org_form = OrganizationInfoForm(instance=request.user)
    return render(request, 'accounts/profile_update.html', {'basic_form': basic_form, 'org_form': org_form})


def _create_profile_change_request(user, change_type, form):
    """创建个人信息变更审核请求"""
    change_request = ProfileChangeRequest(
        user=user,
        change_type=change_type
    )
    
    if change_type == 'student_info':
        change_request.requested_student_college = form.cleaned_data.get('student_college')
        change_request.requested_student_major = form.cleaned_data.get('student_major')
        change_request.requested_student_grade = form.cleaned_data.get('student_grade')
    else:  # manager_info
        # 将多对多关系ID存储为JSON
        managed_colleges = form.cleaned_data.get('managed_colleges', [])
        managed_majors = form.cleaned_data.get('managed_majors', [])
        managed_grades = form.cleaned_data.get('managed_grades', [])
        
        change_request.requested_managed_colleges = json.dumps([c.id for c in managed_colleges])
        change_request.requested_managed_majors = json.dumps([m.id for m in managed_majors])
        change_request.requested_managed_grades = json.dumps([g.id for g in managed_grades])
    
    change_request.save()


def custom_login(request):
    """自定义登录视图，支持请求身份检查。"""
    if request.method == 'POST':
        username = request.POST.get('username')
        password = request.POST.get('password')
        
        user = authenticate(request, username=username, password=password)
        
        if user is not None:
            login(request, user)
            
            # 检查是否有待审核的角色变更请求
            pending_role_request = ProfileChangeRequest.objects.filter(
                user=user,
                change_type='role_change',
                status='pending'
            ).first()
            
            if pending_role_request:
                role_choices = dict(user.ROLE_CHOICES)
                requested_role_display = role_choices.get(pending_role_request.requested_role, '未知')
                messages.warning(request, f'您有一个待审核的身份请求（「{requested_role_display}」），请耐心等待管理员审核。您可以以当前身份登录。')
            
            return redirect('home')
        else:
            messages.error(request, '用户名或密码错误。')
    
    from django.contrib.auth.forms import AuthenticationForm
    form = AuthenticationForm()
    return render(request, 'accounts/login.html', {'form': form})


@login_required
def cancel_request(request):
    """
    取消用户的所有待审核请求。
    
    需要登录。仅支持 POST 请求：
    - POST: 取消所有待审核的变更请求。
    """
    if request.method == 'POST':
        # 查找所有待审核的请求
        pending_requests = ProfileChangeRequest.objects.filter(
            user=request.user,
            status='pending'
        )
        
        if pending_requests.exists():
            count = pending_requests.count()
            pending_requests.delete()
            messages.success(request, f'已取消您的 {count} 个待审核请求。')
        else:
            messages.info(request, '您当前没有待审核的请求。')
    return redirect('home')


class CustomPasswordChangeView(PasswordChangeView):
    """自定义密码修改视图，添加成功消息和错误提示。"""
    template_name = 'accounts/password_change.html'
    success_url = reverse_lazy('home')
    
    def form_valid(self, form):
        messages.success(self.request, '您的密码已成功修改。')
        return super().form_valid(form)
    
    def form_invalid(self, form):
        # 将表单错误转换为消息提示
        for field, errors in form.errors.items():
            for error in errors:
                if field == '__all__':
                    messages.error(self.request, error)
                else:
                    field_name = form.fields[field].label or field
                    messages.error(self.request, f'{field_name}: {error}')
        return super().form_invalid(form)


class CustomLogoutView(LogoutView):
    """自定义退出视图，添加退出消息。"""
    next_page = 'login'
    
    def dispatch(self, request, *args, **kwargs):
        messages.success(request, '您已成功退出登录。')
        return super().dispatch(request, *args, **kwargs)


@login_required
def get_majors_by_college(request, college_id):
    """
    获取指定学院的专业列表（API接口）
    
    参数：
        college_id: 学院ID
    
    返回：
        JSON格式的专业列表：[{"id": 1, "name": "专业名称"}, ...]
    """
    try:
        majors = Major.objects.filter(college_id=college_id).values('id', 'name')
        return JsonResponse({
            'success': True,
            'majors': list(majors)
        })
    except Exception as e:
        return JsonResponse({
            'success': False,
            'error': str(e)
        }, status=400)
