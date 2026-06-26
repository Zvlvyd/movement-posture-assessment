from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from typing import List
from backend.database.connection import get_db
from backend.database import models
from backend.database.models import User, UserRole, SystemLog
from backend.services.auth_service import get_current_user, require_role
from datetime import datetime

router = APIRouter(prefix='/api/admin', tags=['System Admin'])

@router.get('/users')
def list_users(db: Session = Depends(get_db), admin: User = Depends(require_role(UserRole.ADMIN))):
    users = db.query(User).all()
    return [{'id': u.id, 'username': u.username, 'role': u.role.value, 'is_active': u.is_active, 'created_at': str(u.created_at)} for u in users]

@router.put('/users/{user_id}/role')
def change_role(user_id: int, role: str, db: Session = Depends(get_db), admin: User = Depends(require_role(UserRole.ADMIN))):
    user = db.query(User).filter(User.id == user_id).first()
    if not user:
        raise HTTPException(status_code=404, detail='User not found')
    user.role = UserRole(role)
    db.commit()
    return {'message': f'role changed to {role}'}

@router.put('/users/{user_id}/status')
def toggle_status(user_id: int, is_active: bool, db: Session = Depends(get_db), admin: User = Depends(require_role(UserRole.ADMIN))):
    user = db.query(User).filter(User.id == user_id).first()
    if not user:
        raise HTTPException(status_code=404, detail='User not found')
    user.is_active = is_active
    db.commit()
    return {'message': f'user {"activated" if is_active else "deactivated"}'}

@router.get('/config')
def get_system_config(db: Session = Depends(get_db), admin: User = Depends(require_role(UserRole.ADMIN))):
    from config.settings import settings
    return {
        'model_path': settings.MODEL_PATH,
        'high_precision_model_path': settings.HIGH_PRECISION_MODEL_PATH,
        'device': settings.DEVICE,
    }

@router.get('/logs')
def get_logs(limit: int = 50, db: Session = Depends(get_db), admin: User = Depends(require_role(UserRole.ADMIN))):
    logs = db.query(SystemLog).order_by(SystemLog.created_at.desc()).limit(limit).all()
    return [{'id': l.id, 'user_id': l.user_id, 'action': l.action, 'ip_address': l.ip_address, 'created_at': str(l.created_at)} for l in logs]
