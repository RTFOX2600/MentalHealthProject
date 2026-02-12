from django.contrib import messages
from django.contrib.auth import login, logout, authenticate
from django.contrib.auth.decorators import login_required
from django.shortcuts import render, redirect

from .forms import RegisterForm, UserProfileForm, DeleteAccountForm


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
            
            # 如果选择的是非学生角色，设置为请求身份
            if selected_role != 'student':
                user.requested_role = selected_role
                user.role = 'student'  # 实际角色设为学生
                user.save()
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
                form.add_error('password', '密码错误，请重新输入。')
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
    注：任何角色变更都会设置为请求身份，需要管理员审核。
    """
    if request.method == 'POST':
        # 在处理表单之前先保存当前角色
        old_role = request.user.role
        
        form = UserProfileForm(request.POST, instance=request.user)
        if form.is_valid():
            # 从表单数据中获取新选择的角色（而不是从对象中获取）
            new_role = form.cleaned_data.get('role')
            
            # 如果角色发生变化
            if old_role != new_role:
                # 不保存角色变化，只更新其他字段
                user = form.save(commit=False)
                user.requested_role = new_role  # 设置请求身份
                user.role = old_role  # 保持原有角色不变
                user.save()
                messages.info(request, f'您的身份变更请求已提交（「{dict(user.ROLE_CHOICES).get(old_role)}」→「{dict(user.ROLE_CHOICES).get(new_role)}」），请等待管理员审核。')
                return redirect('home')
            else:
                # 角色未变化，正常保存所有字段
                form.save()
                messages.success(request, "您的个人信息已成功更新。")
                return redirect('home')
    else:
        form = UserProfileForm(instance=request.user)
    return render(request, 'accounts/profile_update.html', {'form': form})


def custom_login(request):
    """自定义登录视图，支持请求身份检查。"""
    if request.method == 'POST':
        username = request.POST.get('username')
        password = request.POST.get('password')
        
        user = authenticate(request, username=username, password=password)
        
        if user is not None:
            login(request, user)
            return redirect('home')
        else:
            # 检查是否是因为有待审核的请求
            from .models import User
            try:
                user_obj = User.objects.get(username=username)
                if user_obj.check_password(password):
                    if user_obj.needs_approval:
                        messages.warning(request, f'您有一个待审核的身份请求（「{user_obj.requested_role_display}」），请耐心等待管理员审核。您可以以当前身份登录。')
                    else:
                        messages.error(request, '用户名或密码错误。')
                else:
                    messages.error(request, '用户名或密码错误。')
            except User.DoesNotExist:
                messages.error(request, '用户名或密码错误。')
    
    from django.contrib.auth.forms import AuthenticationForm
    form = AuthenticationForm()
    return render(request, 'accounts/login.html', {'form': form})


@login_required
def cancel_request(request):
    """
    取消身份变更请求。
    
    需要登录。仅支持 POST 请求：
    - POST: 将用户的 requested_role 设为 None，取消待审核的身份请求。
    """
    if request.method == 'POST':
        user = request.user
        if user.requested_role:
            old_requested_role = user.requested_role_display
            user.requested_role = None
            user.save()
            messages.success(request, f'已取消您的「{old_requested_role}」身份变更请求。')
        else:
            messages.info(request, '您当前没有待审核的身份请求。')
    return redirect('home')
