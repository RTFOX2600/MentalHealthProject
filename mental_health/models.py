from django.db import models
from django.contrib.auth import get_user_model

User = get_user_model()


class UploadedDataSet(models.Model):
    """上传的数据集"""
    uploaded_by = models.ForeignKey(User, on_delete=models.CASCADE, verbose_name="上传用户")
    uploaded_at = models.DateTimeField(auto_now_add=True, verbose_name="上传时间")
    session_id = models.CharField(max_length=100, unique=True, verbose_name="会话ID")
    
    class Meta:
        verbose_name = "数据集"
        verbose_name_plural = "数据集"
        ordering = ['-uploaded_at']


class CanteenConsumption(models.Model):
    """食堂消费记录"""
    dataset = models.ForeignKey(UploadedDataSet, on_delete=models.CASCADE, related_name='canteen_records')
    student_id = models.CharField(max_length=50, verbose_name="学号")
    month = models.CharField(max_length=10, verbose_name="年份-月份")
    consumption = models.DecimalField(max_digits=10, decimal_places=2, verbose_name="食堂消费额度（本月）")
    
    class Meta:
        verbose_name = "食堂消费记录"
        verbose_name_plural = "食堂消费记录"
        indexes = [
            models.Index(fields=['student_id', 'month']),
        ]


class SchoolGateRecord(models.Model):
    """校门进出记录"""
    dataset = models.ForeignKey(UploadedDataSet, on_delete=models.CASCADE, related_name='gate_records')
    student_id = models.CharField(max_length=50, verbose_name="学号")
    entry_time = models.DateTimeField(verbose_name="校门进出时间")
    direction = models.CharField(max_length=10, verbose_name="进出方向")
    location = models.CharField(max_length=100, verbose_name="位置")
    
    class Meta:
        verbose_name = "校门进出记录"
        verbose_name_plural = "校门进出记录"
        indexes = [
            models.Index(fields=['student_id', 'entry_time']),
        ]


class DormGateRecord(models.Model):
    """寝室门禁记录"""
    dataset = models.ForeignKey(UploadedDataSet, on_delete=models.CASCADE, related_name='dorm_records')
    student_id = models.CharField(max_length=50, verbose_name="学号")
    entry_time = models.DateTimeField(verbose_name="寝室进出时间")
    direction = models.CharField(max_length=10, verbose_name="进出方向")
    building = models.CharField(max_length=100, verbose_name="楼栋")
    
    class Meta:
        verbose_name = "寝室门禁记录"
        verbose_name_plural = "寝室门禁记录"
        indexes = [
            models.Index(fields=['student_id', 'entry_time']),
        ]


class NetworkAccessRecord(models.Model):
    """网络访问记录"""
    dataset = models.ForeignKey(UploadedDataSet, on_delete=models.CASCADE, related_name='network_records')
    student_id = models.CharField(max_length=50, verbose_name="学号")
    start_time = models.DateTimeField(verbose_name="开始时间")
    domain = models.CharField(max_length=255, verbose_name="访问域名", blank=True)
    use_vpn = models.BooleanField(verbose_name="是否使用VPN")
    
    class Meta:
        verbose_name = "网络访问记录"
        verbose_name_plural = "网络访问记录"
        indexes = [
            models.Index(fields=['student_id', 'start_time']),
        ]


class GradeRecord(models.Model):
    """成绩记录"""
    dataset = models.ForeignKey(UploadedDataSet, on_delete=models.CASCADE, related_name='grade_records')
    student_id = models.CharField(max_length=50, verbose_name="学号")
    month = models.CharField(max_length=10, verbose_name="年份-月份")
    subject_grades = models.JSONField(verbose_name="各科成绩")  # 存储为 JSON 格式
    
    class Meta:
        verbose_name = "成绩记录"
        verbose_name_plural = "成绩记录"
        indexes = [
            models.Index(fields=['student_id', 'month']),
        ]


class AnalysisResult(models.Model):
    """分析结果"""
    dataset = models.ForeignKey(UploadedDataSet, on_delete=models.CASCADE, related_name='analysis_results')
    analysis_type = models.CharField(max_length=50, verbose_name="分析类型")  # comprehensive, ideology, poverty
    created_at = models.DateTimeField(auto_now_add=True, verbose_name="分析时间")
    result_data = models.JSONField(verbose_name="分析结果数据")
    excel_file = models.FileField(upload_to='analysis_results/', verbose_name="Excel文件", null=True, blank=True)
    
    class Meta:
        verbose_name = "分析结果"
        verbose_name_plural = "分析结果"
        ordering = ['-created_at']
