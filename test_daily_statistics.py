"""
测试每日统计功能
"""
import os
import django

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'school_platform.settings')
django.setup()

from staff_dashboard.models import DailyStatistics, Student
from datetime import date, timedelta

def test_daily_statistics_model():
    """测试每日统计模型"""
    print("=" * 50)
    print("测试每日统计模型")
    print("=" * 50)
    
    # 检查模型是否正确创建
    print(f"✓ DailyStatistics 模型已加载")
    print(f"  - 字段: {[f.name for f in DailyStatistics._meta.get_fields()]}")
    
    # 检查学生数量
    student_count = Student.objects.count()
    print(f"✓ 当前学生数量: {student_count}")
    
    # 检查现有统计数据
    stats_count = DailyStatistics.objects.count()
    print(f"✓ 当前每日统计记录数: {stats_count}")
    
    if stats_count > 0:
        # 显示一些统计样本
        sample_stats = DailyStatistics.objects.select_related('student')[:5]
        print("\n样本统计记录:")
        for stat in sample_stats:
            print(f"  - {stat.student.student_id} | {stat.get_data_type_display()} | {stat.date} | {stat.statistics_data}")
    
    print("\n测试完成！")

def test_aggregate_functions():
    """测试聚合函数"""
    print("\n" + "=" * 50)
    print("测试聚合函数")
    print("=" * 50)
    
    from staff_dashboard.core import (
        calculate_canteen_stats,
        calculate_gate_stats,
        calculate_dormitory_stats,
        calculate_network_stats,
        calculate_academic_stats
    )
    
    # 获取一个学生进行测试
    student = Student.objects.first()
    
    if not student:
        print("✗ 没有学生数据，无法测试")
        return
    
    print(f"✓ 测试学生: {student.name} ({student.student_id})")
    
    # 测试日期范围
    end_date = date.today()
    start_date = end_date - timedelta(days=30)
    
    print(f"✓ 测试日期范围: {start_date} 至 {end_date}")
    
    # 测试各个聚合函数
    print("\n测试聚合函数:")
    
    try:
        canteen_stats = calculate_canteen_stats(student, start_date, end_date)
        print(f"  ✓ 食堂消费统计: {canteen_stats}")
    except Exception as e:
        print(f"  ✗ 食堂消费统计失败: {e}")
    
    try:
        gate_stats = calculate_gate_stats(student, start_date, end_date)
        print(f"  ✓ 校门门禁统计: {gate_stats}")
    except Exception as e:
        print(f"  ✗ 校门门禁统计失败: {e}")
    
    try:
        dorm_stats = calculate_dormitory_stats(student, start_date, end_date)
        print(f"  ✓ 寝室门禁统计: {dorm_stats}")
    except Exception as e:
        print(f"  ✗ 寝室门禁统计失败: {e}")
    
    try:
        network_stats = calculate_network_stats(student, start_date, end_date)
        print(f"  ✓ 网络访问统计: {network_stats}")
    except Exception as e:
        print(f"  ✗ 网络访问统计失败: {e}")
    
    try:
        academic_stats = calculate_academic_stats(student, start_date, end_date)
        print(f"  ✓ 成绩统计: {academic_stats}")
    except Exception as e:
        print(f"  ✗ 成绩统计失败: {e}")
    
    print("\n测试完成！")

if __name__ == '__main__':
    try:
        test_daily_statistics_model()
        test_aggregate_functions()
        print("\n" + "=" * 50)
        print("所有测试完成！")
        print("=" * 50)
    except Exception as e:
        print(f"\n测试失败: {e}")
        import traceback
        traceback.print_exc()
