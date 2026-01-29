from ninja import Router, Schema
from django.contrib.auth import logout

router = Router(tags=["用户账户管理"])

class ProfileSchema(Schema):
    username: str
    first_name: str = None
    last_name: str = None
    phone_number: str = None

class MessageResponse(Schema):
    message: str


@router.get("/me", response=ProfileSchema)
def get_me(request):
    """
    获取当前登录用户的资料。
    """
    return request.user


@router.post("/update-profile", response=MessageResponse)
def update_profile(request, data: ProfileSchema):
    """
    更新当前用户的个人资料。
    """
    user = request.user
    for attr, value in data.dict(exclude_unset=True).items():
        setattr(user, attr, value)
    user.save()
    return {"message": "个人资料已成功更新"}


@router.post("/delete-account", response=MessageResponse)
def delete_account_api(request):
    """
    注销（删除）当前用户的账号。
    注意：在实际调用前应进行密码或二次验证。
    """
    user = request.user
    logout(request)
    user.delete()
    return {"message": "您的账号已成功注销"}
