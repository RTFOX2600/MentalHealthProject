from django import forms
from django.contrib.auth.forms import UserCreationForm
from .models import User, College, Major, Grade

class RegisterForm(UserCreationForm):
    last_name = forms.CharField(label='姓', required=True)
    first_name = forms.CharField(label='名', required=True)
    role = forms.ChoiceField(
        label='角色',
        choices=User.ROLE_CHOICES,
        required=True,
        widget=forms.Select(attrs={'class': 'form-control'})
    )
    email = forms.EmailField(label='电子邮箱', required=True)
    phone_number = forms.CharField(label='电话号码', required=True)

    class Meta(UserCreationForm.Meta):
        model = User
        fields = UserCreationForm.Meta.fields + ('last_name', 'first_name', 'role', 'email', 'phone_number')

class UserProfileForm(forms.ModelForm):
    """基本信息表单（姓名、角色、邮箱、电话）"""
    class Meta:
        model = User
        fields = ['last_name', 'first_name', 'role', 'email', 'phone_number']
        widgets = {
            'role': forms.Select(attrs={'class': 'form-control'})
        }

class OrganizationInfoForm(forms.ModelForm):
    """组织信息表单（学院、专业、年级）"""
    # 学生组织信息
    student_college = forms.ModelChoiceField(
        queryset=College.objects.all(),
        required=False,
        label='所属学院',
        widget=forms.Select(attrs={'class': 'form-control'}),
        help_text='仅限学生填写'
    )
    student_major = forms.ModelChoiceField(
        queryset=Major.objects.all(),
        required=False,
        label='所属专业',
        widget=forms.Select(attrs={'class': 'form-control'}),
        help_text='仅限学生填写'
    )
    student_grade = forms.ModelChoiceField(
        queryset=Grade.objects.all(),
        required=False,
        label='所属年级',
        widget=forms.Select(attrs={'class': 'form-control'}),
        help_text='仅限学生填写'
    )
    
    # 辅导员/管理员组织信息
    managed_colleges = forms.ModelMultipleChoiceField(
        queryset=College.objects.all(),
        required=False,
        label='负责学院',
        widget=forms.CheckboxSelectMultiple(),
        help_text='仅限辅导员/管理员填写，可多选'
    )
    managed_majors = forms.ModelMultipleChoiceField(
        queryset=Major.objects.all(),
        required=False,
        label='负责专业',
        widget=forms.CheckboxSelectMultiple(),
        help_text='仅限辅导员/管理员填写，可多选'
    )
    managed_grades = forms.ModelMultipleChoiceField(
        queryset=Grade.objects.all(),
        required=False,
        label='负责年级',
        widget=forms.CheckboxSelectMultiple(),
        help_text='仅限辅导员/管理员填写，可多选'
    )
    
    class Meta:
        model = User
        fields = [
            'student_college', 'student_major', 'student_grade',
            'managed_colleges', 'managed_majors', 'managed_grades'
        ]

class DeleteAccountForm(forms.Form):
    password = forms.CharField(
        label='确认密码',
        widget=forms.PasswordInput,
        help_text='为了您的账号安全，请在注销前输入登录密码进行确认。'
    )
