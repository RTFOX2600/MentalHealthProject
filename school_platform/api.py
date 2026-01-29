from ninja import NinjaAPI
from django.contrib.admin.views.decorators import staff_member_required

# 创建 API 实例，设置标题和版本
# docs_url="/docs" 意味着 Swagger 文档将直接出现在 /api/docs
api = NinjaAPI(
    title="精准思政系统 API",
    version="1.0.0",
    description="基于 Django Ninja 自动生成的交互式接口文档",
)

# 注册各个模块的 router
from mental_health.api import router as mental_health_router
from accounts.api import router as accounts_router

api.add_router("/mental-health/", mental_health_router)
api.add_router("/accounts/", accounts_router)
