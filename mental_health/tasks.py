"""
Celery 异步任务
用于处理耗时的数据分析操作
"""
from celery import shared_task
from django.core.cache import cache
from .models import UploadedDataSet


@shared_task(bind=True, name='mental_health.analyze_task')
def analyze_task(self, user_id, analysis_type, params=None):
    """
    异步分析任务
    
    Args:
        self: Celery task instance
        user_id: 用户ID
        analysis_type: 分析类型（comprehensive, ideology, poverty）
        params: 分析参数
    
    Returns:
        dict: 分析结果，包含 status, filename, excel_data(base64编码)
    """
    try:
        # 更新任务状态：正在准备数据
        self.update_state(
            state='PREPARING',
            meta={'current': 10, 'total': 100, 'status': '正在准备数据...'}
        )
        
        # 获取用户的数据集
        dataset = UploadedDataSet.objects.filter(
            uploaded_by_id=user_id
        ).order_by('-uploaded_at').first()
        
        if not dataset:
            return {
                'status': 'error',
                'message': '未找到上传的数据，请先上传数据文件'
            }
        
        # 更新任务状态：加载数据
        self.update_state(
            state='LOADING',
            meta={'current': 30, 'total': 100, 'status': '正在加载数据...'}
        )
        
        # 准备数据字典
        data_dict = {}
        
        if analysis_type in ['comprehensive', 'poverty']:
            # 需要食堂消费数据
            canteen_records = dataset.canteen_records.all().values('student_id', 'month', 'consumption')
            if canteen_records:
                data_dict['canteen'] = [
                    {
                        '学号': r['student_id'],
                        '年份-月份': r['month'],
                        '食堂消费额度（本月）': float(r['consumption'])
                    }
                    for r in canteen_records
                ]
        
        if analysis_type in ['comprehensive', 'poverty']:
            # 需要校门进出数据
            gate_records = dataset.gate_records.all().values('student_id', 'entry_time', 'direction', 'location')
            if gate_records:
                data_dict['school_gate'] = [
                    {
                        '学号': r['student_id'],
                        '校门进出时间': r['entry_time'],
                        '进出方向': r['direction'],
                        '位置': r['location']
                    }
                    for r in gate_records
                ]
        
        if analysis_type == 'comprehensive':
            # 需要寝室门禁数据
            dorm_records = dataset.dorm_records.all().values('student_id', 'entry_time', 'direction', 'building')
            if dorm_records:
                data_dict['dorm_gate'] = [
                    {
                        '学号': r['student_id'],
                        '寝室进出时间': r['entry_time'],
                        '进出方向': r['direction'],
                        '楼栋': r['building']
                    }
                    for r in dorm_records
                ]
        
        if analysis_type in ['comprehensive', 'ideology']:
            # 需要网络访问数据
            network_records = dataset.network_records.all().values('student_id', 'start_time', 'domain', 'use_vpn')
            if network_records:
                data_dict['network'] = [
                    {
                        '学号': r['student_id'],
                        '开始时间': r['start_time'],
                        '访问域名': r['domain'],
                        '是否使用VPN': '是' if r['use_vpn'] else '否'
                    }
                    for r in network_records
                ]
        
        if analysis_type in ['comprehensive', 'ideology']:
            # 需要成绩数据
            grade_records = dataset.grade_records.all().values('student_id', 'month', 'subject_grades')
            if grade_records:
                grades_list = []
                for r in grade_records:
                    grade_dict = {'学号': r['student_id'], '年份-月份': r['month']}
                    grade_dict.update(r['subject_grades'])
                    grades_list.append(grade_dict)
                data_dict['grades'] = grades_list
        
        # 更新任务状态：开始分析
        self.update_state(
            state='ANALYZING',
            meta={'current': 50, 'total': 100, 'status': '正在进行数据分析...'}
        )
        
        # 执行分析
        if analysis_type == 'comprehensive':
            from core.mental_health.analyse import MentalHealthAnalyzer
            analyzer = MentalHealthAnalyzer(params=params or {})
        elif analysis_type == 'ideology':
            from core.mental_health.analyse import PrecisionIdeologyAnalyzer
            analyzer = PrecisionIdeologyAnalyzer(params=params or {})
        elif analysis_type == 'poverty':
            from core.mental_health.analyse import PrecisionPovertyAlleviationAnalyzer
            analyzer = PrecisionPovertyAlleviationAnalyzer(params=params or {})
        else:
            return {
                'status': 'error',
                'message': '未知的分析类型'
            }
        
        result = analyzer.analyze_comprehensive(data_dict)
        
        # 更新任务状态：生成报告
        self.update_state(
            state='GENERATING',
            meta={'current': 90, 'total': 100, 'status': '正在生成分析报告...'}
        )
        
        if result['status'] == 'success':
            # 将 Excel 数据转换为 base64 编码（便于 JSON 传输）
            import base64
            excel_b64 = base64.b64encode(result['excel_data']).decode('utf-8')
            
            # 缓存结果文件（1小时过期）
            cache_key = f'analysis_result_{self.request.id}'
            try:
                cache.set(cache_key, {
                    'filename': result['filename'],
                    'excel_data': result['excel_data']
                }, timeout=3600)
                print(f"✅ 缓存写入成功: {cache_key}")
                
                # 验证缓存是否可读
                test_read = cache.get(cache_key)
                if test_read:
                    print(f"✅ 缓存读取验证成功")
                else:
                    print(f"❌ 缓存读取验证失败！")
            except Exception as cache_error:
                print(f"❌ 缓存操作失败: {cache_error}")
            
            # 返回结果（不包含 base64 数据，太大会导致 Celery 结果后端失败）
            return {
                'status': 'success',
                'filename': result['filename'],
                'task_id': self.request.id,
                'cache_key': cache_key
            }
        else:
            return {
                'status': 'error',
                'message': result.get('message', '分析失败')
            }
    
    except Exception as e:
        import traceback
        error_msg = traceback.format_exc()
        print(f"分析任务错误: {error_msg}")
        return {
            'status': 'error',
            'message': str(e)
        }


@shared_task(bind=True, name='mental_health.upload_task')
def upload_task(self, user_id, file_type, file_content, filename):
    """
    异步上传任务
    
    Args:
        self: Celery task instance
        user_id: 用户ID
        file_type: 文件类型 (canteen, school-gate, dorm-gate, network, grades)
        file_content: 文件内容 (base64编码)
        filename: 文件名
    
    Returns:
        dict: 上传结果
    """
    try:
        import pandas as pd
        import io
        import base64
        from .models import (
            CanteenConsumption, SchoolGateRecord, DormGateRecord,
            NetworkAccessRecord, GradeRecord
        )
        from django.utils import timezone
        import pytz
        import uuid
        
        LOCAL_TZ = pytz.timezone('Asia/Shanghai')
        
        # 更新任务状态：正在解析文件
        self.update_state(
            state='PARSING',
            meta={'current': 10, 'total': 100, 'status': '正在解析文件...'}
        )
        
        # 解码文件内容
        file_data = base64.b64decode(file_content)
        file_obj = io.BytesIO(file_data)
        
        # 读取文件
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
                'message': f'文件解析失败：{str(parse_error)}\n\n请检查：\n1. 文件是否损坏或格式不正确\n2. Excel 文件是否被其他程序占用\n3. CSV 文件编码是否为 UTF-8'
            }
        
        total_rows = len(df)
        
        # 更新任务状态：开始存储
        self.update_state(
            state='STORING',
            meta={'current': 30, 'total': 100, 'status': f'开始存储 {total_rows} 条记录...'}
        )
        
        # 获取或创建当前用户的数据集
        dataset, created = UploadedDataSet.objects.get_or_create(
            uploaded_by_id=user_id,
            defaults={'session_id': str(uuid.uuid4())}
        )
        
        # 根据类型删除旧数据
        if file_type == 'canteen':
            dataset.canteen_records.all().delete()
            model_class = CanteenConsumption
        elif file_type == 'school-gate':
            dataset.gate_records.all().delete()
            model_class = SchoolGateRecord
        elif file_type == 'dorm-gate':
            dataset.dorm_records.all().delete()
            model_class = DormGateRecord
        elif file_type == 'network':
            dataset.network_records.all().delete()
            model_class = NetworkAccessRecord
        elif file_type == 'grades':
            dataset.grade_records.all().delete()
            model_class = GradeRecord
        else:
            return {
                'status': 'error',
                'message': '未知的文件类型'
            }
        
        # 分批插入数据，并实时报告进度
        batch_size = 500
        records = []
        processed = 0
                
        for idx, row in df.iterrows():
            try:
                # 构建记录对象
                if file_type == 'canteen':
                    record = CanteenConsumption(
                        dataset=dataset,
                        student_id=str(row['学号']),
                        month=row['年份-月份'],
                        consumption=float(row['食堂消费额度（本月）'])
                    )
                elif file_type == 'school-gate':
                    dt = pd.to_datetime(row['校门进出时间'])
                    if dt.tzinfo is None:
                        dt = timezone.make_aware(dt, LOCAL_TZ)
                    direction_map = {'进入': '进', 'in': '进', '出去': '出', 'out': '出', '离开': '出'}
                    raw_dir = str(row['进出方向']).strip()
                    direction = direction_map.get(raw_dir, raw_dir)
                    record = SchoolGateRecord(
                        dataset=dataset,
                        student_id=str(row['学号']),
                        entry_time=dt,
                        direction=direction,
                        location=row['位置']
                    )
                elif file_type == 'dorm-gate':
                    dt = pd.to_datetime(row['寅室进出时间'])
                    if dt.tzinfo is None:
                        dt = timezone.make_aware(dt, LOCAL_TZ)
                    direction_map = {'进入': '进', 'in': '进', '出去': '出', 'out': '出', '离开': '出'}
                    raw_dir = str(row['进出方向']).strip()
                    direction = direction_map.get(raw_dir, raw_dir)
                    record = DormGateRecord(
                        dataset=dataset,
                        student_id=str(row['学号']),
                        entry_time=dt,
                        direction=direction,
                        building=row['楼栋']
                    )
                elif file_type == 'network':
                    dt = pd.to_datetime(row['开始时间'])
                    if dt.tzinfo is None:
                        dt = timezone.make_aware(dt, LOCAL_TZ)
                    use_vpn = str(row['是否使用VPN']).strip() in ['是', 'yes', 'Yes', 'YES']
                    record = NetworkAccessRecord(
                        dataset=dataset,
                        student_id=str(row['学号']),
                        start_time=dt,
                        domain=str(row.get('访问域名', '')),
                        use_vpn=use_vpn
                    )
                elif file_type == 'grades':
                    grade_columns = [col for col in df.columns if col not in ['学号', '年份-月份']]
                    subject_grades = {}
                    for col in grade_columns:
                        try:
                            subject_grades[col] = float(row[col])
                        except:
                            subject_grades[col] = 0.0
                    record = GradeRecord(
                        dataset=dataset,
                        student_id=str(row['学号']),
                        month=row['年份-月份'],
                        subject_grades=subject_grades
                    )
                        
                records.append(record)
                    
            except KeyError as col_error:
                return {
                    'status': 'error',
                    'message': f'第 {idx + 2} 行数据错误：缺少列 "{col_error}"\n\n请检查：\n1. 表格是否为正确的文件类型\n2. 列名是否完全匹配（区分大小写、中文符号）'
                }
            except ValueError as val_error:
                return {
                    'status': 'error',
                    'message': f'第 {idx + 2} 行数据错误：{str(val_error)}\n\n请检查：\n1. 日期时间格式是否正确（如 2024-01-01 12:00:00）\n2. 数值字段是否为有效数字'
                }
            except Exception as row_error:
                return {
                    'status': 'error',
                    'message': f'第 {idx + 2} 行数据处理失败：{str(row_error)}\n\n请检查该行数据是否完整且格式正确'
                }
            
            # 每 500 条批量插入一次
            if len(records) >= batch_size:
                model_class.objects.bulk_create(records, batch_size=batch_size)
                processed += len(records)
                records = []
                
                # 更新进度：30% + (processed / total_rows * 70%)
                progress = 30 + int((processed / total_rows) * 70)
                self.update_state(
                    state='STORING',
                    meta={
                        'current': progress,
                        'total': 100,
                        'status': f'已存储 {processed}/{total_rows} 条记录...'
                    }
                )
        
        # 插入剩余记录
        if records:
            model_class.objects.bulk_create(records, batch_size=batch_size)
            processed += len(records)
        
        # 更新任务状态：完成
        return {
            'status': 'success',
            'message': f'{file_type} 上传成功',
            'records': total_rows
        }
    
    except Exception as e:
        import traceback
        error_msg = traceback.format_exc()
        print(f"上传任务错误: {error_msg}")
        return {
            'status': 'error',
            'message': str(e)
        }
