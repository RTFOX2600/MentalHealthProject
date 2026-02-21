"""
工作台数据导入 API 接口
支持学生基本信息及五类行为数据的批量导入
"""
from ninja import Router, Schema, File
from ninja.files import UploadedFile
from typing import Optional, List
from django.http import JsonResponse
import base64

router = Router(tags=["工作台-数据导入"])


class TaskResponse(Schema):
    """任务提交响应"""
    status: str
    task_id: str
    message: str


class TaskStatusResponse(Schema):
    """任务状态响应"""
    status: str  # pending, processing, success, error
    current: int = 0
    total: int = 100
    message: str = ""
    records: Optional[int] = None
    errors: Optional[List[str]] = None


class ImportSummaryResponse(Schema):
    """导入统计响应"""
    total_students: int
    total_records: dict  # {'canteen': 100, 'gate': 200, ...}
    last_import_time: Optional[str] = None


@router.post("/import/students", response={200: TaskResponse, 400: dict})
def import_students(request, file: UploadedFile = File(...)):
    """
    ### 批量导入学生基本信息
    
    **文件格式要求**：CSV 或 Excel (UTF-8)
    
    **必需列**：
    - 姓名
    - 学号 (如 2400001)
    - 学院代码 (如 CS)
    - 专业代码 (如 CS01)
    - 年级 (如 2024)
    
    **处理流程**：
    1. 解析文件并验证数据格式
    2. 检查学院、专业、年级是否存在
    3. 批量创建或更新学生记录
    4. 返回导入统计
    """
    if not request.user.role in ['counselor', 'admin']:
        return 400, {"status": "error", "detail": "权限不足"}
    
    try:
        from .tasks import import_students_task
        
        file_content = file.read()
        file_b64 = base64.b64encode(file_content).decode('utf-8')
        
        task = import_students_task.delay(
            user_id=request.user.id,
            file_content=file_b64,
            filename=file.name
        )
        
        return 200, {
            "status": "submitted",
            "task_id": task.id,
            "message": "学生信息导入任务已提交"
        }
    except Exception as e:
        return 400, {"status": "error", "detail": str(e)}


@router.post("/import/canteen", response={200: TaskResponse, 400: dict})
def import_canteen_records(request, file: UploadedFile = File(...)):
    """
    ### 批量导入食堂消费记录
    
    **文件格式要求**：CSV 或 Excel (UTF-8)
    
    **必需列**：
    - 学号
    - 月份 (格式：2025-02)
    - 消费金额
    
    **注意事项**：
    - 学号必须在学生表中存在
    - 同一学生同一月份只能有一条记录（重复则更新）
    """
    if not request.user.role in ['counselor', 'admin']:
        return 400, {"status": "error", "detail": "权限不足"}
    
    try:
        from .tasks import import_records_task
        
        file_content = file.read()
        file_b64 = base64.b64encode(file_content).decode('utf-8')
        
        task = import_records_task.delay(
            user_id=request.user.id,
            record_type='canteen',
            file_content=file_b64,
            filename=file.name
        )
        
        return 200, {
            "status": "submitted",
            "task_id": task.id,
            "message": "食堂消费记录导入任务已提交"
        }
    except Exception as e:
        return 400, {"status": "error", "detail": str(e)}


@router.post("/import/school-gate", response={200: TaskResponse, 400: dict})
def import_school_gate_records(request, file: UploadedFile = File(...)):
    """
    ### 批量导入校门门禁记录
    
    **文件格式要求**：CSV 或 Excel (UTF-8)
    
    **必需列**：
    - 学号
    - 时间 (时间戳格式，如 2025-02-15 08:30:00)
    - 校门位置 (如 北门)
    - 进出方向 (进 或 出)
    """
    if not request.user.role in ['counselor', 'admin']:
        return 400, {"status": "error", "detail": "权限不足"}
    
    try:
        from .tasks import import_records_task
        
        file_content = file.read()
        file_b64 = base64.b64encode(file_content).decode('utf-8')
        
        task = import_records_task.delay(
            user_id=request.user.id,
            record_type='school-gate',
            file_content=file_b64,
            filename=file.name
        )
        
        return 200, {
            "status": "submitted",
            "task_id": task.id,
            "message": "校门门禁记录导入任务已提交"
        }
    except Exception as e:
        return 400, {"status": "error", "detail": str(e)}


@router.post("/import/dormitory", response={200: TaskResponse, 400: dict})
def import_dormitory_records(request, file: UploadedFile = File(...)):
    """
    ### 批量导入寝室门禁记录
    
    **文件格式要求**：CSV 或 Excel (UTF-8)
    
    **必需列**：
    - 学号
    - 时间 (时间戳格式)
    - 寝室楼栋 (如 12栋)
    - 进出方向 (进 或 出)
    """
    if not request.user.role in ['counselor', 'admin']:
        return 400, {"status": "error", "detail": "权限不足"}
    
    try:
        from .tasks import import_records_task
        
        file_content = file.read()
        file_b64 = base64.b64encode(file_content).decode('utf-8')
        
        task = import_records_task.delay(
            user_id=request.user.id,
            record_type='dormitory',
            file_content=file_b64,
            filename=file.name
        )
        
        return 200, {
            "status": "submitted",
            "task_id": task.id,
            "message": "寝室门禁记录导入任务已提交"
        }
    except Exception as e:
        return 400, {"status": "error", "detail": str(e)}


@router.post("/import/network", response={200: TaskResponse, 400: dict})
def import_network_records(request, file: UploadedFile = File(...)):
    """
    ### 批量导入网络访问记录
    
    **文件格式要求**：CSV 或 Excel (UTF-8)
    
    **必需列**：
    - 学号
    - 开始时间 (时间戳格式)
    - 结束时间 (时间戳格式)
    - 是否使用VPN (是/否 或 True/False)
    """
    if not request.user.role in ['counselor', 'admin']:
        return 400, {"status": "error", "detail": "权限不足"}
    
    try:
        from .tasks import import_records_task
        
        file_content = file.read()
        file_b64 = base64.b64encode(file_content).decode('utf-8')
        
        task = import_records_task.delay(
            user_id=request.user.id,
            record_type='network',
            file_content=file_b64,
            filename=file.name
        )
        
        return 200, {
            "status": "submitted",
            "task_id": task.id,
            "message": "网络访问记录导入任务已提交"
        }
    except Exception as e:
        return 400, {"status": "error", "detail": str(e)}


@router.post("/import/academic", response={200: TaskResponse, 400: dict})
def import_academic_records(request, file: UploadedFile = File(...)):
    """
    ### 批量导入成绩记录
    
    **文件格式要求**：CSV 或 Excel (UTF-8)
    
    **必需列**：
    - 学号
    - 月份 (格式：2025-02)
    - 平均成绩
    
    **注意事项**：
    - 同一学生同一月份只能有一条记录（重复则更新）
    """
    if not request.user.role in ['counselor', 'admin']:
        return 400, {"status": "error", "detail": "权限不足"}
    
    try:
        from .tasks import import_records_task
        
        file_content = file.read()
        file_b64 = base64.b64encode(file_content).decode('utf-8')
        
        task = import_records_task.delay(
            user_id=request.user.id,
            record_type='academic',
            file_content=file_b64,
            filename=file.name
        )
        
        return 200, {
            "status": "submitted",
            "task_id": task.id,
            "message": "成绩记录导入任务已提交"
        }
    except Exception as e:
        return 400, {"status": "error", "detail": str(e)}


@router.get("/import-status/{task_id}", response=TaskStatusResponse)
def check_import_status(request, task_id: str):
    """
    ### 查询导入任务状态
    
    返回任务的执行进度、成功/失败状态、错误信息等
    """
    from celery.result import AsyncResult
    
    task = AsyncResult(task_id)
    
    if task.state == 'PENDING':
        return {"status": "pending", "message": "任务排队中...", "current": 0}
    
    elif task.state in ['PARSING', 'VALIDATING', 'IMPORTING']:
        info = task.info if isinstance(task.info, dict) else {}
        return {
            "status": "processing",
            "current": info.get('current', 0),
            "total": info.get('total', 100),
            "message": info.get('message', '处理中...'),
            "records": info.get('records', 0)
        }
    
    elif task.state == 'SUCCESS':
        result = task.result
        if not isinstance(result, dict):
            return {"status": "error", "message": f"任务执行异常: {str(result)}", "current": 100}
        
        return {
            "status": "success" if result.get('status') == 'success' else "error",
            "message": result.get('message', '导入完成'),
            "current": 100,
            "records": result.get('records'),
            "errors": result.get('errors', [])
        }
    
    return {
        "status": "error",
        "message": str(task.info) if task.info else "任务执行失败",
        "current": 100
    }


@router.get("/import-summary", response=ImportSummaryResponse)
def get_import_summary(request):
    """
    ### 获取导入统计信息
    
    返回当前系统中的学生总数和各类记录总数
    """
    from .models import (
        Student, CanteenConsumptionRecord, SchoolGateAccessRecord,
        DormitoryAccessRecord, NetworkAccessRecord, AcademicRecord
    )
    
    # 根据用户权限筛选学生
    if request.user.role == 'admin':
        students = Student.objects.all()
    elif request.user.role == 'counselor':
        # 辅导员只能看到自己负责的学生
        managed_colleges = request.user.managed_colleges.all()
        managed_majors = request.user.managed_majors.all()
        managed_grades = request.user.managed_grades.all()
        
        students = Student.objects.filter(
            college__in=managed_colleges,
            major__in=managed_majors,
            grade__in=managed_grades
        ).distinct()
    else:
        students = Student.objects.none()
    
    student_ids = list(students.values_list('id', flat=True))
    
    return {
        "total_students": students.count(),
        "total_records": {
            "canteen": CanteenConsumptionRecord.objects.filter(student_id__in=student_ids).count(),
            "school_gate": SchoolGateAccessRecord.objects.filter(student_id__in=student_ids).count(),
            "dormitory": DormitoryAccessRecord.objects.filter(student_id__in=student_ids).count(),
            "network": NetworkAccessRecord.objects.filter(student_id__in=student_ids).count(),
            "academic": AcademicRecord.objects.filter(student_id__in=student_ids).count(),
        },
        "last_import_time": None  # TODO: 可以添加最后导入时间记录
    }
