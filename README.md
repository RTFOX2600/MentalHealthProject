# 思想关怀系统

# 项目简介

这是一个通过分析各种数据、进行学生思想状态分析的系统。
可以辅助思想健康分析工作、精准思政工作、精准扶贫工作、舆论监控工作等。

各个部门以及辅导员上传食堂消费统计数据、门禁记录数据、校园网记录数据等，
系统会定时对数据进行处理、分析，并生成每个年级、学院、专业的报告，
同时提供简单的筛选、排序、统计等功能，辅助辅导员进行思想状态分析工作。

---
## 🛠️ 技术栈

### 后端
- **Python 3.12+**
- **Django 6.0+** - Web 框架
- **Celery** - 异步任务队列
- **Redis** - 缓存与消息代理
- **SQLite/PostgreSQL** - 数据库
- **Gunicorn** - WSGI 服务器

### 前端
- **HTML5 + CSS3** - 基础结构与样式
- **JavaScript (ES6+)** - 交互逻辑
- **Bootstrap 5** - UI 框架
- **Chart.js** - 数据可视化
- **DataTables** - 表格增强

### AI 与数据分析
- **DeepSeek** - AI 辅导员与关键信息解析
- **Pandas & NumPy** - 数据处理
- **Scikit-learn** - 机器学习

### 工具与环境
- **Docker** - 容器化部署
- **Git** - 版本控制
- **网络爬虫** - 舆情数据采集

---

## 🚀 快速开始

### 前置要求

- Python 3.12+
- Redis (可选，用于 Celery)
- Git

### 安装步骤

1. **克隆仓库**

```bash
git clone https://github.com/RTFOX2600/MentalHealthProject.git
cd MentalHealthProject
```

2. **创建虚拟环境**

```bash
# Windows
python -m venv venv
venv\Scripts\activate

# Linux/macOS
python3 -m venv venv
source venv/bin/activate
```

3. **安装依赖**

```bash
pip install -r requirements.txt
```

4. **配置环境变量**

复制 `.env.example` 为 `.env` 并修改配置：

```bash
cp .env.example .env
```

编辑 `.env` 文件：

```env
SECRET_KEY=your-secret-key-here
DEBUG=True
ALLOWED_HOSTS=localhost,127.0.0.1
REDIS_URL=redis://localhost:6379/0
```

5. **数据库迁移**

```bash
python manage.py migrate
```

6. **创建超级用户**

```bash
python manage.py createsuperuser
```

7. **收集静态文件（生产环境）**

```bash
python manage.py collectstatic --noinput
```

8. **启动开发服务器**

```bash
# 启动 Django
python manage.py runserver

# 启动 Celery （另一个终端）
celery -A school_platform worker --loglevel=info --pool=solo
```

9. **访问系统**

- 主页：http://localhost:8000
- 管理后台：http://localhost:8000/admin

---

## 📦 部署指南

### 生产环境配置

1. **环境变量配置**

```env
SECRET_KEY=your-production-secret-key
DEBUG=False
ALLOWED_HOSTS=yourdomain.com,www.yourdomain.com
CSRF_TRUSTED_ORIGINS=https://yourdomain.com,https://www.yourdomain.com
REDIS_URL=redis://localhost:6379/0
```

2. **使用 Gunicorn 启动**

项目已包含 `gunicorn.conf.py` 配置文件：

```bash
# 使用配置文件启动
gunicorn -c gunicorn.conf.py school_platform.wsgi:application

# 或手动指定参数
gunicorn school_platform.wsgi:application --bind 0.0.0.0:8000 --workers 4
```

3. **Nginx 配置示例**

```nginx
server {
    listen 80;
    server_name yourdomain.com;

    location /static/ {
        alias /path/to/MentalHealthProject/staticfiles/;
    }

    location / {
        proxy_pass http://127.0.0.1:8000;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto $scheme;
    }
}
```

4. **Celery 守护进程（systemd）**

创建 `/etc/systemd/system/celery.service`：

```ini
[Unit]
Description=Celery Service
After=network.target

[Service]
Type=forking
User=your-user
Group=your-group
WorkingDirectory=/path/to/MentalHealthProject
Environment="PATH=/path/to/venv/bin"
ExecStart=/path/to/venv/bin/celery -A school_platform worker --detach

[Install]
WantedBy=multi-user.target
```

---

## 📚 文档

- [功能说明](DEMO_USAGE.md)
- [开源许可证](LICENSE)

---

## 🤝 贡献

欢迎贡献代码！请遵循以下流程：

1. Fork 本仓库
2. 创建特性分支 (`git checkout -b feature/AmazingFeature`)
3. 提交修改 (`git commit -m 'Add some AmazingFeature'`)
4. 推送分支 (`git push origin feature/AmazingFeature`)
5. 提交 Pull Request

---

## 📝 许可证

本项目采用 [GNU AGPL-3.0](LICENSE) 许可证。

### 主要条款

- 自由使用：任何人都可以免费使用本系统
- 自由修改：可以查看源代码并进行修改
- 自由分发：可以分享原版或修改后的版本，但必须保持相同许可证
- 网络服务义务：如果通过网络提供服务，必须向用户提供源代码

**注意：**所有衍生作品也必须以 AGPL-3.0 开源，不允许闭源商业化。

---

## 📧 联系方式

如有问题或建议，欢迎通过以下方式联系：

- 提交 [Issue](https://github.com/RTFOX2600/MentalHealthProject/issues)

---

<div align="center">

**⭐ 如果这个项目对你有帮助，请给一个 Star ⭐**

Copyright © 2026 · [MentalHealthProject](https://github.com/RTFOX2600/MentalHealthProject)

</div>
