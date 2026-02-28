"""
批量统计计算模块 - 高性能版本

一次性加载数据到内存，批量计算多个学生多天的统计结果
避免N+1查询问题，大幅提升性能
"""

from datetime import datetime, timedelta
from django.db.models import Q
from django.utils import timezone
from collections import defaultdict


def batch_calculate_canteen_stats(students, start_date, end_date):
    """
    批量计算食堂消费统计
    
    Args:
        students: 学生列表
        start_date: 开始日期
        end_date: 结束日期
    
    Returns:
        dict: {student_id: {date: stats_data}}
    """
    from staff_dashboard.models import CanteenConsumptionRecord
    
    student_ids = [s.id for s in students]
    
    # 生成日期列表
    dates = []
    current = start_date
    while current <= end_date:
        dates.append(current)
        current += timedelta(days=1)
    
    # 一次性查询所有记录
    records = CanteenConsumptionRecord.objects.filter(
        student_id__in=student_ids
    ).select_related('student')
    
    # 按学生+月份分组
    student_month_data = defaultdict(lambda: defaultdict(float))
    for record in records:
        student_month_data[record.student_id][record.month] = float(record.amount)
    
    # 计算每个学生每天的统计
    results = defaultdict(dict)
    for student in students:
        month_data = student_month_data.get(student.id, {})
        
        # 按月份排序计算趋势
        sorted_months = sorted(month_data.keys())
        month_trends = {}  # {month: trend_value}
        
        for i, month in enumerate(sorted_months):
            if i == 0:
                month_trends[month] = 0  # 第一个月份没有趋势
            else:
                prev_month = sorted_months[i-1]
                current_amount = month_data[month]
                prev_amount = month_data[prev_month]
                
                if prev_amount > 0:
                    # 计算环比增长率
                    trend = ((current_amount - prev_amount) / prev_amount) * 100
                    month_trends[month] = round(trend, 2)
                else:
                    month_trends[month] = 0
        
        for date in dates:
            month_key = date.strftime('%Y-%m')
            
            # 获取当月数据
            amount = month_data.get(month_key, 0)
            trend = month_trends.get(month_key, 0)
            
            # 计算最低消费：从所有月份中取最小值
            min_amount = min(month_data.values()) if month_data else 0
            
            results[student.id][date] = {
                'avg_expense': amount,
                'expense_trend': trend,
                'min_expense': min_amount
            }
    
    return results


def batch_calculate_gate_stats(students, start_date, end_date):
    """
    批量计算校门门禁统计
    
    Args:
        students: 学生列表
        start_date: 开始日期
        end_date: 结束日期
    
    Returns:
        dict: {student_id: {date: stats_data}}
    """
    from staff_dashboard.models import SchoolGateAccessRecord
    
    student_ids = [s.id for s in students]
    
    # 生成日期列表
    dates = []
    current = start_date
    while current <= end_date:
        dates.append(current)
        current += timedelta(days=1)
    
    # 转换为datetime范围
    start_datetime = timezone.make_aware(datetime.combine(start_date, datetime.min.time()))
    end_datetime = timezone.make_aware(datetime.combine(end_date, datetime.max.time()))
    
    # 一次性查询所有记录
    records = SchoolGateAccessRecord.objects.filter(
        student_id__in=student_ids,
        timestamp__gte=start_datetime,
        timestamp__lte=end_datetime
    ).select_related('student')
    
    # 按学生+日期分组统计
    student_date_stats = defaultdict(lambda: defaultdict(lambda: {
        'total': 0,
        'night': 0,
        'late_night': 0
    }))
    
    for record in records:
        # 转换为本地时区（Asia/Shanghai）
        local_time = record.timestamp.astimezone(timezone.get_current_timezone())
        date_key = local_time.date()
        hour = local_time.hour
        
        student_date_stats[record.student_id][date_key]['total'] += 1
        
        # 夜间时段：22:00 - 23:59
        if 22 <= hour <= 23:
            student_date_stats[record.student_id][date_key]['night'] += 1
        # 深夜时段：00:00 - 05:59
        elif 0 <= hour <= 5:
            student_date_stats[record.student_id][date_key]['late_night'] += 1
    
    # 构建结果
    results = defaultdict(dict)
    for student in students:
        date_stats = student_date_stats.get(student.id, {})
        
        for date in dates:
            stats = date_stats.get(date, {'total': 0, 'night': 0, 'late_night': 0})
            results[student.id][date] = {
                'total_count': stats['total'],
                'night_in_out_count': stats['night'],
                'late_night_in_out_count': stats['late_night']
            }
    
    return results


def batch_calculate_dormitory_stats(students, start_date, end_date):
    """
    批量计算寝室门禁统计
    
    Args:
        students: 学生列表
        start_date: 开始日期
        end_date: 结束日期
    
    Returns:
        dict: {student_id: {date: stats_data}}
    """
    from staff_dashboard.models import DormitoryAccessRecord
    
    student_ids = [s.id for s in students]
    
    # 生成日期列表
    dates = []
    current = start_date
    while current <= end_date:
        dates.append(current)
        current += timedelta(days=1)
    
    # 转换为datetime范围
    start_datetime = timezone.make_aware(datetime.combine(start_date, datetime.min.time()))
    end_datetime = timezone.make_aware(datetime.combine(end_date, datetime.max.time()))
    
    # 一次性查询所有记录
    records = DormitoryAccessRecord.objects.filter(
        student_id__in=student_ids,
        timestamp__gte=start_datetime,
        timestamp__lte=end_datetime
    ).select_related('student')
    
    # 按学生+日期分组统计
    student_date_stats = defaultdict(lambda: defaultdict(lambda: {
        'total': 0,
        'night': 0,
        'late_night': 0
    }))
    
    for record in records:
        # 转换为本地时区（Asia/Shanghai）
        local_time = record.timestamp.astimezone(timezone.get_current_timezone())
        date_key = local_time.date()
        hour = local_time.hour
        
        student_date_stats[record.student_id][date_key]['total'] += 1
        
        # 夜间时段：22:00 - 23:59
        if 22 <= hour <= 23:
            student_date_stats[record.student_id][date_key]['night'] += 1
        # 深夜时段：00:00 - 05:59
        elif 0 <= hour <= 5:
            student_date_stats[record.student_id][date_key]['late_night'] += 1
    
    # 构建结果
    results = defaultdict(dict)
    for student in students:
        date_stats = student_date_stats.get(student.id, {})
        
        for date in dates:
            stats = date_stats.get(date, {'total': 0, 'night': 0, 'late_night': 0})
            results[student.id][date] = {
                'total_count': stats['total'],
                'night_in_out_count': stats['night'],
                'late_night_in_out_count': stats['late_night']
            }
    
    return results


def batch_calculate_network_stats(students, start_date, end_date):
    """
    批量计算网络访问统计
    
    Args:
        students: 学生列表
        start_date: 开始日期
        end_date: 结束日期
    
    Returns:
        dict: {student_id: {date: stats_data}}
    """
    from staff_dashboard.models import NetworkAccessRecord
    
    student_ids = [s.id for s in students]
    
    # 生成日期列表
    dates = []
    current = start_date
    while current <= end_date:
        dates.append(current)
        current += timedelta(days=1)
    
    # 转换为datetime范围
    start_datetime = timezone.make_aware(datetime.combine(start_date, datetime.min.time()))
    end_datetime = timezone.make_aware(datetime.combine(end_date, datetime.max.time()))
    
    # 一次性查询所有记录
    records = NetworkAccessRecord.objects.filter(
        student_id__in=student_ids,
        start_time__gte=start_datetime,
        end_time__lte=end_datetime
    ).select_related('student')
    
    # 按学生+日期统计
    student_date_stats = defaultdict(lambda: defaultdict(lambda: {
        'vpn_count': 0,
        'total_count': 0,
        'duration': 0.0,
        'has_night': False,
        'has_late_night': False
    }))
    
    for record in records:
        # 转换为本地时区
        local_start = record.start_time.astimezone(timezone.get_current_timezone())
        local_end = record.end_time.astimezone(timezone.get_current_timezone())
        
        date_key = local_start.date()
        duration = (record.end_time - record.start_time).total_seconds() / 3600
        
        student_date_stats[record.student_id][date_key]['total_count'] += 1
        student_date_stats[record.student_id][date_key]['duration'] += duration
        
        if record.use_vpn:
            student_date_stats[record.student_id][date_key]['vpn_count'] += 1
        
        # 检查是否覆盖夜间时段（22:00-23:59）
        start_hour = local_start.hour
        end_hour = local_end.hour
        
        # 判断是否覆盖夜间时段
        if (22 <= start_hour <= 23) or (22 <= end_hour <= 23):
            student_date_stats[record.student_id][date_key]['has_night'] = True
        
        # 判断是否覆盖深夜时段
        if (0 <= start_hour <= 5) or (0 <= end_hour <= 5):
            student_date_stats[record.student_id][date_key]['has_late_night'] = True
    
    # 构建结果
    results = defaultdict(dict)
    for student in students:
        date_stats = student_date_stats.get(student.id, {})
        
        for date in dates:
            stats = date_stats.get(date, {
                'vpn_count': 0, 
                'total_count': 0, 
                'duration': 0,
                'has_night': False,
                'has_late_night': False
            })
            
            vpn_rate = (stats['vpn_count'] / stats['total_count'] * 100) if stats['total_count'] > 0 else 0
            
            results[student.id][date] = {
                'vpn_usage_rate': round(vpn_rate, 2),
                'night_usage_rate': 1 if stats['has_night'] else 0,  # 0或1，表示该天是否有夜间访问
                'late_night_usage_rate': 1 if stats['has_late_night'] else 0,
                'avg_duration': round(stats['duration'], 2),
                'max_duration': round(stats['duration'], 2)
            }
    
    return results


def batch_calculate_academic_stats(students, start_date, end_date):
    """
    批量计算成绩统计
    
    Args:
        students: 学生列表
        start_date: 开始日期
        end_date: 结束日期
    
    Returns:
        dict: {student_id: {date: stats_data}}
    """
    from staff_dashboard.models import AcademicRecord
    
    student_ids = [s.id for s in students]
    
    # 生成日期列表
    dates = []
    current = start_date
    while current <= end_date:
        dates.append(current)
        current += timedelta(days=1)
    
    # 一次性查询所有记录
    records = AcademicRecord.objects.filter(
        student_id__in=student_ids
    ).select_related('student')
    
    # 按学生+月份分组
    student_month_data = defaultdict(lambda: defaultdict(float))
    for record in records:
        student_month_data[record.student_id][record.month] = float(record.average_score)
    
    # 计算每个学生每天的统计
    results = defaultdict(dict)
    for student in students:
        month_data = student_month_data.get(student.id, {})
        
        # 按月份排序计算趋势
        sorted_months = sorted(month_data.keys())
        month_trends = {}  # {month: trend_value}
        
        for i, month in enumerate(sorted_months):
            if i == 0:
                month_trends[month] = 0  # 第一个月份没有趋势
            else:
                prev_month = sorted_months[i-1]
                current_score = month_data[month]
                prev_score = month_data[prev_month]
                
                # 计算分数差值（不是百分比）
                trend = current_score - prev_score
                month_trends[month] = round(trend, 2)
        
        for date in dates:
            month_key = date.strftime('%Y-%m')
            
            # 获取当月数据
            score = month_data.get(month_key, 0)
            trend = month_trends.get(month_key, 0)
            
            results[student.id][date] = {
                'avg_score': score,
                'score_trend': trend
            }
    
    return results
