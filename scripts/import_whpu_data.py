"""
武汉轻工大学学院和专业数据导入脚本

使用方法：
在项目根目录下运行：
python manage.py shell < scripts/import_whpu_data.py
"""

import os
import sys
import django

# 设置 Django 环境
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'school_platform.settings')
django.setup()

from accounts.models import College, Major, Grade

# 武汉轻工大学学院及专业数据
WHPU_DATA = {
    '食品科学与工程学院': [
        '食品科学与工程',
        '食品质量与安全',
        '粮食工程',
        '食品营养与健康',
        '食品科学与工程（中英合作办学）'
    ],
    '生命科学与技术学院': [
        '生物工程',
        '生物技术',
        '生物信息学',
        '制药工程',
        '合成生物学'
    ],
    '化学与环境工程学院': [
        '化学工程与工艺',
        '环境工程',
        '功能材料'
    ],
    '机械工程学院': [
        '机械设计制造及其自动化',
        '包装工程',
        '材料成型及控制工程',
        '智能制造工程'
    ],
    '动物科学与营养工程学院': [
        '动物科学',
        '动物药学',
        '水产养殖学',
        '饲料工程'
    ],
    '电气与电子工程学院': [
        '电气工程及其自动化',
        '自动化',
        '通信工程',
        '电子信息科学与技术'
    ],
    '数学与计算机学院': [
        '计算机科学与技术',
        '软件工程',
        '信息与计算科学',
        '人工智能'
    ],
    '土木工程与建筑学院': [
        '土木工程',
        '建筑学',
        '智能建造',
        '工程管理（中外合作办学）'
    ],
    '管理学院': [
        '工商管理',
        '会计学',
        '旅游管理',
        '物流管理',
        '行政管理',
        '大数据管理与应用'
    ],
    '经济学院': [
        '国际经济与贸易',
        '金融学',
        '数字经济'
    ],
    '艺术设计学院': [
        '视觉传达设计',
        '环境设计',
        '产品设计'
    ],
    '人文与传媒学院': [
        '汉语言文学',
        '网络与新媒体',
        '广告学（中美合作办学）'
    ],
    '医学与健康学院': [
        '护理学',
        '康复治疗学',
        '药学'
    ],
    '外国语学院': [
        '英语',
        '翻译'
    ],
    '硒科学与工程现代产业学院': [
        '应用生物科学'
    ]
}

# 年级数据（最近几年）
GRADE_DATA = [
    (2021, '2021级'),
    (2022, '2022级'),
    (2023, '2023级'),
    (2024, '2024级'),
    (2025, '2025级'),
]


def import_colleges_and_majors():
    """导入学院和专业数据"""
    print("=" * 60)
    print("开始导入武汉轻工大学学院和专业数据...")
    print("=" * 60)
    
    college_count = 0
    major_count = 0
    
    for idx, (college_name, majors) in enumerate(WHPU_DATA.items(), start=1):
        # 生成学院代码（使用序号）
        college_code = f"C{str(idx).zfill(3)}"
        
        # 创建或获取学院
        college, created = College.objects.get_or_create(
            name=college_name,
            defaults={'code': college_code}
        )
        
        if created:
            print(f"✓ 创建学院: {college_name} (代码: {college.code})")
            college_count += 1
        else:
            print(f"- 学院已存在: {college_name} (代码: {college.code})")
        
        # 创建该学院下的专业
        for major_idx, major_name in enumerate(majors, start=1):
            # 生成专业代码
            major_code = f"{college.code}M{str(major_idx).zfill(3)}"
            
            # 先检查是否已存在（根据学院+专业名）
            existing_major = Major.objects.filter(college=college, name=major_name).first()
            
            if existing_major:
                print(f"  - 专业已存在: {major_name} (代码: {existing_major.code})")
            else:
                # 不存在则创建
                try:
                    major = Major.objects.create(
                        code=major_code,
                        name=major_name,
                        college=college
                    )
                    print(f"  ✓ 创建专业: {major_name} (代码: {major_code})")
                    major_count += 1
                except Exception as e:
                    print(f"  × 创建专业失败: {major_name} - {str(e)}")
    
    print("\n" + "=" * 60)
    print(f"学院和专业导入完成！")
    print(f"共创建 {college_count} 个学院，{major_count} 个专业")
    print("=" * 60)


def import_grades():
    """导入年级数据"""
    print("\n" + "=" * 60)
    print("开始导入年级数据...")
    print("=" * 60)
    
    grade_count = 0
    
    for year, name in GRADE_DATA:
        grade, created = Grade.objects.get_or_create(
            year=year,
            defaults={'name': name}
        )
        
        if created:
            print(f"✓ 创建年级: {name} (入学年份: {year})")
            grade_count += 1
        else:
            print(f"- 年级已存在: {name}")
    
    print("\n" + "=" * 60)
    print(f"年级导入完成！共创建 {grade_count} 个年级")
    print("=" * 60)


def show_statistics():
    """显示统计信息"""
    print("\n" + "=" * 60)
    print("数据库统计信息")
    print("=" * 60)
    
    total_colleges = College.objects.count()
    total_majors = Major.objects.count()
    total_grades = Grade.objects.count()
    
    print(f"学院总数: {total_colleges}")
    print(f"专业总数: {total_majors}")
    print(f"年级总数: {total_grades}")
    
    print("\n学院及其专业数量分布：")
    for college in College.objects.all():
        major_count = college.majors.count()
        print(f"  - {college.name}: {major_count} 个专业")
    
    print("=" * 60)


if __name__ == '__main__':
    # 导入学院和专业
    import_colleges_and_majors()
    
    # 导入年级
    import_grades()
    
    # 显示统计信息
    show_statistics()
    
    print("\n✅ 所有数据导入完成！")
    print("\n提示：专业已自动关联到对应的学院，可以在表单中实现学院-专业筛选联动。")
