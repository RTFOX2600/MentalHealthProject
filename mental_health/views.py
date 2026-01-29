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
    """
    心理健康分析系统演示页面。
    
    渲染并返回演示主页 (demo.html)，该页面包含文件上传区域和分析启动按钮。
    """
    return render(request, 'mental_health/demo.html')


@login_required
@csrf_exempt
def upload_file(request, file_type):
    """
    数据文件异步上传接口。
    
    参数:
    - file_type: 文件类型标识，包括 'canteen' (食堂), 'school-gate' (校门), 
      'dorm-gate' (寝室), 'network' (网络), 'grades' (成绩)。
    - file: POST 请求中的文件对象。
    
    返回:
    - JsonResponse: 包含提交状态 'submitted' 和 Celery 任务 ID 'task_id'。
    
    说明:
    该接口将文件内容转为 Base64 并分发给异步任务 upload_task 处理，避免主线程阻塞。
    """
    if request.method != 'POST':
        return JsonResponse({'status': 'error', 'detail': '仅支持POST请求'}, status=405)

    file = request.FILES.get('file')
    if not file:
        return JsonResponse({'status': 'error', 'detail': '未找到上传的文件'}, status=400)

    try:
        # 读取文件内容并转换为 base64
        import base64
        file_content = file.read()
        file_b64 = base64.b64encode(file_content).decode('utf-8')
        
        # 提交异步任务
        from .tasks import upload_task
        task = upload_task.delay(
            user_id=request.user.id,
            file_type=file_type,
            file_content=file_b64,
            filename=file.name
        )
        
        return JsonResponse({
            'status': 'submitted',
            'task_id': task.id,
            'message': '上传任务已提交，正在处理中...'
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


@login_required
def check_upload_status(request, task_id):
    """
    查询文件上传任务的执行状态。
    
    参数:
    - task_id: Celery 任务的 UUID。
    
    返回:
    - JsonResponse: 包含任务状态 ('pending', 'processing', 'success', 'error')、
      当前进度 current、总进度 total 以及状态消息 message。
    """
    from celery.result import AsyncResult
    
    task = AsyncResult(task_id)
    
    if task.state == 'PENDING':
        response = {
            'status': 'pending',
            'current': 0,
            'total': 100,
            'message': '任务排队中...'
        }
    elif task.state == 'PARSING':
        response = {
            'status': 'processing',
            'current': task.info.get('current', 10),
            'total': task.info.get('total', 100),
            'message': task.info.get('status', '正在解析文件...')
        }
    elif task.state == 'STORING':
        response = {
            'status': 'processing',
            'current': task.info.get('current', 50),
            'total': task.info.get('total', 100),
            'message': task.info.get('status', '正在存储数据...')
        }
    elif task.state == 'SUCCESS':
        result = task.result
        if result.get('status') == 'success':
            response = {
                'status': 'success',
                'message': result.get('message'),
                'records': result.get('records')
            }
        else:
            response = {
                'status': 'error',
                'message': result.get('message', '上传失败')
            }
    elif task.state == 'FAILURE':
        response = {
            'status': 'error',
            'message': str(task.info)
        }
    else:
        response = {
            'status': task.state.lower(),
            'message': '任务处理中...'
        }
    
    return JsonResponse(response)


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
    数据分析任务提交接口。
    
    参数:
    - analysis_type: 分析模式，可选 'comprehensive' (综合分析), 
      'ideology' (精准思政), 'poverty' (精准扶贫)。默认为 'comprehensive'。
    - request.body: JSON 格式的分析参数。
    
    返回:
    - JsonResponse: 包含任务提交状态 'submitted' 和 Celery 任务 ID 'task_id'。
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
        # 检查用户是否有数据
        dataset = UploadedDataSet.objects.filter(
            uploaded_by=request.user
        ).first()
        
        if not dataset:
            return JsonResponse({
                'status': 'error',
                'detail': '未找到上传的数据，请先上传数据文件'
            }, status=404)
        
        # 提交异步任务
        from .tasks import analyze_task
        task = analyze_task.delay(
            user_id=request.user.id,
            analysis_type=analysis_type,
            params=params
        )
        
        return JsonResponse({
            'status': 'submitted',
            'task_id': task.id,
            'message': '分析任务已提交，正在处理中...'
        })
    
    except Exception as e:
        import traceback
        traceback.print_exc()
        return JsonResponse({'status': 'error', 'detail': str(e)}, status=500)


@login_required
def check_task_status(request, task_id):
    """
    查询数据分析任务的执行状态。
    
    参数:
    - task_id: Celery 任务的 UUID。
    
    返回:
    - JsonResponse: 包含任务状态 ('pending', 'processing', 'success', 'error')、
      当前进度及各个阶段的消息。任务成功后会返回 cache_key 以供下载。
    """
    from celery.result import AsyncResult
    
    task = AsyncResult(task_id)
    
    if task.state == 'PENDING':
        response = {
            'status': 'pending',
            'current': 0,
            'total': 100,
            'message': '任务排队中...'
        }
    elif task.state == 'PREPARING':
        response = {
            'status': 'processing',
            'current': task.info.get('current', 10),
            'total': task.info.get('total', 100),
            'message': task.info.get('status', '正在准备数据...')
        }
    elif task.state == 'LOADING':
        response = {
            'status': 'processing',
            'current': task.info.get('current', 30),
            'total': task.info.get('total', 100),
            'message': task.info.get('status', '正在加载数据...')
        }
    elif task.state == 'ANALYZING':
        response = {
            'status': 'processing',
            'current': task.info.get('current', 50),
            'total': task.info.get('total', 100),
            'message': task.info.get('status', '正在进行数据分析...')
        }
    elif task.state == 'GENERATING':
        response = {
            'status': 'processing',
            'current': task.info.get('current', 90),
            'total': task.info.get('total', 100),
            'message': task.info.get('status', '正在生成报告...')
        }
    elif task.state == 'SUCCESS':
        result = task.result
        if result.get('status') == 'success':
            response = {
                'status': 'success',
                'filename': result.get('filename'),
                'task_id': task_id,
                'cache_key': result.get('cache_key'),
                'message': '分析完成！'
            }
        else:
            response = {
                'status': 'error',
                'message': result.get('message', '分析失败')
            }
    elif task.state == 'FAILURE':
        response = {
            'status': 'error',
            'message': str(task.info)
        }
    else:
        response = {
            'status': 'unknown',
            'message': f'未知状态: {task.state}'
        }
    
    return JsonResponse(response)


@login_required
def download_result(request, task_id):
    """
    分析结果文件下载接口。
    
    参数:
    - task_id: 关联的分析任务 ID。
    
    返回:
    - FileResponse: 生成的 Excel 文件流。
    - JsonResponse: 发生错误或文件已过期时的错误提示。
    
    说明:
    后端会优先从 Redis 缓存中检索生成的二进制 Excel 数据，若缓存过期需重新分析。
    """
    from django.core.cache import cache
    from celery.result import AsyncResult
    import base64
    
    task = AsyncResult(task_id)
    
    if task.state != 'SUCCESS':
        return JsonResponse({
            'status': 'error',
            'detail': '任务尚未完成或已失败'
        }, status=400)
    
    # 从 Celery 结果后端获取结果
    result = task.result
    
    if not result or result.get('status') != 'success':
        return JsonResponse({
            'status': 'error',
            'detail': '分析结果不可用'
        }, status=404)
    
    # 先尝试从缓存获取（快）
    cache_key = result.get('cache_key')
    if cache_key:
        cached_data = cache.get(cache_key)
        if cached_data:
            response = FileResponse(
                io.BytesIO(cached_data['excel_data']),
                content_type='application/vnd.openxmlformats-officedocument.spreadsheetml.sheet'
            )
            response['Content-Disposition'] = f'attachment; filename="{cached_data["filename"]}"'
            return response
        else:
            print(f"❌ Django 端缓存读取失败: {cache_key}")
    
    # 缓存失败，返回错误
    return JsonResponse({
        'status': 'error',
        'detail': '文件缓存已过期，请重新分析'
    }, status=404)
