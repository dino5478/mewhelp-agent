"""用户路由：注册 / 登录 / 查询当前用户。"""

from fastapi import APIRouter, Depends
from fastapi.security import OAuth2PasswordRequestForm
from sqlalchemy.orm import Session

from app.core.security import create_access_token
from app.database import get_db
from app.deps import get_current_user
from app.models import User
from app.schemas.user import Token, UserCreate, UserOut
from app.services import user_service

router = APIRouter(prefix="/users", tags=["users"])


@router.post("/register", response_model=UserOut, status_code=201)
def register(payload: UserCreate, db: Session = Depends(get_db)) -> User:
    return user_service.create_user(db, payload.username, payload.password)


@router.post("/login", response_model=Token)
def login(
    form_data: OAuth2PasswordRequestForm = Depends(),
    db: Session = Depends(get_db),
) -> Token:
    user = user_service.authenticate(db, form_data.username, form_data.password)
    return Token(access_token=create_access_token(str(user.id)))


@router.get("/me", response_model=UserOut)
def me(current_user: User = Depends(get_current_user)) -> User:
    return current_user
