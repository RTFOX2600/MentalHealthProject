from django import forms
from django.contrib.auth.forms import UserCreationForm
from .models import User

class RegisterForm(UserCreationForm):
    last_name = forms.CharField(label='姓', required=True)
    first_name = forms.CharField(label='名', required=True)
    position = forms.CharField(label='职位', required=True)
    email = forms.EmailField(label='电子邮箱', required=True)
    phone_number = forms.CharField(label='电话号码', required=True)

    class Meta(UserCreationForm.Meta):
        model = User
        fields = UserCreationForm.Meta.fields + ('last_name', 'first_name', 'position', 'email', 'phone_number')

class UserProfileForm(forms.ModelForm):
    class Meta:
        model = User
        fields = ['last_name', 'first_name', 'position', 'email', 'phone_number']

class DeleteAccountForm(forms.Form):
    password = forms.CharField(
        label='确认密码',
        widget=forms.PasswordInput,
        help_text='为了您的账号安全，请在注销前输入登录密码进行确认。'
    )
