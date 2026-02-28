"""
工作台数据导入 Celery 异步任务
支持大文件批量处理、数据验证、错误收集、每日统计计算
"""
import time

from celery import shared_task
from django.db import transaction
from django.utils import timezone
from django.db.models import Avg, Count, Sum, Q, F
from datetime import datetime, timedelta
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
        
        # 限制验证前10000行数据，提升性能
        validation_limit = min(10000, total_rows)
        
        idx: int
        for idx, row in df.head(validation_limit).iterrows():
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
                'message': '验证前10000行数据中没有有效的数据可导入',
                'errors': errors[:10]  # 只返回前10条错误
            }
        
        # 如果验证通过，处理剩余数据（跳过验证，直接导入）
        if total_rows > validation_limit:
            for idx in range(validation_limit, total_rows):
                try:
                    row = df.iloc[idx]
                    college_code = str(row['学院代码']).strip()
                    major_code = str(row['专业代码']).strip()
                    grade_year = int(row['年级'])
                    student_id = str(row['学号']).strip()
                    
                    # 跳过无效数据
                    if college_code not in colleges or major_code not in majors or grade_year not in grades:
                        continue
                    
                    valid_records.append({
                        'name': str(row['姓名']).strip(),
                        'student_id': student_id,
                        'college': colleges[college_code],
                        'major': majors[major_code],
                        'grade': grades[grade_year]
                    })
                except:
                    continue  # 跳过错误数据
        
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

        print(f"开始解析文件")
        
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

        print(f"开始验证前10000行数据")
        
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
        
        # 限制验证前10000行数据，提升性能
        validation_limit = min(10000, total_rows)
        
        idx: int
        for idx, row in df.head(validation_limit).iterrows():
            try:
                # 根据记录类型构建记录对象
                # 验证学生是否存在
                student_id = str(row['学号']).strip()
                if student_id not in students:
                    errors.append(f'第 {idx + 2} 行：学号 {student_id} 不存在')
                    continue
                
                student = students[student_id]
                
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
                'message': '验证前10000行数据中没有有效的数据可导入',
                'errors': errors[:10]
            }

        print(f"开始处理剩余数据")
        
        # 如果验证通过，处理剩余数据（跳过详细验证，直接导入）
        if total_rows > validation_limit:
            # 更新状态：正在处理剩余数据
            self.update_state(
                state='PROCESSING',
                meta={'current': 40, 'total': 100, 'message': f'正在处理剩余 {total_rows - validation_limit} 行数据...'}
            )

            # 优化：使用切片而非 iloc，性能提升10-100倍
            remaining_df = df.iloc[validation_limit:]

            # 预先过滤出存在的学生ID
            remaining_df = remaining_df[remaining_df['学号'].astype(str).str.strip().isin(students.keys())]

            # 根据记录类型批量处理
            if record_type == 'canteen':
                for _, row in remaining_df.iterrows():
                    try:
                        student_id = str(row['学号']).strip()
                        valid_records.append(CanteenConsumptionRecord(
                            student=students[student_id],
                            month=str(row['月份']).strip(),
                            amount=float(row['消费金额'])
                        ))
                    except:
                        continue
                        
            elif record_type == 'school-gate':
                # 批量时间转换（一次性转换所有时间，而非逐行转换）
                remaining_df['时间_parsed'] = pd.to_datetime(remaining_df['时间'])
                for _, row in remaining_df.iterrows():
                    try:
                        student_id = str(row['学号']).strip()
                        dt = row['时间_parsed']
                        if dt.tzinfo is None:
                            dt = timezone.make_aware(dt, LOCAL_TZ)
                        direction_raw = str(row['进出方向']).strip()
                        direction = direction_map.get(direction_raw, direction_raw)
                        if direction in ['in', 'out']:
                            valid_records.append(SchoolGateAccessRecord(
                                student=students[student_id],
                                timestamp=dt,
                                gate_location=str(row['校门位置']).strip(),
                                direction=direction
                            ))
                    except:
                        continue
                        
            elif record_type == 'dormitory':
                # 批量时间转换
                remaining_df['时间_parsed'] = pd.to_datetime(remaining_df['时间'])
                for _, row in remaining_df.iterrows():
                    try:
                        student_id = str(row['学号']).strip()
                        dt = row['时间_parsed']
                        if dt.tzinfo is None:
                            dt = timezone.make_aware(dt, LOCAL_TZ)
                        direction_raw = str(row['进出方向']).strip()
                        direction = direction_map.get(direction_raw, direction_raw)
                        if direction in ['in', 'out']:
                            valid_records.append(DormitoryAccessRecord(
                                student=students[student_id],
                                timestamp=dt,
                                building=str(row['寝室楼栋']).strip(),
                                direction=direction
                            ))
                    except:
                        continue
                        
            elif record_type == 'network':
                # 批量时间转换（一次性转换所有开始时间和结束时间）
                remaining_df['开始时间_parsed'] = pd.to_datetime(remaining_df['开始时间'])
                remaining_df['结束时间_parsed'] = pd.to_datetime(remaining_df['结束时间'])
                for _, row in remaining_df.iterrows():
                    try:
                        student_id = str(row['学号']).strip()
                        start_dt = row['开始时间_parsed']
                        if start_dt.tzinfo is None:
                            start_dt = timezone.make_aware(start_dt, LOCAL_TZ)
                        end_dt = row['结束时间_parsed']
                        if end_dt.tzinfo is None:
                            end_dt = timezone.make_aware(end_dt, LOCAL_TZ)
                        use_vpn_raw = str(row['是否使用VPN']).strip().lower()
                        use_vpn = use_vpn_raw in ['是', 'yes', 'true', '1']
                        valid_records.append(NetworkAccessRecord(
                            student=students[student_id],
                            start_time=start_dt,
                            end_time=end_dt,
                            use_vpn=use_vpn
                        ))
                    except:
                        continue
                        
            elif record_type == 'academic':
                for _, row in remaining_df.iterrows():
                    try:
                        student_id = str(row['学号']).strip()
                        valid_records.append(AcademicRecord(
                            student=students[student_id],
                            month=str(row['月份']).strip(),
                            average_score=float(row['平均成绩'])
                        ))
                    except:
                        continue
        
        # 更新任务状态：开始导入
        self.update_state(
            state='IMPORTING',
            meta={'current': 60, 'total': 100, 'message': f'正在导入 {len(valid_records)} 条记录...'}
        )

        print(f"开始导入记录")
        
        # 批量导入
        batch_size = 500
        imported_count = 0
        
        with transaction.atomic():
            # 对于有唯一约束的记录类型，需要先删除重复数据
            if record_type in ['canteen', 'academic']:
                # 优化：收集所有学生ID和月份，使用分批删除
                student_ids = set(record.student_id for record in valid_records)
                months = set(record.month for record in valid_records)
                
                # 使用 student_id__in 和 month__in，一次性删除所有可能的重复
                model_class.objects.filter(
                    student_id__in=student_ids,
                    month__in=months
                ).delete()
            
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


@shared_task(bind=True, name='staff_dashboard.calculate_daily_statistics_task')
def calculate_daily_statistics_task(self, start_date=None, end_date=None):
    """
    异步计算每日统计数据
    
    Args:
        self: Celery task instance
        start_date: 开始日期 (YYYY-MM-DD 字符串)，默认为未统计的最早日期
        end_date: 结束日期 (YYYY-MM-DD 字符串)，默认为今天
    
    Returns:
        dict: 统计结果
    """
    try:
        from .models import (
            Student, DailyStatistics,
            CanteenConsumptionRecord, SchoolGateAccessRecord,
            DormitoryAccessRecord, NetworkAccessRecord, AcademicRecord
        )
        from .core.batch_statistics import (
            batch_calculate_canteen_stats,
            batch_calculate_gate_stats,
            batch_calculate_dormitory_stats,
            batch_calculate_network_stats,
            batch_calculate_academic_stats,
        )
        from datetime import datetime, timedelta
        from django.utils import timezone as django_timezone
        
        # 更新任务状态：正在初始化
        self.update_state(
            state='PARSING',
            meta={'current': 5, 'total': 100, 'message': '正在初始化统计任务...'}
        )
        
        # 解析日期范围
        if end_date:
            end = datetime.strptime(end_date, '%Y-%m-%d').date()
        else:
            end = django_timezone.now().date()
        
        if start_date:
            start = datetime.strptime(start_date, '%Y-%m-%d').date()
            print(f"指定统计范围: {start} 至 {end}")
        else:
            # 默认统计最近30天
            start = end - timedelta(days=30)
            print(f"未指定开始日期，默认统计最近30天: {start} 至 {end}")
        
        # 确保开始日期不晚于结束日期
        if start > end:
            start = end
        
        # 更新任务状态：正在加载数据
        self.update_state(
            state='VALIDATING',
            meta={'current': 10, 'total': 100, 'message': f'正在加载学生数据和统计范围 {start} 至 {end}...'}
        )
        
        # 获取所有学生（预加载到内存，避免重复查询）
        students = list(Student.objects.all())
        total_students = len(students)
        
        if total_students == 0:
            return {
                'status': 'error',
                'message': '系统中没有学生数据'
            }
        
        # 生成日期列表
        dates = []
        current_date = start
        while current_date <= end:
            dates.append(current_date)
            current_date += timedelta(days=1)
        
        total_tasks = len(dates) * total_students * 5  # 5种数据类型
        completed_tasks = 0
        
        # 统计类型配置（批量计算）
        data_types_batch = [
            ('canteen', batch_calculate_canteen_stats),
            ('school_gate', batch_calculate_gate_stats),
            ('dormitory', batch_calculate_dormitory_stats),
            ('network', batch_calculate_network_stats),
            ('academic', batch_calculate_academic_stats),
        ]
        
        # 更新任务状态：开始计算
        self.update_state(
            state='PROCESSING',
            meta={
                'current': 15,
                'total': 100,
                'message': f'开始计算 {total_students} 名学生在 {len(dates)} 天的统计数据...'
            }
        )
        
        # 批量创建统计记录
        batch_size = 500  # SQLite 限制：单次查询最多999个参数，为安全起见使用500
        update_batch_size = 100  # 更新操作需要更小的批次（每条记录需要2+个参数）
        statistics_to_create = []
        statistics_to_update = []
        
        # 查询已存在的统计记录（一次性加载到内存）
        existing_stats = {}
        for stat in DailyStatistics.objects.filter(
            date__gte=start,
            date__lte=end
        ).select_related('student'):
            key = (stat.student_id, stat.data_type, stat.date)
            existing_stats[key] = stat
        
        print(f"开始统计：{len(dates)}天 × {total_students}学生 × 5类型 = {total_tasks}项任务")
        print(f"已存在统计记录：{len(existing_stats)}条")
        
        # 优化：按数据类型分组处理，使用批量计算
        for data_type, batch_calc_func in data_types_batch:
            print(f"开始处理 {data_type} 统计，批量计算 {total_students} 名学生在 {len(dates)} 天的数据...")

            # 批量计算所有学生所有日期的统计（一次查询）
            try:
                batch_results = batch_calc_func(students, start, end)
                print(f"批量计算完成，共 {len(batch_results)} 名学生")
            except Exception as e:
                print(f"批量计算失败: {e}")
                import traceback
                traceback.print_exc()
                continue
            
            # 处理每个学生每天的结果
            for student in students:
                student_results = batch_results.get(student.id, {})
                
                for date in dates:
                    try:
                        stats_data = student_results.get(date, {})
                        
                        # 检查是否已存在
                        key = (student.id, data_type, date)
                        if key in existing_stats:
                            # 更新现有记录
                            existing_stat = existing_stats[key]
                            existing_stat.statistics_data = stats_data
                            statistics_to_update.append(existing_stat)
                        else:
                            # 创建新记录
                            statistics_to_create.append(DailyStatistics(
                                student=student,
                                data_type=data_type,
                                date=date,
                                statistics_data=stats_data
                            ))
                        
                    except Exception as e:
                        # 跳过错误，继续处理
                        print(f"处理失败: student={student.student_id}, type={data_type}, date={date}, error={str(e)}")
                    
                    completed_tasks += 1
                    
                    # 每处理 1000 条记录更新一次进度（减少更新频率）
                    if completed_tasks % 1000 == 0:
                        progress = 15 + int((completed_tasks / total_tasks) * 70)
                        self.update_state(
                            state='PROCESSING',
                            meta={
                                'current': progress,
                                'total': 100,
                                'message': f'正在计算... {completed_tasks}/{total_tasks} ({progress-15}%)'
                            }
                        )
                        # print(f"进度：{completed_tasks}/{total_tasks} ({int((completed_tasks/total_tasks)*100)}%)")
                    
                    # 批量保存 - 创建
                    if len(statistics_to_create) >= batch_size:
                        with transaction.atomic():
                            DailyStatistics.objects.bulk_create(statistics_to_create, batch_size=batch_size)
                        # print(f"批量创建 {len(statistics_to_create)} 条记录")
                        statistics_to_create = []
                    
                    # 批量保存 - 更新（使用更小的批次）
                    if len(statistics_to_update) >= update_batch_size:
                        with transaction.atomic():
                            DailyStatistics.objects.bulk_update(
                                statistics_to_update,
                                ['statistics_data', 'updated_at'],
                                batch_size=update_batch_size
                            )
                        # print(f"批量更新 {len(statistics_to_update)} 条记录")
                        statistics_to_update = []
        
        # 更新任务状态：保存剩余数据
        self.update_state(
            state='IMPORTING',
            meta={'current': 90, 'total': 100, 'message': '正在保存统计结果...'}
        )
        
        # 保存剩余的记录
        with transaction.atomic():
            if statistics_to_create:
                DailyStatistics.objects.bulk_create(statistics_to_create, batch_size=batch_size)
            if statistics_to_update:
                # 分批更新，避免超过 SQLite 参数限制
                for i in range(0, len(statistics_to_update), update_batch_size):
                    batch = statistics_to_update[i:i + update_batch_size]
                    DailyStatistics.objects.bulk_update(
                        batch,
                        ['statistics_data', 'updated_at'],
                        batch_size=update_batch_size
                    )
        
        total_created = len(statistics_to_create)
        total_updated = len(statistics_to_update)
        
        return {
            'status': 'success',
            'message': f'每日统计计算完成：{start} 至 {end}，新增 {total_created} 条，更新 {total_updated} 条',
            'records': total_created + total_updated,
            'date_range': f'{start} 至 {end}',
            'total_students': total_students,
            'total_days': len(dates)
        }
        
    except Exception as e:
        import traceback
        error_msg = traceback.format_exc()
        print(f"每日统计计算错误: {error_msg}")
        return {
            'status': 'error',
            'message': f'统计计算失败：{str(e)}'
        }

