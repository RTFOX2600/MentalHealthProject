"""
测试批量统计性能
"""
import os
import django
import time

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'school_platform.settings')
django.setup()

from staff_dashboard.models import Student
from staff_dashboard.core.batch_statistics import (
    batch_calculate_canteen_stats,
    batch_calculate_gate_stats,
    batch_calculate_dormitory_stats,
    batch_calculate_network_stats,
    batch_calculate_academic_stats
)
from datetime import date, timedelta

def test_batch_performance():
    """测试批量计算性能"""
    print("=" * 60)
    print("批量统计性能测试")
    print("=" * 60)
    
    # 获取学生列表
    students = list(Student.objects.all()[:10])  # 先测试10个学生
    if not students:
        print("✗ 没有学生数据")
        return
    
    print(f"✓ 测试学生数: {len(students)}")
    
    # 测试日期范围：最近7天
    end_date = date.today()
    start_date = end_date - timedelta(days=7)
    
    print(f"✓ 测试日期范围: {start_date} 至 {end_date}")
    print()
    
    # 测试各个批量函数
    test_cases = [
        ('食堂消费', batch_calculate_canteen_stats),
        ('校门门禁', batch_calculate_gate_stats),
        ('寝室门禁', batch_calculate_dormitory_stats),
        ('网络访问', batch_calculate_network_stats),
        ('成绩统计', batch_calculate_academic_stats),
    ]
    
    for name, func in test_cases:
        print(f"测试 {name} ...")
        
        try:
            start_time = time.time()
            results = func(students, start_date, end_date)
            elapsed = time.time() - start_time
            
            # 统计结果数量
            total_records = sum(len(dates_dict) for dates_dict in results.values())
            
            print(f"  ✓ 耗时: {elapsed:.3f}秒")
            print(f"  ✓ 结果: {len(results)}名学生，共{total_records}条记录")
            
            # 显示一个样本
            if results:
                sample_student_id = list(results.keys())[0]
                sample_dates = list(results[sample_student_id].keys())
                if sample_dates:
                    sample_date = sample_dates[0]
                    sample_data = results[sample_student_id][sample_date]
                    print(f"  ✓ 样本数据: {sample_data}")
            
        except Exception as e:
            print(f"  ✗ 失败: {e}")
            import traceback
            traceback.print_exc()
        
        print()

if __name__ == '__main__':
    test_batch_performance()
    print("=" * 60)
    print("测试完成")
    print("=" * 60)
