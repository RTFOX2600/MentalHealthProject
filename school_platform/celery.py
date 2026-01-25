"""
Celery 配置文件
用于配置异步任务队列
"""
import os
from celery import Celery

# 设置 Django settings 模块
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'school_platform.settings')

# 创建 Celery 应用
app = Celery('school_platform')

# 从 Django settings 加载配置，命名空间为 'CELERY'
app.config_from_object('django.conf:settings', namespace='CELERY')

# 自动发现所有已注册 app 中的 tasks.py
app.autodiscover_tasks()


@app.task(bind=True, ignore_result=True)
def debug_task(self):
    """调试任务"""
    print(f'Request: {self.request!r}')
