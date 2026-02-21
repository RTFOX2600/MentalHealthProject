"""
工作台数据导入 Celery 异步任务
支持大文件批量处理、数据验证、错误收集
"""
from celery import shared_task
from django.db import transaction
from django.utils import timezone
import pandas as pd
import io
import base64
import pytz

LOCAL_TZ = pytz.timezone('Asia/Shanghai')


@shared_task(bind=True, name='staff_dashboard.import_students_task')
def import_students_task(self, user_id, file_content, filename):
    """
    异步导入学生基本信息
    
    Args:
        self: Celery task instance
        user_id: 用户ID
        file_content: 文件内容 (base64编码)
        filename: 文件名
    
    Returns:
        dict: 导入结果
    """
    try:
        from .models import Student
        from accounts.models import College, Major, Grade
        
        # 更新任务状态：正在解析文件
        self.update_state(
            state='PARSING',
            meta={'current': 10, 'total': 100, 'message': '正在解析文件...'}
        )
        
        # 解码并读取文件
        file_data = base64.b64decode(file_content)
        file_obj = io.BytesIO(file_data)
        
        try:
            if filename.endswith('.csv'):
                df = pd.read_csv(file_obj, encoding='utf-8')
            elif filename.endswith(('.xlsx', '.xls')):
                df = pd.read_excel(file_obj)
            else:
                return {
                    'status': 'error',
                    'message': '只支持 CSV 或 Excel 文件'
                }
        except Exception as parse_error:
            return {
                'status': 'error',
                'message': f'文件解析失败：{str(parse_error)}'
            }
        
        # 验证必需列
        required_columns = ['姓名', '学号', '学院代码', '专业代码', '年级']
        missing_columns = [col for col in required_columns if col not in df.columns]
        if missing_columns:
            return {
                'status': 'error',
                'message': f'缺少必需列：{", ".join(missing_columns)}'
            }
        
        total_rows = len(df)
        
        # 更新任务状态：开始验证
        self.update_state(
            state='VALIDATING',
            meta={'current': 30, 'total': 100, 'message': '正在验证数据...'}
        )
        
        # 预加载所有学院、专业、年级
        colleges = {c.code: c for c in College.objects.all()}
        majors = {m.code: m for m in Major.objects.all()}
        grades = {g.year: g for g in Grade.objects.all()}
        
        # 收集错误
        errors = []
        valid_records = []
        
        for idx, row in df.iterrows():
            try:
                # 验证学院
                college_code = str(row['学院代码']).strip()
                if college_code not in colleges:
                    errors.append(f'第 {idx + 2} 行：学院代码 {college_code} 不存在')
                    continue
                
                # 验证专业
                major_code = str(row['专业代码']).strip()
                if major_code not in majors:
                    errors.append(f'第 {idx + 2} 行：专业代码 {major_code} 不存在')
                    continue
                
                # 验证年级
                try:
                    grade_year = int(row['年级'])
                    if grade_year not in grades:
                        errors.append(f'第 {idx + 2} 行：年级 {grade_year} 不存在')
                        continue
                except ValueError:
                    errors.append(f'第 {idx + 2} 行：年级格式错误')
                    continue
                
                # 验证学号格式
                student_id = str(row['学号']).strip()
                if not student_id or len(student_id) > 20:
                    errors.append(f'第 {idx + 2} 行：学号格式错误')
                    continue
                
                valid_records.append({
                    'name': str(row['姓名']).strip(),
                    'student_id': student_id,
                    'college': colleges[college_code],
                    'major': majors[major_code],
                    'grade': grades[grade_year]
                })
                
            except Exception as e:
                errors.append(f'第 {idx + 2} 行：数据处理失败 - {str(e)}')
        
        if not valid_records:
            return {
                'status': 'error',
                'message': '没有有效的数据可导入',
                'errors': errors[:10]  # 只返回前10条错误
            }
        
        # 更新任务状态：开始导入
        self.update_state(
            state='IMPORTING',
            meta={'current': 60, 'total': 100, 'message': f'正在导入 {len(valid_records)} 条记录...'}
        )
        
        # 批量导入（使用 update_or_create）
        imported_count = 0
        updated_count = 0
        
        with transaction.atomic():
            for record in valid_records:
                student, created = Student.objects.update_or_create(
                    student_id=record['student_id'],
                    defaults={
                        'name': record['name'],
                        'college': record['college'],
                        'major': record['major'],
                        'grade': record['grade']
                    }
                )
                if created:
                    imported_count += 1
                else:
                    updated_count += 1
        
        # 构建结果消息
        message_parts = []
        if imported_count > 0:
            message_parts.append(f'新增 {imported_count} 条')
        if updated_count > 0:
            message_parts.append(f'更新 {updated_count} 条')
        if errors:
            message_parts.append(f'跳过 {len(errors)} 条错误数据')
        
        return {
            'status': 'success',
            'message': '学生信息导入完成：' + '，'.join(message_parts),
            'records': imported_count + updated_count,
            'errors': errors[:20] if errors else []  # 返回前20条错误供查看
        }
        
    except Exception as e:
        import traceback
        error_msg = traceback.format_exc()
        print(f"导入学生信息错误: {error_msg}")
        return {
            'status': 'error',
            'message': f'导入失败：{str(e)}'
        }


@shared_task(bind=True, name='staff_dashboard.import_records_task')
def import_records_task(self, user_id, record_type, file_content, filename):
    """
    异步导入各类行为记录
    
    Args:
        self: Celery task instance
        user_id: 用户ID
        record_type: 记录类型 (canteen, school-gate, dormitory, network, academic)
        file_content: 文件内容 (base64编码)
        filename: 文件名
    
    Returns:
        dict: 导入结果
    """
    try:
        from .models import (
            Student, CanteenConsumptionRecord, SchoolGateAccessRecord,
            DormitoryAccessRecord, NetworkAccessRecord, AcademicRecord
        )
        
        # 更新任务状态：正在解析文件
        self.update_state(
            state='PARSING',
            meta={'current': 10, 'total': 100, 'message': '正在解析文件...'}
        )
        
        # 解码并读取文件
        file_data = base64.b64decode(file_content)
        file_obj = io.BytesIO(file_data)
        
        try:
            if filename.endswith('.csv'):
                df = pd.read_csv(file_obj, encoding='utf-8')
            elif filename.endswith(('.xlsx', '.xls')):
                df = pd.read_excel(file_obj)
            else:
                return {
                    'status': 'error',
                    'message': '只支持 CSV 或 Excel 文件'
                }
        except Exception as parse_error:
            return {
                'status': 'error',
                'message': f'文件解析失败：{str(parse_error)}'
            }
        
        # 根据记录类型验证列和配置
        if record_type == 'canteen':
            required_columns = ['学号', '月份', '消费金额']
            model_class = CanteenConsumptionRecord
        elif record_type == 'school-gate':
            required_columns = ['学号', '时间', '校门位置', '进出方向']
            model_class = SchoolGateAccessRecord
        elif record_type == 'dormitory':
            required_columns = ['学号', '时间', '寝室楼栋', '进出方向']
            model_class = DormitoryAccessRecord
        elif record_type == 'network':
            required_columns = ['学号', '开始时间', '结束时间', '是否使用VPN']
            model_class = NetworkAccessRecord
        elif record_type == 'academic':
            required_columns = ['学号', '月份', '平均成绩']
            model_class = AcademicRecord
        else:
            return {
                'status': 'error',
                'message': '未知的记录类型'
            }
        
        # 验证必需列
        missing_columns = [col for col in required_columns if col not in df.columns]
        if missing_columns:
            return {
                'status': 'error',
                'message': f'缺少必需列：{", ".join(missing_columns)}'
            }
        
        total_rows = len(df)
        
        # 更新任务状态：开始验证
        self.update_state(
            state='VALIDATING',
            meta={'current': 30, 'total': 100, 'message': '正在验证数据...'}
        )
        
        # 预加载所有学生（用学号作为键）
        students = {s.student_id: s for s in Student.objects.all()}
        
        # 收集错误和有效记录
        errors = []
        valid_records = []
        
        direction_map = {'进': 'in', '出': 'out', 'in': 'in', 'out': 'out', '进入': 'in', '离开': 'out', '出去': 'out'}
        
        for idx, row in df.iterrows():
            try:
                # 验证学生是否存在
                student_id = str(row['学号']).strip()
                if student_id not in students:
                    errors.append(f'第 {idx + 2} 行：学号 {student_id} 不存在')
                    continue
                
                student = students[student_id]
                
                # 根据记录类型构建记录对象
                if record_type == 'canteen':
                    valid_records.append(CanteenConsumptionRecord(
                        student=student,
                        month=str(row['月份']).strip(),
                        amount=float(row['消费金额'])
                    ))
                    
                elif record_type == 'school-gate':
                    dt = pd.to_datetime(row['时间'])
                    if dt.tzinfo is None:
                        dt = timezone.make_aware(dt, LOCAL_TZ)
                    
                    direction_raw = str(row['进出方向']).strip()
                    direction = direction_map.get(direction_raw, direction_raw)
                    if direction not in ['in', 'out']:
                        errors.append(f'第 {idx + 2} 行：进出方向格式错误')
                        continue
                    
                    valid_records.append(SchoolGateAccessRecord(
                        student=student,
                        timestamp=dt,
                        gate_location=str(row['校门位置']).strip(),
                        direction=direction
                    ))
                    
                elif record_type == 'dormitory':
                    dt = pd.to_datetime(row['时间'])
                    if dt.tzinfo is None:
                        dt = timezone.make_aware(dt, LOCAL_TZ)
                    
                    direction_raw = str(row['进出方向']).strip()
                    direction = direction_map.get(direction_raw, direction_raw)
                    if direction not in ['in', 'out']:
                        errors.append(f'第 {idx + 2} 行：进出方向格式错误')
                        continue
                    
                    valid_records.append(DormitoryAccessRecord(
                        student=student,
                        timestamp=dt,
                        building=str(row['寝室楼栋']).strip(),
                        direction=direction
                    ))
                    
                elif record_type == 'network':
                    start_dt = pd.to_datetime(row['开始时间'])
                    if start_dt.tzinfo is None:
                        start_dt = timezone.make_aware(start_dt, LOCAL_TZ)
                    
                    end_dt = pd.to_datetime(row['结束时间'])
                    if end_dt.tzinfo is None:
                        end_dt = timezone.make_aware(end_dt, LOCAL_TZ)
                    
                    use_vpn_raw = str(row['是否使用VPN']).strip().lower()
                    use_vpn = use_vpn_raw in ['是', 'yes', 'true', '1']
                    
                    valid_records.append(NetworkAccessRecord(
                        student=student,
                        start_time=start_dt,
                        end_time=end_dt,
                        use_vpn=use_vpn
                    ))
                    
                elif record_type == 'academic':
                    valid_records.append(AcademicRecord(
                        student=student,
                        month=str(row['月份']).strip(),
                        average_score=float(row['平均成绩'])
                    ))
                
            except KeyError as e:
                errors.append(f'第 {idx + 2} 行：缺少列 {str(e)}')
            except ValueError as e:
                errors.append(f'第 {idx + 2} 行：数据格式错误 - {str(e)}')
            except Exception as e:
                errors.append(f'第 {idx + 2} 行：处理失败 - {str(e)}')
        
        if not valid_records:
            return {
                'status': 'error',
                'message': '没有有效的数据可导入',
                'errors': errors[:10]
            }
        
        # 更新任务状态：开始导入
        self.update_state(
            state='IMPORTING',
            meta={'current': 60, 'total': 100, 'message': f'正在导入 {len(valid_records)} 条记录...'}
        )
        
        # 批量导入
        batch_size = 500
        imported_count = 0
        
        with transaction.atomic():
            # 对于有唯一约束的记录类型，需要先删除重复数据
            if record_type in ['canteen', 'academic']:
                # 获取所有要导入的学生-月份组合
                student_months = set()
                for record in valid_records:
                    student_months.add((record.student_id, record.month))
                
                # 删除已存在的记录
                for student_id, month in student_months:
                    model_class.objects.filter(student_id=student_id, month=month).delete()
            
            # 分批插入
            for i in range(0, len(valid_records), batch_size):
                batch = valid_records[i:i + batch_size]
                model_class.objects.bulk_create(batch, batch_size=batch_size)
                imported_count += len(batch)
                
                # 更新进度
                progress = 60 + int((imported_count / len(valid_records)) * 40)
                self.update_state(
                    state='IMPORTING',
                    meta={
                        'current': progress,
                        'total': 100,
                        'message': f'已导入 {imported_count}/{len(valid_records)} 条记录...',
                        'records': imported_count
                    }
                )
        
        # 构建结果消息
        record_type_names = {
            'canteen': '食堂消费记录',
            'school-gate': '校门门禁记录',
            'dormitory': '寝室门禁记录',
            'network': '网络访问记录',
            'academic': '成绩记录'
        }
        
        message = f'{record_type_names.get(record_type, "记录")}导入完成：导入 {imported_count} 条'
        if errors:
            message += f'，跳过 {len(errors)} 条错误数据'
        
        return {
            'status': 'success',
            'message': message,
            'records': imported_count,
            'errors': errors[:20] if errors else []
        }
        
    except Exception as e:
        import traceback
        error_msg = traceback.format_exc()
        print(f"导入记录错误: {error_msg}")
        return {
            'status': 'error',
            'message': f'导入失败：{str(e)}'
        }
