from datetime import datetime, timedelta, timezone
from typing import Optional
from jose import JWTError, jwt
from fastapi import Depends, HTTPException, status, Response
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from fastapi.responses import JSONResponse
from sqlalchemy.orm import Session
from config.settings import settings
from backend.database.connection import get_db
from backend.database.models import User, UserRole
from backend.schemas.user import UserRegister, UserLogin, UserResponse, TokenResponse
from shared.security import hash_password, verify_password, needs_password_upgrade
from backend.logger import get_logger

logger = get_logger(__name__)

security = HTTPBearer(auto_error=False)

ACCESS_TOKEN_COOKIE = "pose_access_token"


def create_access_token(data: dict, expires_delta: Optional[timedelta] = None) -> str:
    to_encode = data.copy()
    expire = datetime.now(timezone.utc) + (expires_delta or timedelta(minutes=settings.ACCESS_TOKEN_EXPIRE_MINUTES))
    to_encode.update({'exp': expire})
    return jwt.encode(to_encode, settings.SECRET_KEY, algorithm=settings.ALGORITHM)


def set_token_cookie(response: Response, token: str):
    """Set the JWT as an httpOnly, SameSite=Strict cookie."""
    response.set_cookie(
        key=ACCESS_TOKEN_COOKIE,
        value=token,
        max_age=settings.ACCESS_TOKEN_EXPIRE_MINUTES * 60,
        httponly=True,
        samesite="strict",
        secure=False,  # Set True in production behind TLS
        path="/",
    )


def clear_token_cookie(response: Response):
    """Remove the auth cookie (logout)."""
    response.delete_cookie(
        key=ACCESS_TOKEN_COOKIE,
        path="/",
        httponly=True,
        samesite="strict",
    )


def register_user(db: Session, data: UserRegister) -> UserResponse:
    existing = db.query(User).filter(User.username == data.username).first()
    if existing:
        raise HTTPException(status_code=400, detail='用户名已存在')
    role_str = (data.role or 'trainee').lower()
    if role_str not in ('trainee', 'coach'):
        raise HTTPException(status_code=400, detail='无效的角色类型')
    role = UserRole.COACH if role_str == 'coach' else UserRole.TRAINEE
    user = User(
        username=data.username,
        password_hash=hash_password(data.password),
        role=role,
        phone=data.phone,
        gender=data.gender
    )
    db.add(user)
    db.commit()
    db.refresh(user)
    return UserResponse.model_validate(user)


def login_user(db: Session, data: UserLogin) -> TokenResponse:
    user = db.query(User).filter(User.username == data.username).first()
    if not user or not verify_password(data.password, user.password_hash):
        raise HTTPException(status_code=401, detail='用户名或密码错误')
    if not user.is_active:
        raise HTTPException(status_code=403, detail='账户已被禁用')
    # Auto-upgrade legacy SHA-256 hashes to bcrypt
    if needs_password_upgrade(user.password_hash):
        user.password_hash = hash_password(data.password)
        db.commit()
    access_token = create_access_token(data={
        'sub': str(user.id),
        'role': user.role.value,
        'tv': user.token_version,
    })
    return TokenResponse(access_token=access_token, user=UserResponse.model_validate(user))


def get_current_user(
    credentials: Optional[HTTPAuthorizationCredentials] = Depends(security),
    db: Session = Depends(get_db)
) -> User:
    token = None
    if credentials:
        token = credentials.credentials
    if not token:
        raise HTTPException(status_code=401, detail='未提供认证令牌')

    try:
        payload = jwt.decode(token, settings.SECRET_KEY, algorithms=[settings.ALGORITHM])
        user_id: str = payload.get('sub')
        token_version: int = payload.get('tv', 0)
        if user_id is None:
            raise HTTPException(status_code=401, detail='无效的令牌')
    except JWTError:
        raise HTTPException(status_code=401, detail='无效的令牌')

    user = db.query(User).filter(User.id == int(user_id)).first()
    if not user:
        raise HTTPException(status_code=401, detail='用户不存在')
    if not user.is_active:
        raise HTTPException(status_code=403, detail='账户已被禁用')
    if user.token_version != token_version:
        raise HTTPException(status_code=401, detail='令牌已失效，请重新登录')

    return user


def require_role(*roles: UserRole):
    def checker(current_user: User = Depends(get_current_user)):
        if current_user.role not in roles:
            raise HTTPException(status_code=403, detail='权限不足')
        return current_user
    return checker
