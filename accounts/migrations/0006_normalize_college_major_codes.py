# Generated manually for normalizing college and major codes

from django.db import migrations


def normalize_codes(apps, schema_editor):
    """将学院和专业代码统一为字母缩写格式"""
    College = apps.get_model('accounts', 'College')
    Major = apps.get_model('accounts', 'Major')
    
    # 学院代码映射：旧代码 -> 新代码
    college_code_mapping = {
        'C001': 'FS',   # Food Science 食品科学与工程学院
        'C002': 'BT',   # Biotechnology 生命科学与技术学院
        'C003': 'CE',   # Chemical Engineering 化学与环境工程学院
        'C004': 'ME',   # Mechanical Engineering 机械工程学院
        'C005': 'AS',   # Animal Science 动物科学与营养工程学院
        'C006': 'EE',   # Electrical Engineering 电气与电子工程学院（注意：已存在EE）
        'C008': 'CA',   # Civil & Architecture 土木工程与建筑学院
        'C009': 'MG',   # Management 管理学院
        'C010': 'EC',   # Economics 经济学院
        'C011': 'AD',   # Art & Design 艺术设计学院
        'C012': 'HM',   # Humanities & Media 人文与传媒学院
        'C013': 'MH',   # Medicine & Health 医学与健康学院
        'C014': 'FL',   # Foreign Languages 外国语学院
        'C015': 'SE',   # Selenium Engineering 硒科学与工程现代产业学院
        # 已经是字母格式的保持不变
        'CS': 'CS',     # Computer Science 数学与计算机学院
        'EE': 'ET',     # Electronics（改为ET避免冲突） 电子工程学院
        'BA': 'BA',     # Business Administration 商学院
        'LA': 'LA',     # Liberal Arts 文学院
    }
    
    # 更新学院代码
    for old_code, new_code in college_code_mapping.items():
        try:
            college = College.objects.get(code=old_code)
            college.code = new_code
            college.save()
            print(f'✓ 学院代码更新: {old_code} -> {new_code} ({college.name})')
        except College.DoesNotExist:
            pass
    
    # 更新专业代码
    # 获取所有学院及其专业
    colleges = College.objects.all()
    for college in colleges:
        majors = Major.objects.filter(college=college).order_by('id')
        for idx, major in enumerate(majors, start=1):
            # 新专业代码格式：学院缩写 + 两位数字
            new_major_code = f'{college.code}{idx:02d}'
            old_major_code = major.code
            major.code = new_major_code
            major.save()
            print(f'✓ 专业代码更新: {old_major_code} -> {new_major_code} ({major.name})')


def reverse_codes(apps, schema_editor):
    """回滚操作（可选）"""
    # 如果需要回滚，可以在这里实现反向操作
    # 但由于原始代码格式不统一，回滚比较复杂，建议备份数据库
    pass


class Migration(migrations.Migration):

    dependencies = [
        ('accounts', '0005_remove_user_is_role_approved_user_requested_role'),
    ]

    operations = [
        migrations.RunPython(normalize_codes, reverse_codes),
    ]
