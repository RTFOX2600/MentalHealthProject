from django.db import models
from django.contrib.auth import get_user_model

User = get_user_model()

# 所有旧的数据分析模型已迁移至 staff_dashboard 应用
# 保留此文件以避免导入错误
