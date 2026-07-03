from fastapi import APIRouter, Depends, Query, Body
from sqlalchemy.orm import Session
from typing import Optional, List
from backend.database.connection import get_db
from backend.database.models import User, UserRole
from backend.services.auth_service import require_role
from backend.services import admin_service

router = APIRouter(prefix='/api/admin', tags=['System Admin'])


# ── User Management ──────────────────────────────────────────────────────────

@router.get('/users')
def list_users(
    role: Optional[str] = None,
    is_active: Optional[bool] = None,
    search: Optional[str] = None,
    page: int = 1,
    page_size: int = 20,
    include_deleted: bool = False,
    db: Session = Depends(get_db),
    admin: User = Depends(require_role(UserRole.ADMIN)),
):
    return admin_service.list_users(db, role, is_active, search, page, page_size, include_deleted)


@router.put('/users/{user_id}/role')
def change_role(
    user_id: int,
    role: str = Query(...),
    db: Session = Depends(get_db),
    admin: User = Depends(require_role(UserRole.ADMIN)),
):
    return admin_service.change_role(db, user_id, role, admin)


@router.put('/users/{user_id}/status')
def toggle_status(
    user_id: int,
    is_active: bool = Query(...),
    db: Session = Depends(get_db),
    admin: User = Depends(require_role(UserRole.ADMIN)),
):
    return admin_service.toggle_status(db, user_id, is_active, admin)


@router.delete('/users/{user_id}')
def soft_delete_user(
    user_id: int,
    db: Session = Depends(get_db),
    admin: User = Depends(require_role(UserRole.ADMIN)),
):
    return admin_service.soft_delete_user(db, user_id, admin)


@router.post('/users/{user_id}/restore')
def restore_user(
    user_id: int,
    db: Session = Depends(get_db),
    admin: User = Depends(require_role(UserRole.ADMIN)),
):
    return admin_service.restore_user(db, user_id)


@router.get('/users/{user_id}')
def get_user_detail(
    user_id: int,
    db: Session = Depends(get_db),
    admin: User = Depends(require_role(UserRole.ADMIN)),
):
    return admin_service.get_user_detail(db, user_id)


@router.post('/users/batch')
def batch_operation(
    user_ids: List[int] = Body(...),
    operation: str = Body(...),
    db: Session = Depends(get_db),
    admin: User = Depends(require_role(UserRole.ADMIN)),
):
    return admin_service.batch_operation(db, user_ids, operation, admin)


# ── Dashboard ────────────────────────────────────────────────────────────────

@router.get('/dashboard')
def get_dashboard_stats(
    db: Session = Depends(get_db),
    admin: User = Depends(require_role(UserRole.ADMIN)),
):
    return admin_service.get_dashboard_stats(db)


# ── Storage ──────────────────────────────────────────────────────────────────

@router.get('/storage')
def get_storage_info(
    admin: User = Depends(require_role(UserRole.ADMIN)),
):
    return admin_service.get_storage_info()


# ── System Config ────────────────────────────────────────────────────────────

@router.get('/config')
def get_system_config(
    db: Session = Depends(get_db),
    admin: User = Depends(require_role(UserRole.ADMIN)),
):
    return admin_service.get_system_config(db)


@router.put('/config')
def update_system_config(
    data: dict = Body(...),
    db: Session = Depends(get_db),
    admin: User = Depends(require_role(UserRole.ADMIN)),
):
    return admin_service.update_system_config(db, data, admin)


# ── Logs ─────────────────────────────────────────────────────────────────────

@router.get('/logs')
def get_logs(
    limit: int = 50,
    action: Optional[str] = None,
    user_id: Optional[int] = None,
    db: Session = Depends(get_db),
    admin: User = Depends(require_role(UserRole.ADMIN)),
):
    return admin_service.get_logs(db, limit, action, user_id)


# ── Export ───────────────────────────────────────────────────────────────────

@router.get('/export/users')
def export_users_csv(
    db: Session = Depends(get_db),
    admin: User = Depends(require_role(UserRole.ADMIN)),
):
    return admin_service.export_users_csv(db)


@router.get('/export/logs')
def export_logs_csv(
    limit: int = 1000,
    db: Session = Depends(get_db),
    admin: User = Depends(require_role(UserRole.ADMIN)),
):
    return admin_service.export_logs_csv(db, limit)
