"""安全工具：密码哈希（bcrypt）与 JWT 的签发 / 校验。"""

from datetime import datetime, timedelta, timezone

import bcrypt
import jwt

from app.core.config import settings
from app.core.exceptions import UnauthorizedError


def hash_password(raw: str) -> str:
    """把明文密码哈希后存库（不可逆）。"""
    return bcrypt.hashpw(raw.encode(), bcrypt.gensalt()).decode()


def verify_password(raw: str, hashed: str) -> bool:
    """校验明文密码与库中哈希是否匹配。"""
    try:
        return bcrypt.checkpw(raw.encode(), hashed.encode())
    except ValueError:
        return False


def create_access_token(subject: str) -> str:
    """签发 JWT。subject 一般放用户 id；exp 是过期时间。"""
    expire = datetime.now(timezone.utc) + timedelta(minutes=settings.ACCESS_TOKEN_EXPIRE_MINUTES)
    payload = {"sub": subject, "exp": expire}
    return jwt.encode(payload, settings.SECRET_KEY, algorithm=settings.ALGORITHM)


def decode_access_token(token: str) -> str:
    """校验并解析 JWT，返回 subject（用户 id）。失败抛 401。"""
    try:
        payload = jwt.decode(token, settings.SECRET_KEY, algorithms=[settings.ALGORITHM])
    except jwt.PyJWTError as exc:
        raise UnauthorizedError("token 无效或已过期") from exc
    subject = payload.get("sub")
    if subject is None:
        raise UnauthorizedError("token 缺少用户标识")
    return subject
