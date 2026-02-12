from django.contrib.auth.models import AbstractUser
from django.db import models

class User(AbstractUser):
    ROLE_CHOICES = [
        ('student', '学生'),
        ('counselor', '辅导员'),
        ('admin', '系统管理员'),
    ]
    
    role = models.CharField(
        max_length=20,
        choices=ROLE_CHOICES,
        default='student',
        verbose_name='角色'
    )
    requested_role = models.CharField(
        max_length=20,
        choices=ROLE_CHOICES,
        blank=True,
        null=True,
        verbose_name='请求身份',
        help_text='用户请求变更的目标身份，空表示无待审核请求'
    )
    phone_number = models.CharField(max_length=20, verbose_name='电话号码', default='')

    def __str__(self):
        return self.username
    
    @property
    def role_display(self):
        """返回角色的中文显示"""
        return dict(self.ROLE_CHOICES).get(self.role, '未知')
    
    @property
    def requested_role_display(self):
        """返回请求身份的中文显示"""
        if self.requested_role:
            return dict(self.ROLE_CHOICES).get(self.requested_role, '未知')
        return None
    
    @property
    def needs_approval(self):
        """判断是否有待审核的请求"""
        return self.requested_role is not None and self.requested_role != ''

