from datetime import datetime
from typing import Optional
from fastapi import APIRouter, Depends, HTTPException, Response
from pydantic import BaseModel
from sqlalchemy.orm import Session
from backend.database.connection import get_db
from backend.database.models import UserRole, UserCycleConfig
from backend.schemas.user import UserRegister, UserLogin, TokenResponse, UserResponse, UserUpdate, ChangePassword
from backend.services.auth_service import (
    register_user, login_user, get_current_user, require_role, set_token_cookie
)
from shared.security import hash_password, verify_password
from backend.logger import get_logger

logger = get_logger(__name__)

router = APIRouter(prefix='/api/auth', tags=['auth'])


class CycleConfigRequest(BaseModel):
    cycle_length: int = 28
    last_period_date: Optional[str] = None


@router.post('/register', response_model=UserResponse)
def register(data: UserRegister, db: Session = Depends(get_db)):
    return register_user(db, data)


@router.post('/login')
def login(data: UserLogin, response: Response, db: Session = Depends(get_db)):
    """Login — returns JWT token + user, sets httpOnly cookie."""
    result = login_user(db, data)
    set_token_cookie(response, result.access_token)
    return result


@router.get('/me', response_model=UserResponse)
def get_me(current_user=Depends(get_current_user)):
    return UserResponse.model_validate(current_user)


@router.put('/me', response_model=UserResponse)
def update_me(data: UserUpdate, db: Session = Depends(get_db), current_user=Depends(get_current_user)):
    if data.phone is not None:
        current_user.phone = data.phone
    if data.avatar is not None:
        current_user.avatar = data.avatar
    if data.gender is not None:
        current_user.gender = data.gender
    db.commit()
    db.refresh(current_user)
    return UserResponse.model_validate(current_user)


@router.put('/change-password')
def change_password(data: ChangePassword, db: Session = Depends(get_db), current_user=Depends(get_current_user)):
    if not verify_password(data.old_password, current_user.password_hash):
        raise HTTPException(status_code=400, detail='原密码错误')
    current_user.password_hash = hash_password(data.new_password)
    # Invalidate all existing tokens for this user
    current_user.token_version += 1
    db.commit()
    return {'message': '密码修改成功'}


@router.get('/cycle-config')
def get_cycle_config(db: Session = Depends(get_db), current_user=Depends(get_current_user)):
    config = db.query(UserCycleConfig).filter(
        UserCycleConfig.user_id == current_user.id
    ).first()
    if not config:
        return {'cycle_length': 28, 'last_period_date': None}
    return {
        'cycle_length': config.cycle_length,
        'last_period_date': str(config.last_period_date) if config.last_period_date else None,
        'intensity_coefficient': config.intensity_coefficient,
    }


@router.put('/cycle-config')
def update_cycle_config(data: CycleConfigRequest, db: Session = Depends(get_db), current_user=Depends(get_current_user)):
    config = db.query(UserCycleConfig).filter(
        UserCycleConfig.user_id == current_user.id
    ).first()
    if not config:
        config = UserCycleConfig(user_id=current_user.id)
        db.add(config)
    config.cycle_length = data.cycle_length
    if data.last_period_date:
        try:
            config.last_period_date = datetime.strptime(data.last_period_date, '%Y-%m-%d')
        except ValueError:
            logger.warning("无效的日期格式: %s (用户 %s)", data.last_period_date, current_user.id)
            raise HTTPException(status_code=400, detail='日期格式无效，请使用 YYYY-MM-DD 格式')
    db.commit()
    db.refresh(config)
    return {'message': '周期配置已更新'}
