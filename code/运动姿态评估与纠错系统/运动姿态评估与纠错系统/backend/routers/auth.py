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
