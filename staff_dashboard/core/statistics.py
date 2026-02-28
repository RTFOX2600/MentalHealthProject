"""
数据统计算法模块

包含各类数据的实时统计计算函数（用于每日统计）：
- 食堂消费统计
- 校门门禁统计
- 寝室门禁统计
- 网络访问统计
- 学业成绩统计

基于每日统计的聚合计算函数（用于范围查询）：
- 食堂消费聚合统计
- 校门门禁聚合统计
- 寝室门禁聚合统计
- 网络访问聚合统计
- 学业成绩聚合统计
"""

from datetime import datetime, time, timedelta
from django.db.models import Avg, Min, Q
from django.utils import timezone

def calculate_canteen_stats(student, start_date, end_date):
    """
    聚合计算食堂消费统计（基于每日统计）
    
    Args:
        student: Student 模型实例
        start_date: 开始日期 (date 对象)
        end_date: 结束日期 (date 对象)
    
    Returns:
        dict: {
            'avg_expense': float,      # 月均消费
            'min_expense': float,      # 最低消费
            'expense_trend': float     # 消费趋势（百分比）
        }
    """
    from staff_dashboard.models import DailyStatistics
    
    # 查询日期范围内的每日统计
    daily_stats = DailyStatistics.objects.filter(
        student=student,
        data_type='canteen',
        date__gte=start_date,
        date__lte=end_date
    ).order_by('date')
    
    if not daily_stats.exists():
        return {'avg_expense': 0, 'expense_trend': 0, 'min_expense': 0}
    
    # 按月聚合数据
    from collections import defaultdict
    monthly_expenses = defaultdict(float)
    
    for stat in daily_stats:
        month_key = stat.date.strftime('%Y-%m')
        # 每日统计中存储的是当天的消费金额（从 avg_expense 字段获取）
        daily_expense = stat.statistics_data.get('avg_expense', 0)
        monthly_expenses[month_key] += daily_expense
    
    if not monthly_expenses:
        return {'avg_expense': 0, 'expense_trend': 0, 'min_expense': 0}
    
    # 按月份排序
    sorted_months = sorted(monthly_expenses.items())
    expenses = [expense for _, expense in sorted_months]
    
    # 计算月均消费
    avg_expense = sum(expenses) / len(expenses)
    avg_expense = round(avg_expense, 2)
    
    # 计算最低消费
    min_expense = min(expenses)
    min_expense = round(min_expense, 2)
    
    # 计算消费趋势
    expense_trend = 0
    if len(expenses) >= 2:
        initial_records = expenses[:min(2, len(expenses))]
        final_records = expenses[-min(2, len(expenses)):]
        
        initial_avg = sum(initial_records) / len(initial_records)
        final_avg = sum(final_records) / len(final_records)
        
        if initial_avg > 0:
            expense_trend = ((final_avg - initial_avg) / initial_avg) * 100
            expense_trend = round(expense_trend, 2)
    
    return {
        'avg_expense': avg_expense,
        'expense_trend': expense_trend,
        'min_expense': min_expense
    }


def calculate_gate_stats(student, start_date, end_date):
    """
    聚合计算校门门禁统计（基于每日统计）
    
    Args:
        student: Student 模型实例
        start_date: 开始日期 (date 对象)
        end_date: 结束日期 (date 对象)
    
    Returns:
        dict: {
            'total_count': int,
            'night_in_out_count': int,
            'late_night_in_out_count': int
        }
    """
    from staff_dashboard.models import DailyStatistics
    
    daily_stats = DailyStatistics.objects.filter(
        student=student,
        data_type='school_gate',
        date__gte=start_date,
        date__lte=end_date
    )
    
    if not daily_stats.exists():
        return {'total_count': 0, 'night_in_out_count': 0, 'late_night_in_out_count': 0}
    
    total_count = 0
    night_in_out_count = 0
    late_night_in_out_count = 0
    
    for stat in daily_stats:
        total_count += stat.statistics_data.get('total_count', 0)
        night_in_out_count += stat.statistics_data.get('night_in_out_count', 0)
        late_night_in_out_count += stat.statistics_data.get('late_night_in_out_count', 0)
    
    return {
        'total_count': total_count,
        'night_in_out_count': night_in_out_count,
        'late_night_in_out_count': late_night_in_out_count
    }


def calculate_dormitory_stats(student, start_date, end_date):
    """
    聚合计算寝室门禁统计（基于每日统计）
    
    Args:
        student: Student 模型实例
        start_date: 开始日期 (date 对象)
        end_date: 结束日期 (date 对象)
    
    Returns:
        dict: {
            'total_count': int,
            'night_in_out_count': int,
            'late_night_in_out_count': int
        }
    """
    from staff_dashboard.models import DailyStatistics
    
    daily_stats = DailyStatistics.objects.filter(
        student=student,
        data_type='dormitory',
        date__gte=start_date,
        date__lte=end_date
    )
    
    if not daily_stats.exists():
        return {'total_count': 0, 'night_in_out_count': 0, 'late_night_in_out_count': 0}
    
    total_count = 0
    night_in_out_count = 0
    late_night_in_out_count = 0
    
    for stat in daily_stats:
        total_count += stat.statistics_data.get('total_count', 0)
        night_in_out_count += stat.statistics_data.get('night_in_out_count', 0)
        late_night_in_out_count += stat.statistics_data.get('late_night_in_out_count', 0)
    
    return {
        'total_count': total_count,
        'night_in_out_count': night_in_out_count,
        'late_night_in_out_count': late_night_in_out_count
    }


def calculate_network_stats(student, start_date, end_date):
    """
    聚合计算网络访问统计（基于每日统计）
    
    Args:
        student: Student 模型实例
        start_date: 开始日期 (date 对象)
        end_date: 结束日期 (date 对象)
    
    Returns:
        dict: {
            'vpn_usage_rate': float,
            'night_usage_rate': float,  # 夜间覆盖率
            'late_night_usage_rate': float,  # 深夜覆盖率
            'avg_duration': float,
            'max_duration': float
        }
    """
    from staff_dashboard.models import DailyStatistics
    from collections import defaultdict
    from datetime import timedelta
    
    daily_stats = DailyStatistics.objects.filter(
        student=student,
        data_type='network',
        date__gte=start_date,
        date__lte=end_date
    )
    
    if not daily_stats.exists():
        return {'vpn_usage_rate': 0, 'night_usage_rate': 0, 'late_night_usage_rate': 0, 'avg_duration': 0, 'max_duration': 0}
    
    # 计算统计范围内的总天数
    total_days = (end_date - start_date).days + 1
    
    # 按月聚合数据
    monthly_duration = defaultdict(float)
    total_vpn_duration = 0
    total_duration = 0
    night_days = 0  # 有夜间访问的天数
    late_night_days = 0  # 有深夜访问的天数
    
    for stat in daily_stats:
        month_key = stat.date.strftime('%Y-%m')
        
        # 获取每日的统计数据
        vpn_rate = stat.statistics_data.get('vpn_usage_rate', 0)
        night_flag = stat.statistics_data.get('night_usage_rate', 0)  # 0或1
        late_night_flag = stat.statistics_data.get('late_night_usage_rate', 0)  # 0或1
        daily_avg_duration = stat.statistics_data.get('avg_duration', 0)
        
        # 按月统计时长
        monthly_duration[month_key] += daily_avg_duration
        
        # 统计总时长和 VPN 使用时长
        total_duration += daily_avg_duration
        total_vpn_duration += daily_avg_duration * (vpn_rate / 100)
        
        # 统计覆盖天数
        if night_flag > 0:
            night_days += 1
        if late_night_flag > 0:
            late_night_days += 1
    
    # 计算月均时长和最大月时长
    if monthly_duration:
        month_durations = list(monthly_duration.values())
        avg_duration = sum(month_durations) / len(month_durations)
        max_duration = max(month_durations)
    else:
        avg_duration = 0
        max_duration = 0
    
    # 计算占比
    vpn_usage_rate = (total_vpn_duration / total_duration * 100) if total_duration > 0 else 0
    night_usage_rate = (night_days / total_days * 100) if total_days > 0 else 0  # 覆盖率
    late_night_usage_rate = (late_night_days / total_days * 100) if total_days > 0 else 0  # 覆盖率
    
    return {
        'vpn_usage_rate': round(vpn_usage_rate, 2),
        'night_usage_rate': round(night_usage_rate, 2),
        'late_night_usage_rate': round(late_night_usage_rate, 2),
        'avg_duration': round(avg_duration, 2),
        'max_duration': round(max_duration, 2)
    }


def calculate_academic_stats(student, start_date, end_date):
    """
    聚合计算学业成绩统计（基于每日统计）
    
    Args:
        student: Student 模型实例
        start_date: 开始日期 (date 对象)
        end_date: 结束日期 (date 对象)
    
    Returns:
        dict: {
            'avg_score': float,
            'score_trend': float
        }
    """
    from staff_dashboard.models import DailyStatistics
    
    daily_stats = DailyStatistics.objects.filter(
        student=student,
        data_type='academic',
        date__gte=start_date,
        date__lte=end_date
    ).order_by('date')
    
    if not daily_stats.exists():
        return {'avg_score': 0, 'score_trend': 0}
    
    # 按月聚合数据
    from collections import defaultdict
    monthly_scores = defaultdict(list)
    
    for stat in daily_stats:
        month_key = stat.date.strftime('%Y-%m')
        score = stat.statistics_data.get('avg_score', 0)
        if score > 0:  # 只统计有效成绩
            monthly_scores[month_key].append(score)
    
    if not monthly_scores:
        return {'avg_score': 0, 'score_trend': 0}
    
    # 计算每个月的平均成绩
    monthly_avg_scores = {}
    for month, scores in monthly_scores.items():
        monthly_avg_scores[month] = sum(scores) / len(scores)
    
    # 按月份排序
    sorted_months = sorted(monthly_avg_scores.items())
    scores = [score for _, score in sorted_months]
    
    # 计算平均成绩
    avg_score = sum(scores) / len(scores)
    avg_score = round(avg_score, 2)
    
    # 计算成绩趋势
    score_trend = 0
    if len(scores) >= 2:
        initial_records = scores[:min(2, len(scores))]
        final_records = scores[-min(2, len(scores)):]
        
        initial_avg = sum(initial_records) / len(initial_records)
        final_avg = sum(final_records) / len(final_records)
        
        if initial_avg > 0:
            score_trend = ((final_avg - initial_avg) / initial_avg) * 100
            score_trend = round(score_trend, 2)
    
    return {
        'avg_score': avg_score,
        'score_trend': score_trend
    }
