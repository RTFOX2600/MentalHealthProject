from django.contrib.auth.models import AbstractUser
from django.db import models


class College(models.Model):
    """学院模型"""
    name = models.CharField(max_length=100, unique=True, verbose_name='学院名称')
    code = models.CharField(max_length=20, unique=True, verbose_name='学院代码')
    
    class Meta:
        verbose_name = '学院'
        verbose_name_plural = '学院'
        ordering = ['code']
    
    def __str__(self):
        return self.name


class Major(models.Model):
    """专业模型"""
    name = models.CharField(max_length=100, verbose_name='专业名称')
    code = models.CharField(max_length=20, unique=True, verbose_name='专业代码')
    college = models.ForeignKey(College, on_delete=models.CASCADE, related_name='majors', verbose_name='所属学院')
    
    class Meta:
        verbose_name = '专业'
        verbose_name_plural = '专业'
        ordering = ['code']
        unique_together = [['college', 'name']]
    
    def __str__(self):
        return f"{self.college.name} - {self.name}"


class Grade(models.Model):
    """年级模型"""
    year = models.IntegerField(unique=True, verbose_name='入学年份')
    name = models.CharField(max_length=20, verbose_name='年级名称')
    
    class Meta:
        verbose_name = '年级'
        verbose_name_plural = '年级'
        ordering = ['-year']
    
    def __str__(self):
        return self.name


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
    phone_number = models.CharField(max_length=20, verbose_name='电话号码', default='')
    
    # 学生的单一学院、专业、年级（外键关系）
    student_college = models.ForeignKey(
        College, 
        on_delete=models.SET_NULL, 
        null=True, 
        blank=True, 
        related_name='students',
        verbose_name='所属学院（学生）'
    )
    student_major = models.ForeignKey(
        Major, 
        on_delete=models.SET_NULL, 
        null=True, 
        blank=True, 
        related_name='students',
        verbose_name='所属专业（学生）'
    )
    student_grade = models.ForeignKey(
        Grade, 
        on_delete=models.SET_NULL, 
        null=True, 
        blank=True, 
        related_name='students',
        verbose_name='所属年级（学生）'
    )
    
    # 辅导员/管理员负责的多个学院、专业、年级（多对多关系）
    managed_colleges = models.ManyToManyField(
        College,
        blank=True,
        related_name='managers',
        verbose_name='负责学院（辅导员/管理员）'
    )
    managed_majors = models.ManyToManyField(
        Major,
        blank=True,
        related_name='managers',
        verbose_name='负责专业（辅导员/管理员）'
    )
    managed_grades = models.ManyToManyField(
        Grade,
        blank=True,
        related_name='managers',
        verbose_name='负责年级（辅导员/管理员）'
    )

    def __str__(self):
        return self.username
    
    @property
    def role_display(self):
        """返回角色的中文显示"""
        return dict(self.ROLE_CHOICES).get(self.role, '未知')


class ProfileChangeRequest(models.Model):
    """个人信息变更申请模型"""
    STATUS_CHOICES = [
        ('pending', '待审核'),
        ('approved', '已通过'),
        ('rejected', '已拒绝'),
    ]
    
    CHANGE_TYPE_CHOICES = [
        ('role_change', '角色变更'),
        ('student_info', '学生信息变更'),
        ('manager_info', '辅导员/管理员信息变更'),
    ]
    
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name='profile_change_requests', verbose_name='申请用户')
    change_type = models.CharField(max_length=20, choices=CHANGE_TYPE_CHOICES, verbose_name='变更类型')
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='pending', verbose_name='审核状态')
    
    # 角色变更申请
    requested_role = models.CharField(
        max_length=20,
        choices=User.ROLE_CHOICES,
        blank=True,
        null=True,
        verbose_name='申请变更的角色'
    )
    
    # 学生申请变更的学院、专业、年级
    requested_student_college = models.ForeignKey(
        College, 
        on_delete=models.SET_NULL, 
        null=True, 
        blank=True, 
        related_name='student_change_requests',
        verbose_name='申请变更的学院（学生）'
    )
    requested_student_major = models.ForeignKey(
        Major, 
        on_delete=models.SET_NULL, 
        null=True, 
        blank=True, 
        related_name='student_change_requests',
        verbose_name='申请变更的专业（学生）'
    )
    requested_student_grade = models.ForeignKey(
        Grade, 
        on_delete=models.SET_NULL, 
        null=True, 
        blank=True, 
        related_name='student_change_requests',
        verbose_name='申请变更的年级（学生）'
    )
    
    # 辅导员/管理员申请变更的学院、专业、年级（存储为JSON字符串）
    requested_managed_colleges = models.TextField(blank=True, default='', verbose_name='申请负责的学院ID列表（JSON）')
    requested_managed_majors = models.TextField(blank=True, default='', verbose_name='申请负责的专业ID列表（JSON）')
    requested_managed_grades = models.TextField(blank=True, default='', verbose_name='申请负责的年级ID列表（JSON）')
    
    # 审核相关字段
    created_at = models.DateTimeField(auto_now_add=True, verbose_name='申请时间')
    reviewed_at = models.DateTimeField(null=True, blank=True, verbose_name='审核时间')
    reviewed_by = models.ForeignKey(
        User, 
        on_delete=models.SET_NULL, 
        null=True, 
        blank=True, 
        related_name='reviewed_requests',
        verbose_name='审核人'
    )
    review_comment = models.TextField(blank=True, default='', verbose_name='审核意见')
    
    class Meta:
        verbose_name = '信息变更申请'
        verbose_name_plural = '信息变更申请'
        ordering = ['-created_at']
    
    def __str__(self):
        return f"{self.user.username} - {self.get_change_type_display()} - {self.get_status_display()}"

