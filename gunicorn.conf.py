# Gunicorn 配置文件
import os
from pathlib import Path

# 项目根目录
BASE_DIR = Path(__file__).resolve().parent

bind = "0.0.0.0:8000"
workers = 7
worker_class = "sync"
timeout = 180  # 超时 3 分钟
keepalive = 5
max_requests = 1000
max_requests_jitter = 50

# 日志配置（相对于项目目录）
accesslog = str(BASE_DIR / "logs" / "access.log")
errorlog = str(BASE_DIR / "logs" / "error.log")
loglevel = "info"
