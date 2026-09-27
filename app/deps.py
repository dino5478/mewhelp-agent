"""FastAPI 依赖：从请求中解析当前登录用户。"""

from fastapi import Depends
from fastapi.security import OAuth2PasswordBearer
from sqlalchemy.orm import Session

from app.core.exceptions import UnauthorizedError
from app.core.security import decode_access_token
from app.database import get_db
from app.models import User

# tokenUrl 指向登录接口，Swagger 的 Authorize 按钮会用到
oauth2_scheme = OAuth2PasswordBearer(tokenUrl="/users/login")


def get_current_user(
    token: str = Depends(oauth2_scheme),
    db: Session = Depends(get_db),
) -> User:
    """校验 Bearer token，取出对应用户；失败一律 401。"""
    subject = decode_access_token(token)
    try:
        user_id = int(subject)
    except ValueError as exc:
        raise UnauthorizedError("token 用户标识非法") from exc

    user = db.get(User, user_id)
    if user is None:
        raise UnauthorizedError("用户不存在")
    return user
