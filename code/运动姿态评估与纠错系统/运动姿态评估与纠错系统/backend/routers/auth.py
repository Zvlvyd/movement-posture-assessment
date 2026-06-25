from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session
from backend.database.connection import get_db
from backend.database.models import UserRole
from backend.schemas.user import UserRegister, UserLogin, TokenResponse, UserResponse, UserUpdate, ChangePassword
from backend.services.auth_service import (
    register_user, login_user, get_current_user, require_role, hash_password, verify_password
)

router = APIRouter(prefix='/api/auth', tags=['auth'])

@router.post('/register', response_model=UserResponse)
def register(data: UserRegister, db: Session = Depends(get_db)):
    return register_user(db, data)

@router.post('/login', response_model=TokenResponse)
def login(data: UserLogin, db: Session = Depends(get_db)):
    return login_user(db, data)

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
        from fastapi import HTTPException
        raise HTTPException(status_code=400, detail='Old password is incorrect')
    current_user.password_hash = hash_password(data.new_password)
    db.commit()
    return {'message': 'Password changed successfully'}


from datetime import datetime
from backend.database.models import UserCycleConfig
from pydantic import BaseModel
from typing import Optional

class CycleConfigRequest(BaseModel):
    cycle_length: int = 28
    last_period_date: Optional[str] = None

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
        except:
            pass
    db.commit()
    db.refresh(config)
    return {'message': 'cycle config updated'}
