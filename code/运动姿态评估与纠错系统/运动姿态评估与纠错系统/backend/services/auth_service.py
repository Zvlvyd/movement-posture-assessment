from datetime import datetime, timedelta
from typing import Optional
from jose import JWTError, jwt
from fastapi import Depends, HTTPException, status
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from sqlalchemy.orm import Session
import hashlib
import secrets
from backend.config import settings
from backend.database.connection import get_db
from backend.database.models import User, UserRole
from backend.schemas.user import UserRegister, UserLogin, UserResponse, TokenResponse

security = HTTPBearer()

def hash_password(password: str) -> str:
    salt = secrets.token_hex(16)
    h = hashlib.sha256((salt + password).encode()).hexdigest()
    return salt + '$' + h

def verify_password(plain: str, hashed: str) -> bool:
    parts = hashed.split('$')
    if len(parts) != 2:
        return False
    salt, h = parts
    return hashlib.sha256((salt + plain).encode()).hexdigest() == h

def create_access_token(data: dict, expires_delta: Optional[timedelta] = None) -> str:
    to_encode = data.copy()
    expire = datetime.utcnow() + (expires_delta or timedelta(minutes=settings.ACCESS_TOKEN_EXPIRE_MINUTES))
    to_encode.update({'exp': expire})
    return jwt.encode(to_encode, settings.SECRET_KEY, algorithm=settings.ALGORITHM)

def register_user(db: Session, data: UserRegister) -> UserResponse:
    existing = db.query(User).filter(User.username == data.username).first()
    if existing:
        raise HTTPException(status_code=400, detail='Username already exists')
    user = User(
        username=data.username,
        password_hash=hash_password(data.password),
        role=UserRole.TRAINEE,
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
        raise HTTPException(status_code=401, detail='Invalid username or password')
    if not user.is_active:
        raise HTTPException(status_code=403, detail='Account is disabled')
    access_token = create_access_token(data={'sub': str(user.id), 'role': user.role.value})
    return TokenResponse(access_token=access_token, user=UserResponse.model_validate(user))

def get_current_user(
    credentials: HTTPAuthorizationCredentials = Depends(security),
    db: Session = Depends(get_db)
) -> User:
    token = credentials.credentials
    try:
        payload = jwt.decode(token, settings.SECRET_KEY, algorithms=[settings.ALGORITHM])
        user_id: str = payload.get('sub')
        if user_id is None:
            raise HTTPException(status_code=401, detail='Invalid token')
    except JWTError:
        raise HTTPException(status_code=401, detail='Invalid token')
    user = db.query(User).filter(User.id == int(user_id)).first()
    if not user:
        raise HTTPException(status_code=401, detail='User not found')
    if not user.is_active:
        raise HTTPException(status_code=403, detail='Account is disabled')
    return user

def require_role(*roles: UserRole):
    def checker(current_user: User = Depends(get_current_user)):
        if current_user.role not in roles:
            raise HTTPException(status_code=403, detail='Insufficient permissions')
        return current_user
    return checker
