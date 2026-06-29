# -*- coding: utf-8 -*-
"""
Admin management service — user management, system config, logs.

Extracted from routers/admin.py to maintain clean layered architecture.
"""
from typing import List

from sqlalchemy.orm import Session
from fastapi import HTTPException

from backend.database.models import User, UserRole, SystemLog


def list_users(db: Session) -> List[dict]:
    """List all users."""
    users = db.query(User).all()
    return [
        {
            'id': u.id,
            'username': u.username,
            'role': u.role.value,
            'is_active': u.is_active,
            'created_at': str(u.created_at),
        }
        for u in users
    ]


def change_role(db: Session, user_id: int, role: str, admin: User) -> dict:
    """Change a user's role. Prevents admin from demoting themselves."""
    user = db.query(User).filter(User.id == user_id).first()
    if not user:
        raise HTTPException(status_code=404, detail='User not found')

    try:
        new_role = UserRole(role)
    except ValueError:
        raise HTTPException(
            status_code=400,
            detail=f'Invalid role: {role}. Must be one of: {[r.value for r in UserRole]}',
        )

    if user.id == admin.id:
        raise HTTPException(status_code=400, detail='Cannot change your own role')

    user.role = new_role
    db.commit()
    return {'message': f'role changed to {role}'}


def toggle_status(db: Session, user_id: int, is_active: bool, admin: User) -> dict:
    """Toggle user active status. Prevents admin from deactivating themselves."""
    user = db.query(User).filter(User.id == user_id).first()
    if not user:
        raise HTTPException(status_code=404, detail='User not found')

    if user.id == admin.id and not is_active:
        raise HTTPException(status_code=400, detail='Cannot deactivate yourself')

    user.is_active = is_active
    db.commit()
    return {'message': f'user {"activated" if is_active else "deactivated"}'}


def get_system_config() -> dict:
    """Get system configuration."""
    from config.settings import settings
    return {
        'model_path': settings.MODEL_PATH,
        'high_precision_model_path': settings.HIGH_PRECISION_MODEL_PATH,
        'device': settings.DEVICE,
    }


def get_logs(db: Session, limit: int = 50) -> List[dict]:
    """Get recent system logs."""
    logs = db.query(SystemLog).order_by(SystemLog.created_at.desc()).limit(limit).all()
    return [
        {
            'id': l.id,
            'user_id': l.user_id,
            'action': l.action,
            'ip_address': l.ip_address,
            'created_at': str(l.created_at),
        }
        for l in logs
    ]
