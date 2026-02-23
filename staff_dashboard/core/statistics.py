"""
数据统计算法模块

包含各类数据的实时统计计算函数：
- 食堂消费统计
- 校门门禁统计
- 寝室门禁统计
- 网络访问统计
- 学业成绩统计
"""

from datetime import datetime, time, timedelta
from django.db.models import Avg, Min, Q
from django.utils import timezone


def calculate_canteen_stats_realtime(student, start_date, end_date):
    """
    实时计算食堂消费统计
    
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
    
    算法说明：
        - 月均消费：时间范围内所有月份的平均消费
        - 最低消费：时间范围内最低的月度消费
        - 消费趋势：(最后两个月平均 - 最初两个月平均) / 最初两个月平均 * 100
          正数表示增长，负数表示下降
    """
    from staff_dashboard.models import CanteenConsumptionRecord
    
    # 生成月份列表
    months = []
    current = start_date.replace(day=1)
    end = end_date.replace(day=1)
    while current <= end:
        months.append(current.strftime('%Y-%m'))
        if current.month == 12:
            current = current.replace(year=current.year + 1, month=1)
        else:
            current = current.replace(month=current.month + 1)
    
    # 查询记录
    records = CanteenConsumptionRecord.objects.filter(
        student=student,
        month__in=months
    ).order_by('month')
    
    if not records.exists():
        return {'avg_expense': 0, 'expense_trend': 0, 'min_expense': 0}
    
    # 计算月均消费
    avg_expense = records.aggregate(avg=Avg('amount'))['avg']
    avg_expense = round(float(avg_expense) if avg_expense else 0, 2)
    
    # 计算最低消费
    min_expense = records.aggregate(min=Min('amount'))['min']
    min_expense = round(float(min_expense) if min_expense else 0, 2)
    
    # 计算消费趋势
    expense_trend = 0
    if len(months) >= 2:
        # 只有至少两个月的数据才计算趋势
        record_list = list(records)
        if len(record_list) >= 2:
            # 取最初两个月和最后两个月
            initial_records = record_list[:min(2, len(record_list))]
            final_records = record_list[-min(2, len(record_list)):]
            
            initial_avg = sum(r.amount for r in initial_records) / len(initial_records)
            final_avg = sum(r.amount for r in final_records) / len(final_records)
            
            if initial_avg > 0:
                expense_trend = ((final_avg - initial_avg) / initial_avg) * 100
                expense_trend = round(expense_trend, 2)
    
    return {
        'avg_expense': avg_expense,
        'expense_trend': expense_trend,
        'min_expense': min_expense
    }


def calculate_gate_stats_realtime(student, start_date, end_date):
    """
    实时计算校门门禁统计
    
    Args:
        student: Student 模型实例
        start_date: 开始日期 (date 对象)
        end_date: 结束日期 (date 对象)
    
    Returns:
        dict: {
            'total_count': int,              # 总进出次数
            'night_in_out_count': int,       # 夜晚进出次数
            'late_night_in_out_count': int   # 深夜进出次数
        }
    
    时间定义：
        - 夜晚：21:00~22:30
        - 深夜：22:30~24:00 与 0:00~5:00
    """
    from staff_dashboard.models import SchoolGateAccessRecord
    
    start_datetime = timezone.make_aware(datetime.combine(start_date, datetime.min.time()))
    end_datetime = timezone.make_aware(datetime.combine(end_date, datetime.max.time()))
    
    records = SchoolGateAccessRecord.objects.filter(
        student=student,
        timestamp__gte=start_datetime,
        timestamp__lte=end_datetime
    )
    
    if not records.exists():
        return {'total_count': 0, 'night_in_out_count': 0, 'late_night_in_out_count': 0}
    
    total_count = records.count()
    
    # 夜晚：21:00~22:30
    night_records = records.filter(
        Q(timestamp__hour=21) |
        Q(timestamp__hour=22, timestamp__minute__lt=30)
    )
    
    # 深夜：22:30~24:00 与 0:00~5:00
    late_night_records = records.filter(
        Q(timestamp__hour=22, timestamp__minute__gte=30) |  # 22:30~23:59
        Q(timestamp__hour=23) |  # 23:00~23:59
        Q(timestamp__hour__lt=5)  # 0:00~4:59
    )
    
    return {
        'total_count': total_count,
        'night_in_out_count': night_records.count(),
        'late_night_in_out_count': late_night_records.count()
    }


def calculate_dormitory_stats_realtime(student, start_date, end_date):
    """
    实时计算寝室门禁统计
    
    Args:
        student: Student 模型实例
        start_date: 开始日期 (date 对象)
        end_date: 结束日期 (date 对象)
    
    Returns:
        dict: {
            'total_count': int,              # 总进出次数
            'night_in_out_count': int,       # 夜晚进出次数
            'late_night_in_out_count': int   # 深夜进出次数
        }
    
    时间定义：
        - 夜晚：21:00~22:30
        - 深夜：22:30~24:00 与 0:00~5:00
    """
    from staff_dashboard.models import DormitoryAccessRecord
    
    start_datetime = timezone.make_aware(datetime.combine(start_date, datetime.min.time()))
    end_datetime = timezone.make_aware(datetime.combine(end_date, datetime.max.time()))
    
    records = DormitoryAccessRecord.objects.filter(
        student=student,
        timestamp__gte=start_datetime,
        timestamp__lte=end_datetime
    )
    
    if not records.exists():
        return {'total_count': 0, 'night_in_out_count': 0, 'late_night_in_out_count': 0}
    
    total_count = records.count()
    
    # 夜晚：21:00~22:30
    night_records = records.filter(
        Q(timestamp__hour=21) |
        Q(timestamp__hour=22, timestamp__minute__lt=30)
    )
    
    # 深夜：22:30~24:00 与 0:00~5:00
    late_night_records = records.filter(
        Q(timestamp__hour=22, timestamp__minute__gte=30) |  # 22:30~23:59
        Q(timestamp__hour=23) |  # 23:00~23:59
        Q(timestamp__hour__lt=5)  # 0:00~4:59
    )
    
    return {
        'total_count': total_count,
        'night_in_out_count': night_records.count(),
        'late_night_in_out_count': late_night_records.count()
    }


def calculate_network_stats_realtime(student, start_date, end_date):
    """
    实时计算网络访问统计
    
    Args:
        student: Student 模型实例
        start_date: 开始日期 (date 对象)
        end_date: 结束日期 (date 对象)
    
    Returns:
        dict: {
            'vpn_usage_rate': float,         # VPN使用占比（百分比）
            'night_usage_rate': float,       # 夜间上网占比（百分比）
            'late_night_usage_rate': float,  # 深夜上网占比（百分比）
            'avg_duration': float,           # 月均上网时长（小时）
            'max_duration': float            # 最大月上网时长（小时）
        }
    
    时间定义：
        - 夜晚：21:00~22:30
        - 深夜：22:30~24:00 与 0:00~5:00
    
    算法说明：
        - 按月统计上网时长，计算月均时长和最大月时长
        - 计算网络访问时间段与目标时间段的交集时长
        - 按分钟级别精确计算，处理跨天情况
    """
    from staff_dashboard.models import NetworkAccessRecord
    from collections import defaultdict
    
    start_datetime = timezone.make_aware(datetime.combine(start_date, datetime.min.time()))
    end_datetime = timezone.make_aware(datetime.combine(end_date, datetime.max.time()))
    
    records = NetworkAccessRecord.objects.filter(
        student=student,
        start_time__gte=start_datetime,
        end_time__lte=end_datetime
    )
    
    if not records.exists():
        return {'vpn_usage_rate': 0, 'night_usage_rate': 0, 'late_night_usage_rate': 0, 'avg_duration': 0, 'max_duration': 0}
    
    # 计算VPN使用占比
    vpn_count = records.filter(use_vpn=True).count()
    total_count = records.count()
    vpn_usage_rate = (vpn_count / total_count * 100) if total_count > 0 else 0
    
    total_duration = 0
    night_duration = 0
    late_night_duration = 0
    
    # 按月统计时长
    monthly_duration = defaultdict(float)
    
    def time_to_minutes(dt):
        """将 datetime 转换为从午夜起算的分钟数"""
        return dt.hour * 60 + dt.minute
    
    def calculate_overlap(start_time, end_time, range_start_minutes, range_end_minutes):
        """
        计算两个时间段的重叠时长（分钟）
        
        Args:
            start_time: 开始时间 (datetime 对象)
            end_time: 结束时间 (datetime 对象)
            range_start_minutes: 目标时间段开始（从午夜起算的分钟数）
            range_end_minutes: 目标时间段结束（从午夜起算的分钟数）
        
        Returns:
            float: 重叠时长（小时）
        """
        overlap = 0
        current = start_time
        
        while current < end_time:
            current_minutes = time_to_minutes(current)
            
            # 处理跨天的情况（深夜时段）
            if range_end_minutes < range_start_minutes:  # 跨天时间段
                if current_minutes >= range_start_minutes or current_minutes < range_end_minutes:
                    # 在目标时间段内
                    next_time = current + timedelta(minutes=1)
                    if next_time <= end_time:
                        overlap += 1
            else:  # 不跨天的时间段
                if range_start_minutes <= current_minutes < range_end_minutes:
                    next_time = current + timedelta(minutes=1)
                    if next_time <= end_time:
                        overlap += 1
            
            current += timedelta(minutes=1)
        
        return overlap / 60.0  # 转换为小时
    
    # 遍历所有记录，计算各时段时长和按月统计
    for record in records:
        duration = (record.end_time - record.start_time).total_seconds() / 3600
        total_duration += duration
        
        # 按月统计（使用记录开始时间的年月）
        month_key = record.start_time.strftime('%Y-%m')
        monthly_duration[month_key] += duration
        
        # 夜晚：21:00~22:30 (1260分钟 ~ 1350分钟)
        night_overlap = calculate_overlap(record.start_time, record.end_time, 21 * 60, 22 * 60 + 30)
        night_duration += night_overlap
        
        # 深夜：22:30~5:00 (1350分钟 ~ 300分钟，跨天）
        late_night_overlap = calculate_overlap(record.start_time, record.end_time, 22 * 60 + 30, 5 * 60)
        late_night_duration += late_night_overlap
    
    # 计算月均时长和最大月时长
    if monthly_duration:
        month_durations = list(monthly_duration.values())
        avg_duration = sum(month_durations) / len(month_durations)
        max_duration = max(month_durations)
    else:
        avg_duration = 0
        max_duration = 0
    
    # 计算占比
    night_usage_rate = (night_duration / total_duration * 100) if total_duration > 0 else 0
    late_night_usage_rate = (late_night_duration / total_duration * 100) if total_duration > 0 else 0
    
    return {
        'vpn_usage_rate': round(vpn_usage_rate, 2),
        'night_usage_rate': round(night_usage_rate, 2),
        'late_night_usage_rate': round(late_night_usage_rate, 2),
        'avg_duration': round(avg_duration, 2),
        'max_duration': round(max_duration, 2)
    }


def calculate_academic_stats_realtime(student, start_date, end_date):
    """
    实时计算学业成绩统计
    
    Args:
        student: Student 模型实例
        start_date: 开始日期 (date 对象)
        end_date: 结束日期 (date 对象)
    
    Returns:
        dict: {
            'avg_score': float,        # 平均成绩
            'score_trend': float       # 成绩趋势（百分比）
        }
    
    算法说明：
        - 平均成绩：时间范围内所有月份的平均成绩
        - 成绩趋势：(最后两个月平均 - 最初两个月平均) / 最初两个月平均 * 100
          正数表示进步，负数表示退步
    """
    from staff_dashboard.models import AcademicRecord
    
    # 生成月份列表
    months = []
    current = start_date.replace(day=1)
    end = end_date.replace(day=1)
    while current <= end:
        months.append(current.strftime('%Y-%m'))
        if current.month == 12:
            current = current.replace(year=current.year + 1, month=1)
        else:
            current = current.replace(month=current.month + 1)
    
    # 查询记录（按月份排序）
    records = AcademicRecord.objects.filter(
        student=student,
        month__in=months
    ).order_by('month')
    
    if not records.exists():
        return {'avg_score': 0, 'score_trend': 0}
    
    # 计算平均成绩
    avg_score = records.aggregate(avg=Avg('average_score'))['avg']
    avg_score = round(float(avg_score) if avg_score else 0, 2)
    
    # 计算成绩趋势
    score_trend = 0
    if len(months) >= 2:
        # 只有至少两个月的数据才计算趋势
        record_list = list(records)
        if len(record_list) >= 2:
            # 取最初两个月和最后两个月
            initial_records = record_list[:min(2, len(record_list))]
            final_records = record_list[-min(2, len(record_list)):]
            
            initial_avg = sum(float(r.average_score) for r in initial_records) / len(initial_records)
            final_avg = sum(float(r.average_score) for r in final_records) / len(final_records)
            
            if initial_avg > 0:
                score_trend = ((final_avg - initial_avg) / initial_avg) * 100
                score_trend = round(score_trend, 2)
    
    return {
        'avg_score': avg_score,
        'score_trend': score_trend
    }
