from django.shortcuts import render
from django.contrib.auth.decorators import login_required
from django.http import JsonResponse, FileResponse
from django.views.decorators.csrf import csrf_exempt
from django.db import transaction
from django.utils import timezone
import pytz
import pandas as pd
import io
import uuid
from .models import (
    UploadedDataSet, CanteenConsumption, SchoolGateRecord,
    DormGateRecord, NetworkAccessRecord, GradeRecord, AnalysisResult
)


# 定义本地时区
LOCAL_TZ = pytz.timezone('Asia/Shanghai')


@login_required
def demo_page(request):
    """演示页面"""
    return render(request, 'mental_health/demo.html')


@login_required
@csrf_exempt
def upload_file(request, file_type):
    """
    上传文件接口
    file_type: canteen, school-gate, dorm-gate, network, grades
    """
    if request.method != 'POST':
        return JsonResponse({'status': 'error', 'detail': '仅支持POST请求'}, status=405)

    file = request.FILES.get('file')
    if not file:
        return JsonResponse({'status': 'error', 'detail': '未找到上传的文件'}, status=400)

    try:
        # 读取文件
        if file.name.endswith('.csv'):
            df = pd.read_csv(file, encoding='utf-8')
        elif file.name.endswith(('.xlsx', '.xls')):
            df = pd.read_excel(file)
        else:
            return JsonResponse({'status': 'error', 'detail': '只支持 CSV 或 Excel 文件'}, status=400)

        # 获取或创建会话ID
        session_id = request.session.get('dataset_session_id')
        if not session_id:
            session_id = str(uuid.uuid4())
            request.session['dataset_session_id'] = session_id

        # 获取或创建数据集
        dataset, created = UploadedDataSet.objects.get_or_create(
            session_id=session_id,
            defaults={'uploaded_by': request.user}
        )

        # 根据类型保存数据（分批提交，无需大事务）
        if file_type == 'canteen':
            _save_canteen_data(dataset, df)
        elif file_type == 'school-gate':
            _save_school_gate_data(dataset, df)
        elif file_type == 'dorm-gate':
            _save_dorm_gate_data(dataset, df)
        elif file_type == 'network':
            _save_network_data(dataset, df)
        elif file_type == 'grades':
            _save_grades_data(dataset, df)
        else:
            return JsonResponse({'status': 'error', 'detail': '未知的文件类型'}, status=400)

        # 标记当前表格已上传
        uploaded_tables = request.session.get('uploaded_tables', [])
        if file_type not in uploaded_tables:
            uploaded_tables.append(file_type)
            request.session['uploaded_tables'] = uploaded_tables

        return JsonResponse({
            'status': 'success',
            'message': f'{file_type} 上传成功',
            'records': len(df)
        })

    except Exception as e:
        import traceback
        error_detail = {
            'error': str(e),
            'type': type(e).__name__,
            'traceback': traceback.format_exc()
        }
        print(f"上传文件错误: {error_detail}")  # 打印到日志
        return JsonResponse({
            'status': 'error',
            'detail': str(e),
            'error_type': type(e).__name__
        }, status=500)


def _save_canteen_data(dataset, df):
    """保存食堂消费数据"""
    # 删除旧数据
    dataset.canteen_records.all().delete()

    records = []
    for _, row in df.iterrows():
        records.append(CanteenConsumption(
            dataset=dataset,
            student_id=str(row['学号']),
            month=row['年份-月份'],
            consumption=float(row['食堂消费额度（本月）'])
        ))
        
        # 每 500 条批量插入一次
        if len(records) >= 500:
            CanteenConsumption.objects.bulk_create(records, batch_size=500)
            records = []
    
    if records:
        CanteenConsumption.objects.bulk_create(records, batch_size=500)


def _save_school_gate_data(dataset, df):
    """保存校门进出数据"""
    dataset.gate_records.all().delete()
    
    # 定义方向映射
    direction_map = {'进入': '进', 'in': '进', '出去': '出', 'out': '出', '离开': '出'}
    
    records = []
    for _, row in df.iterrows():
        dt = pd.to_datetime(row['校门进出时间'])
        if dt.tzinfo is None:
            dt = timezone.make_aware(dt, LOCAL_TZ)
        
        # 标准化方向
        raw_dir = str(row['进出方向']).strip()
        direction = direction_map.get(raw_dir, raw_dir)
        
        records.append(SchoolGateRecord(
            dataset=dataset,
            student_id=str(row['学号']),
            entry_time=dt,
            direction=direction,
            location=row['位置']
        ))
        
        # 每 500 条批量插入一次，避免内存占用过大
        if len(records) >= 500:
            SchoolGateRecord.objects.bulk_create(records, batch_size=500)
            records = []
    
    # 插入剩余记录
    if records:
        SchoolGateRecord.objects.bulk_create(records, batch_size=500)


def _save_dorm_gate_data(dataset, df):
    """保存寝室门禁数据"""
    dataset.dorm_records.all().delete()

    # 定义方向映射
    direction_map = {'进入': '进', 'in': '进', '出去': '出', 'out': '出', '离开': '出'}

    records = []
    for _, row in df.iterrows():
        dt = pd.to_datetime(row['寝室进出时间'])
        if dt.tzinfo is None:
            dt = timezone.make_aware(dt, LOCAL_TZ)

        # 标准化方向
        raw_dir = str(row['进出方向']).strip()
        direction = direction_map.get(raw_dir, raw_dir)

        records.append(DormGateRecord(
            dataset=dataset,
            student_id=str(row['学号']),
            entry_time=dt,
            direction=direction,
            building=row['楼栋']
        ))
        
        # 每 500 条批量插入一次
        if len(records) >= 500:
            DormGateRecord.objects.bulk_create(records, batch_size=500)
            records = []
    
    if records:
        DormGateRecord.objects.bulk_create(records, batch_size=500)


def _save_network_data(dataset, df):
    dataset.network_records.all().delete()
    tz = pytz.timezone('Asia/Shanghai')
    records = []
    for _, row in df.iterrows():
        dt = pd.to_datetime(row['开始时间'])
        if dt.tzinfo is None:
            dt = timezone.make_aware(dt, tz)
        use_vpn = str(row['是否使用VPN']).strip() in ['是', 'yes', 'Yes', 'YES']
        records.append(NetworkAccessRecord(
            dataset=dataset,
            student_id=str(row['学号']),
            start_time=dt,
            domain=str(row.get('访问域名', '')),
            use_vpn=use_vpn
        ))
        
        # 每 500 条批量插入一次
        if len(records) >= 500:
            NetworkAccessRecord.objects.bulk_create(records, batch_size=500)
            records = []
    
    if records:
        NetworkAccessRecord.objects.bulk_create(records, batch_size=500)


def _save_grades_data(dataset, df):
    """保存成绩数据"""
    dataset.grade_records.all().delete()

    records = []
    grade_columns = [col for col in df.columns if col not in ['学号', '年份-月份']]

    for _, row in df.iterrows():
        subject_grades = {}
        for col in grade_columns:
            try:
                subject_grades[col] = float(row[col])
            except:
                subject_grades[col] = None

        records.append(GradeRecord(
            dataset=dataset,
            student_id=str(row['学号']),
            month=row['年份-月份'],
            subject_grades=subject_grades
        ))
        
        # 每 500 条批量插入一次
        if len(records) >= 500:
            GradeRecord.objects.bulk_create(records, batch_size=500)
            records = []
    
    if records:
        GradeRecord.objects.bulk_create(records, batch_size=500)


@login_required
@csrf_exempt
def analyze_data(request, analysis_type='comprehensive'):
    """
    分析数据接口
    analysis_type: comprehensive, ideology, poverty
    """
    if request.method != 'POST':
        return JsonResponse({'status': 'error', 'detail': '仅支持POST请求'}, status=405)

    import json
    params = {}
    try:
        if request.body:
            params = json.loads(request.body)
    except:
        pass

    try:
        # 获取当前会话的数据集（优先使用 session_id，否则使用用户最新数据）
        session_id = request.session.get('dataset_session_id')
        
        if session_id:
            dataset = UploadedDataSet.objects.filter(session_id=session_id).first()
        else:
            # Session 过期时，使用当前用户最新上传的数据集
            dataset = UploadedDataSet.objects.filter(
                uploaded_by=request.user
            ).order_by('-uploaded_at').first()
        
        if not dataset:
            return JsonResponse({
                'status': 'error',
                'detail': '未找到上传的数据，请先上传数据文件'
            }, status=404)

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

        # 执行分析
        if analysis_type == 'comprehensive':
            from core.mental_health.analyse import MentalHealthAnalyzer
            analyzer = MentalHealthAnalyzer(params=params)
        elif analysis_type == 'ideology':
            from core.mental_health.analyse import PrecisionIdeologyAnalyzer
            analyzer = PrecisionIdeologyAnalyzer(params=params)
        elif analysis_type == 'poverty':
            from core.mental_health.analyse import PrecisionPovertyAlleviationAnalyzer
            analyzer = PrecisionPovertyAlleviationAnalyzer(params=params)
        else:
            return JsonResponse({'status': 'error', 'detail': '未知的分析类型'}, status=400)

        result = analyzer.analyze_comprehensive(data_dict)

        if result['status'] == 'success':
            # 直接返回文件流，不再保存到服务器本地
            filename = result['filename']
            response = FileResponse(
                io.BytesIO(result['excel_data']),
                content_type='application/vnd.openxmlformats-officedocument.spreadsheetml.sheet'
            )
            response['Content-Disposition'] = f'attachment; filename="{filename}"'
            return response
        else:
            return JsonResponse({'status': 'error', 'detail': result['message']}, status=500)

    except Exception as e:
        import traceback
        traceback.print_exc()
        return JsonResponse({'status': 'error', 'detail': str(e)}, status=500)
