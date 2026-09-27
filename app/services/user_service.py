"""用户业务逻辑：注册与认证。"""

from sqlalchemy.orm import Session

from app.core.exceptions import ConflictError, UnauthorizedError
from app.core.security import hash_password, verify_password
from app.models import User


def create_user(db: Session, username: str, password: str) -> User:
    if db.query(User).filter_by(username=username).first() is not None:
        raise ConflictError("用户名已存在")
    user = User(username=username, password_hash=hash_password(password))
    db.add(user)
    db.commit()
    db.refresh(user)
    return user


def authenticate(db: Session, username: str, password: str) -> User:
    user = db.query(User).filter_by(username=username).first()
    if user is None or not verify_password(password, user.password_hash):
        raise UnauthorizedError("用户名或密码错误")
    return user
