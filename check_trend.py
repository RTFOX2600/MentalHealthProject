import os
import django

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'school_platform.settings')
django.setup()

from staff_dashboard.models import DailyStatistics, Student
from datetime import date

# 获取第一个学生
student = Student.objects.first()
print(f"学生: {student.name} ({student.student_id})")
print("\n=== 食堂消费统计（2024-01 到 2024-03）===")

# 查询食堂消费统计
canteen_stats = DailyStatistics.objects.filter(
    student=student,
    data_type='canteen',
    date__gte=date(2024, 1, 1),
    date__lte=date(2024, 3, 31)
).order_by('date')[:10]

for stat in canteen_stats:
    data = stat.statistics_data
    print(f"{stat.date}: 消费={data.get('avg_expense', 0):.2f}元, 趋势={data.get('expense_trend', 0)}%")

print("\n=== 成绩统计（2024-01 到 2024-03）===")

# 查询成绩统计
academic_stats = DailyStatistics.objects.filter(
    student=student,
    data_type='academic',
    date__gte=date(2024, 1, 1),
    date__lte=date(2024, 3, 31)
).order_by('date')[:10]

for stat in academic_stats:
    data = stat.statistics_data
    print(f"{stat.date}: 成绩={data.get('avg_score', 0):.2f}分, 趋势={data.get('score_trend', 0)}")

print("\n结论: 如果趋势全部为0，说明需要重新统计！")
