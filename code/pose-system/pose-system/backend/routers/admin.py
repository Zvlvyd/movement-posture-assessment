from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session
from backend.database.connection import get_db
from backend.database.models import User, UserRole
from backend.services.auth_service import require_role
from backend.services import admin_service

router = APIRouter(prefix='/api/admin', tags=['System Admin'])


@router.get('/users')
def list_users(
    db: Session = Depends(get_db),
    admin: User = Depends(require_role(UserRole.ADMIN)),
):
    return admin_service.list_users(db)


@router.put('/users/{user_id}/role')
def change_role(
    user_id: int,
    role: str,
    db: Session = Depends(get_db),
    admin: User = Depends(require_role(UserRole.ADMIN)),
):
    return admin_service.change_role(db, user_id, role, admin)


@router.put('/users/{user_id}/status')
def toggle_status(
    user_id: int,
    is_active: bool,
    db: Session = Depends(get_db),
    admin: User = Depends(require_role(UserRole.ADMIN)),
):
    return admin_service.toggle_status(db, user_id, is_active, admin)


@router.get('/config')
def get_system_config(
    admin: User = Depends(require_role(UserRole.ADMIN)),
):
    return admin_service.get_system_config()


@router.get('/logs')
def get_logs(
    limit: int = 50,
    db: Session = Depends(get_db),
    admin: User = Depends(require_role(UserRole.ADMIN)),
):
    return admin_service.get_logs(db, limit)
