# Gunicorn 配置文件
bind = "0.0.0.0:8000"
workers = 7
worker_class = "sync"
timeout = 180  # 超时 3 分钟
keepalive = 5
max_requests = 1000
max_requests_jitter = 50
accesslog = "/tmp/gunicorn_access.log"
errorlog = "/tmp/gunicorn_error.log"
loglevel = "info"
