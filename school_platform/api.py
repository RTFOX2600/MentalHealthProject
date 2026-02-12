from ninja import NinjaAPI
from ninja.openapi.docs import Swagger
from django.contrib.admin.views.decorators import staff_member_required

from mental_health.api import router as mental_health_router


# 创建 API 实例，设置标题和版本
# docs_url="/docs" 意味着 Swagger 文档将直接出现在 /api/docs
api = NinjaAPI(
    title="精准思政系统 API",
    version="1.0.0",
    description="基于 Django Ninja 自动生成的交互式接口文档",
    docs=Swagger(settings={
        "swagger_ui_bundle_js": "https://unpkg.com/swagger-ui-dist@5/swagger-ui-bundle.js",
        "swagger_ui_css": "https://unpkg.com/swagger-ui-dist@5/swagger-ui.css",
    })
)

# 注册各个模块的 router
api.add_router("/mental-health/", mental_health_router)
