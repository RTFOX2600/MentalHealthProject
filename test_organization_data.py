"""
测试脚本：创建基础组织数据（学院、专业、年级）

运行方法：
python manage.py shell < test_organization_data.py
"""

from accounts.models import College, Major, Grade

# 创建学院
colleges_data = [
    {'code': 'CS', 'name': '计算机科学学院'},
    {'code': 'EE', 'name': '电子工程学院'},
    {'code': 'BA', 'name': '商学院'},
    {'code': 'LA', 'name': '文学院'},
]

print("正在创建学院数据...")
for college_data in colleges_data:
    college, created = College.objects.get_or_create(
        code=college_data['code'],
        defaults={'name': college_data['name']}
    )
    if created:
        print(f"✓ 创建学院：{college.name} ({college.code})")
    else:
        print(f"- 学院已存在：{college.name} ({college.code})")

# 创建专业
majors_data = [
    {'code': 'CS01', 'name': '计算机科学与技术', 'college_code': 'CS'},
    {'code': 'CS02', 'name': '软件工程', 'college_code': 'CS'},
    {'code': 'CS03', 'name': '人工智能', 'college_code': 'CS'},
    {'code': 'EE01', 'name': '电子信息工程', 'college_code': 'EE'},
    {'code': 'EE02', 'name': '通信工程', 'college_code': 'EE'},
    {'code': 'BA01', 'name': '工商管理', 'college_code': 'BA'},
    {'code': 'BA02', 'name': '会计学', 'college_code': 'BA'},
    {'code': 'LA01', 'name': '汉语言文学', 'college_code': 'LA'},
]

print("\n正在创建专业数据...")
for major_data in majors_data:
    college = College.objects.get(code=major_data['college_code'])
    major, created = Major.objects.get_or_create(
        code=major_data['code'],
        defaults={'name': major_data['name'], 'college': college}
    )
    if created:
        print(f"✓ 创建专业：{major.name} ({major.code}) - {college.name}")
    else:
        print(f"- 专业已存在：{major.name} ({major.code})")

# 创建年级
grades_data = [
    {'year': 2021, 'name': '2021级'},
    {'year': 2022, 'name': '2022级'},
    {'year': 2023, 'name': '2023级'},
    {'year': 2024, 'name': '2024级'},
]

print("\n正在创建年级数据...")
for grade_data in grades_data:
    grade, created = Grade.objects.get_or_create(
        year=grade_data['year'],
        defaults={'name': grade_data['name']}
    )
    if created:
        print(f"✓ 创建年级：{grade.name}")
    else:
        print(f"- 年级已存在：{grade.name}")

print("\n✅ 所有测试数据创建完成！")
print(f"学院总数：{College.objects.count()}")
print(f"专业总数：{Major.objects.count()}")
print(f"年级总数：{Grade.objects.count()}")
