from django.db import models
from accounts.models import College, Major, Grade


class Student(models.Model):
    """学生基本信息模型（非用户）"""
    name = models.CharField(max_length=100, verbose_name='姓名')
    student_id = models.CharField(max_length=20, unique=True, verbose_name='学号', db_index=True)
    college = models.ForeignKey(
        College,
        on_delete=models.PROTECT,
        related_name='data_students',
        verbose_name='学院',
        db_index=True
    )
    major = models.ForeignKey(
        Major,
        on_delete=models.PROTECT,
        related_name='data_students',
        verbose_name='专业',
        db_index=True
    )
    grade = models.ForeignKey(
        Grade,
        on_delete=models.PROTECT,
        related_name='data_students',
        verbose_name='年级',
        db_index=True
    )
    
    class Meta:
        verbose_name = '学生'
        verbose_name_plural = '学生'
        ordering = ['student_id']
        indexes = [
            models.Index(fields=['college', 'major', 'grade']),
            models.Index(fields=['college', 'grade']),
            models.Index(fields=['major', 'grade']),
        ]
    
    def __str__(self):
        return f"{self.name}({self.student_id})"


class CanteenConsumptionRecord(models.Model):
    """食堂消费记录"""
    student = models.ForeignKey(
        Student,
        on_delete=models.CASCADE,
        related_name='canteen_records',
        verbose_name='学生',
        db_index=True
    )
    month = models.CharField(max_length=7, verbose_name='月份', db_index=True, help_text='格式：2025-02')
    amount = models.DecimalField(max_digits=10, decimal_places=2, verbose_name='消费金额')
    
    class Meta:
        verbose_name = '食堂消费记录'
        verbose_name_plural = '食堂消费记录'
        ordering = ['-month', 'student__student_id']
        indexes = [
            models.Index(fields=['student', 'month']),
            models.Index(fields=['month', 'amount']),
            models.Index(fields=['-amount']),
        ]
        unique_together = [['student', 'month']]
    
    def __str__(self):
        return f"{self.student.student_id} - {self.month} - ¥{self.amount}"


class SchoolGateAccessRecord(models.Model):
    """校门门禁记录"""
    DIRECTION_CHOICES = [
        ('in', '进'),
        ('out', '出'),
    ]
    
    student = models.ForeignKey(
        Student,
        on_delete=models.CASCADE,
        related_name='gate_records',
        verbose_name='学生',
        db_index=True
    )
    timestamp = models.DateTimeField(verbose_name='时间', db_index=True)
    gate_location = models.CharField(max_length=50, verbose_name='校门位置', db_index=True)
    direction = models.CharField(max_length=3, choices=DIRECTION_CHOICES, verbose_name='进出方向', db_index=True)
    
    class Meta:
        verbose_name = '校门门禁记录'
        verbose_name_plural = '校门门禁记录'
        ordering = ['-timestamp']
        indexes = [
            models.Index(fields=['student', 'timestamp']),
            models.Index(fields=['student', '-timestamp']),
            models.Index(fields=['timestamp', 'direction']),
            models.Index(fields=['gate_location', 'timestamp']),
        ]
    
    def __str__(self):
        return f"{self.student.student_id} - {self.gate_location} - {self.get_direction_display()}"


class DormitoryAccessRecord(models.Model):
    """寝室门禁记录"""
    DIRECTION_CHOICES = [
        ('in', '进'),
        ('out', '出'),
    ]
    
    student = models.ForeignKey(
        Student,
        on_delete=models.CASCADE,
        related_name='dorm_records',
        verbose_name='学生',
        db_index=True
    )
    timestamp = models.DateTimeField(verbose_name='时间', db_index=True)
    building = models.CharField(max_length=50, verbose_name='寝室楼栋', db_index=True)
    direction = models.CharField(max_length=3, choices=DIRECTION_CHOICES, verbose_name='进出方向', db_index=True)
    
    class Meta:
        verbose_name = '寝室门禁记录'
        verbose_name_plural = '寝室门禁记录'
        ordering = ['-timestamp']
        indexes = [
            models.Index(fields=['student', 'timestamp']),
            models.Index(fields=['student', '-timestamp']),
            models.Index(fields=['timestamp', 'direction']),
            models.Index(fields=['building', 'timestamp']),
        ]
    
    def __str__(self):
        return f"{self.student.student_id} - {self.building} - {self.get_direction_display()}"


class NetworkAccessRecord(models.Model):
    """网络访问记录"""
    student = models.ForeignKey(
        Student,
        on_delete=models.CASCADE,
        related_name='network_records',
        verbose_name='学生',
        db_index=True
    )
    start_time = models.DateTimeField(verbose_name='开始时间', db_index=True)
    end_time = models.DateTimeField(verbose_name='结束时间', db_index=True)
    use_vpn = models.BooleanField(verbose_name='是否使用VPN', db_index=True)
    
    class Meta:
        verbose_name = '网络访问记录'
        verbose_name_plural = '网络访问记录'
        ordering = ['-start_time']
        indexes = [
            models.Index(fields=['student', 'start_time']),
            models.Index(fields=['student', '-start_time']),
            models.Index(fields=['start_time', 'end_time']),
            models.Index(fields=['use_vpn', 'start_time']),
        ]
    
    def __str__(self):
        vpn_status = 'VPN' if self.use_vpn else '无VPN'
        return f"{self.student.student_id} - {self.start_time} - {vpn_status}"


class AcademicRecord(models.Model):
    """各科成绩记录"""
    student = models.ForeignKey(
        Student,
        on_delete=models.CASCADE,
        related_name='academic_records',
        verbose_name='学生',
        db_index=True
    )
    month = models.CharField(max_length=7, verbose_name='月份', db_index=True, help_text='格式：2025-02')
    average_score = models.DecimalField(max_digits=5, decimal_places=2, verbose_name='平均成绩')
    
    class Meta:
        verbose_name = '成绩记录'
        verbose_name_plural = '成绩记录'
        ordering = ['-month', 'student__student_id']
        indexes = [
            models.Index(fields=['student', 'month']),
            models.Index(fields=['month', 'average_score']),
            models.Index(fields=['-average_score']),
        ]
        unique_together = [['student', 'month']]
    
    def __str__(self):
        return f"{self.student.student_id} - {self.month} - {self.average_score}"


class DataStatistics(models.Model):
    """数据统计模型 - 存储各类数据的统计信息"""
    DATA_TYPE_CHOICES = [
        ('canteen', '食堂消费记录'),
        ('school_gate', '校门门禁记录'),
        ('dormitory', '寝室门禁记录'),
        ('network', '网络访问记录'),
        ('academic', '成绩记录'),
    ]
    
    student = models.ForeignKey(
        Student,
        on_delete=models.CASCADE,
        related_name='statistics',
        verbose_name='学生',
        db_index=True
    )
    data_type = models.CharField(
        max_length=20,
        choices=DATA_TYPE_CHOICES,
        verbose_name='数据类型',
        db_index=True
    )
    start_date = models.DateField(verbose_name='统计开始日期', db_index=True)
    end_date = models.DateField(verbose_name='统计结束日期', db_index=True)
    statistics_data = models.JSONField(verbose_name='统计数据', default=dict)
    created_at = models.DateTimeField(auto_now_add=True, verbose_name='创建时间')
    updated_at = models.DateTimeField(auto_now=True, verbose_name='更新时间')
    
    class Meta:
        verbose_name = '数据统计'
        verbose_name_plural = '数据统计'
        ordering = ['-updated_at']
        indexes = [
            models.Index(fields=['student', 'data_type', 'start_date', 'end_date']),
            models.Index(fields=['data_type', 'updated_at']),
        ]
        unique_together = [['student', 'data_type', 'start_date', 'end_date']]
    
    def __str__(self):
        return f"{self.student.student_id} - {self.get_data_type_display()} - {self.start_date} 至 {self.end_date}"
