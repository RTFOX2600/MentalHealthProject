from django.contrib import messages
from django.contrib.auth import login, logout
from django.contrib.auth.decorators import login_required
from django.shortcuts import render, redirect

from .forms import RegisterForm, UserProfileForm, DeleteAccountForm


def register(request):
    """
    用户注册接口。
    
    支持 GET 和 POST 请求：
    - GET: 返回注册页面。
    - POST: 提交注册表单，验证成功后保存用户并自动登录，跳转至首页。
    """
    if request.method == 'POST':
        form = RegisterForm(request.POST)
        if form.is_valid():
            user = form.save()
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
    """
    if request.method == 'POST':
        form = UserProfileForm(request.POST, instance=request.user)
        if form.is_valid():
            form.save()
            messages.success(request, "您的个人信息已成功更新。")
            return redirect('home')
    else:
        form = UserProfileForm(instance=request.user)
    return render(request, 'accounts/profile_update.html', {'form': form})
