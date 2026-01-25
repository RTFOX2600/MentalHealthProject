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
