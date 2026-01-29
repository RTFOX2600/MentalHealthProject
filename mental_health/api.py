from ninja import Router, Schema, File
from ninja.files import UploadedFile
from django.http import JsonResponse, FileResponse
from django.core.cache import cache
from .tasks import upload_task, analyze_task
from .models import UploadedDataSet
from celery.result import AsyncResult
import base64
import io

router = Router(tags=["分析 demo"])

class StatusResponse(Schema):
    status: str = "status"
    current: int = 26
    total: int = 100
    message: str = "This is a msg."
    filename: str = None
    cache_key: str = None
    records: int = None

class AnalysisParams(Schema):
    # 综合分析参数
    contamination: float = 0.15
    night_start: int = 23

    # 精准思政参数 (基于论文指标体系)
    positivity_high: float = 4.0
    positivity_low: float = -2.0
    intensity_high: float = 1.2
    intensity_low: float = 0.8
    radicalism_high: float = 4.0
    radicalism_low: float = 1.5

    # 精准扶贫参数
    poverty_threshold: float = 300.0
    trend_threshold: float = -50.0

class TaskResponse(Schema):
    status: str
    task_id: str
    message: str


@router.post("/upload/{file_type}", response={200: TaskResponse, 400: dict})
def upload_file(request, file_type: str, file: UploadedFile = File(...)):
    """
    ### 数据文件异步上传接口
    将 CSV/Excel 文件（UTF-8）提交至后台进行异步解析。

    支持的 file_type 有: `canteen`, `school-gate`, `dorm-gate`, `network`, `grades`

    **后台处理逻辑 (upload_task):**
    - **阶段流转**: `PARSING` (解析格式) -> `STORING` (分批入库) -> `SUCCESS`
    - **技术细节**: 使用 pandas 处理数据，并利用 Django `bulk_create` 进行每 500 条/批次的原子化入库。
    """
    try:
        file_content = file.read()
        file_b64 = base64.b64encode(file_content).decode('utf-8')
        
        task = upload_task.delay(
            user_id=request.user.id,
            file_type=file_type,
            file_content=file_b64,
            filename=file.name
        )
        
        return 200, {
            "status": "submitted",
            "task_id": task.id,
            "message": f"{file_type} 文件上传任务已提交"
        }
    except Exception as e:
        return 400, {"status": "error", "detail": str(e)}


@router.post("/analyze/{analysis_type}", response={200: TaskResponse, 404: dict})
def analyze_data(request, analysis_type: str, params: AnalysisParams = None):
    """
    ### 数据分析任务提交接口
    触发后台分析引擎，支持 analysis_type 为 comprehensive（综合），ideology（思政），poverty（扶贫）三类分析。

    **后台处理逻辑 (analyze_task):**
    - **阶段流转**: `PREPARING` -> `LOADING` -> `ANALYZING` -> `GENERATING` -> `SUCCESS`
    - **数据获取**: 根据分析类型自动从数据库调取食堂、校门、寝室、网络、成绩等维度数据。
    - **结果输出**: 生成的 Excel 报告将存入 Redis 缓存，过期时间为 1 小时。

    综合分析参数（只需要这两个）
    - contamination: float = 0.15
    - night_start: int = 23

    精准思政参数 (基于论文指标体系)
    - positivity_high: float = 4.0
    - positivity_low: float = -2.0
    - intensity_high: float = 1.2
    - intensity_low: float = 0.8
    - radicalism_high: float = 4.0
    - radicalism_low: float = 1.5

    精准扶贫参数
    - poverty_threshold: float = 300.0
    - trend_threshold: float = -50.0
    """
    dataset = UploadedDataSet.objects.filter(uploaded_by=request.user).first()
    if not dataset:
        return 404, {"status": "error", "detail": "未找到上传的数据"}

    task = analyze_task.delay(
        user_id=request.user.id,
        analysis_type=analysis_type,
        params=params.dict() if params else {}
    )
    
    return 200, {
        "status": "submitted",
        "task_id": task.id,
        "message": f"{analysis_type} 分析任务已提交"
    }


@router.get("/upload-status/{task_id}", response=StatusResponse)
def check_upload_status(request, task_id: str):
    """
    查询文件上传任务的执行状态和进度。
    """
    task = AsyncResult(task_id)
    
    if task.state == 'PENDING':
        return {"status": "pending", "message": "任务排队中..."}
    elif task.state in ['PARSING', 'STORING']:
        info = task.info or {}
        return {
            "status": "processing",
            "current": info.get('current', 10),
            "total": info.get('total', 100),
            "message": info.get('status', '正在处理数据...')
        }
    elif task.state == 'SUCCESS':
        result = task.result
        return {
            "status": "success" if result.get('status') == 'success' else "error",
            "message": result.get('message'),
            "current": 100,
            "records": result.get('records')
        }
    return {"status": "error", "message": str(task.info)}


@router.get("/task-status/{task_id}", response=StatusResponse)
def check_task_status(request, task_id: str):
    """
    查询数据分析任务的执行状态。

    任务成功后将返回 cache_key。
    """
    task = AsyncResult(task_id)
    
    if task.state == 'PENDING':
        return {"status": "pending", "message": "任务排队中..."}
    elif task.state in ['PREPARING', 'LOADING', 'ANALYZING', 'GENERATING']:
        info = task.info or {}
        return {
            "status": "processing",
            "current": info.get('current', 10),
            "total": info.get('total', 100),
            "message": info.get('status', '分析进行中...')
        }
    elif task.state == 'SUCCESS':
        result = task.result
        return {
            "status": "success",
            "filename": result.get('filename'),
            "cache_key": result.get('cache_key'),
            "message": "分析完成！",
            "current": 100
        }
    return {"status": "error", "message": str(task.info)}


@router.get("/download-result/{task_id}")
def download_result(request, task_id: str):
    """
    下载分析生成的 Excel 报告。
    """
    task = AsyncResult(task_id)
    if task.state != 'SUCCESS':
        return JsonResponse({"status": "error", "detail": "任务尚未完成"}, status=400)
    
    result = task.result
    cache_key = result.get('cache_key')
    cached_data = cache.get(cache_key)
    
    if not cached_data:
        return JsonResponse({"status": "error", "detail": "文件已过期"}, status=404)
        
    response = FileResponse(
        io.BytesIO(cached_data['excel_data']),
        content_type='application/vnd.openxmlformats-officedocument.spreadsheetml.sheet'
    )
    response['Content-Disposition'] = f'attachment; filename="{cached_data["filename"]}"'
    return response
