# -*- coding: utf-8 -*-
"""
Admin management service — user management, dashboard, system config, logs.

Extracted from routers/admin.py to maintain clean layered architecture.
"""
import csv
import io
import os
from datetime import datetime, timedelta
from typing import List, Optional

from sqlalchemy import func
from sqlalchemy.orm import Session
from fastapi import HTTPException
from fastapi.responses import StreamingResponse

from backend.database.models import (
    User, UserRole, SystemLog, SystemConfig,
    ClassGroup, FMSRecord, AssessmentRecord, CheckInCard,
)
from backend.database.models_v2 import PrescriptionPlan


# ── User Management ──────────────────────────────────────────────────────────

def list_users(
    db: Session,
    role: Optional[str] = None,
    is_active: Optional[bool] = None,
    search: Optional[str] = None,
    page: int = 1,
    page_size: int = 20,
    include_deleted: bool = False,
) -> dict:
    """List users with filtering, pagination, and soft-delete support."""
    q = db.query(User)

    if not include_deleted:
        q = q.filter(User.deleted_at.is_(None))

    if role:
        try:
            q = q.filter(User.role == UserRole(role))
        except ValueError:
            raise HTTPException(status_code=400, detail=f'Invalid role: {role}')

    if is_active is not None:
        q = q.filter(User.is_active == is_active)

    if search:
        like = f'%{search}%'
        q = q.filter(
            (User.username.like(like)) | (User.phone.like(like))
        )

    total = q.count()
    users = (
        q.order_by(User.created_at.desc())
        .offset((page - 1) * page_size)
        .limit(page_size)
        .all()
    )

    return {
        'items': [
            {
                'id': u.id,
                'username': u.username,
                'role': u.role.value,
                'phone': u.phone,
                'gender': u.gender,
                'is_active': u.is_active,
                'last_login_at': str(u.last_login_at) if u.last_login_at else None,
                'last_active_at': str(u.last_active_at) if u.last_active_at else None,
                'created_at': str(u.created_at),
                'deleted_at': str(u.deleted_at) if u.deleted_at else None,
            }
            for u in users
        ],
        'total': total,
        'page': page,
        'page_size': page_size,
    }


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

    old_role = user.role.value
    user.role = new_role
    db.commit()
    return {'message': f'Role changed from {old_role} to {role}'}


def toggle_status(db: Session, user_id: int, is_active: bool, admin: User) -> dict:
    """Toggle user active status. Prevents admin from deactivating themselves."""
    user = db.query(User).filter(User.id == user_id).first()
    if not user:
        raise HTTPException(status_code=404, detail='User not found')

    if user.id == admin.id and not is_active:
        raise HTTPException(status_code=400, detail='Cannot deactivate yourself')

    user.is_active = is_active
    db.commit()
    return {'message': f'User {"activated" if is_active else "deactivated"}'}


def soft_delete_user(db: Session, user_id: int, admin: User) -> dict:
    """Soft-delete a user (sets deleted_at timestamp)."""
    user = db.query(User).filter(User.id == user_id, User.deleted_at.is_(None)).first()
    if not user:
        raise HTTPException(status_code=404, detail='User not found or already deleted')

    if user.id == admin.id:
        raise HTTPException(status_code=400, detail='Cannot delete yourself')

    user.deleted_at = datetime.utcnow()
    user.is_active = False
    db.commit()
    return {'message': f'User {user.username} deleted'}


def restore_user(db: Session, user_id: int) -> dict:
    """Restore a soft-deleted user."""
    user = db.query(User).filter(User.id == user_id, User.deleted_at.isnot(None)).first()
    if not user:
        raise HTTPException(status_code=404, detail='User not found or not deleted')

    user.deleted_at = None
    user.is_active = True
    db.commit()
    return {'message': f'User {user.username} restored'}


def get_user_detail(db: Session, user_id: int) -> dict:
    """Get a user's full profile with stats."""
    user = db.query(User).filter(User.id == user_id, User.deleted_at.is_(None)).first()
    if not user:
        raise HTTPException(status_code=404, detail='User not found')

    # Count related records
    fms_count = db.query(func.count(FMSRecord.id)).filter(FMSRecord.user_id == user_id).scalar()
    assessment_count = db.query(func.count(AssessmentRecord.id)).filter(AssessmentRecord.user_id == user_id).scalar()
    prescription_count = db.query(func.count(PrescriptionPlan.id)).filter(PrescriptionPlan.user_id == user_id).scalar()
    checkin_count = db.query(func.count(CheckInCard.id)).filter(CheckInCard.user_id == user_id).scalar()

    # Get latest streak
    latest_checkin = (
        db.query(CheckInCard)
        .filter(CheckInCard.user_id == user_id)
        .order_by(CheckInCard.date.desc())
        .first()
    )
    streak = latest_checkin.streak_days if latest_checkin else 0

    # Get class memberships
    classes = (
        db.query(ClassGroup)
        .join(ClassGroup.students)
        .filter(User.id == user_id)
        .all()
    )

    return {
        'id': user.id,
        'username': user.username,
        'role': user.role.value,
        'phone': user.phone,
        'gender': user.gender,
        'is_active': user.is_active,
        'last_login_at': str(user.last_login_at) if user.last_login_at else None,
        'last_active_at': str(user.last_active_at) if user.last_active_at else None,
        'created_at': str(user.created_at),
        'stats': {
            'fms_records': fms_count,
            'assessments': assessment_count,
            'prescriptions': prescription_count,
            'checkins': checkin_count,
            'streak_days': streak,
            'classes': [{'id': c.id, 'name': c.name} for c in classes],
        },
    }


def batch_operation(db: Session, user_ids: List[int], operation: str, admin: User) -> dict:
    """Batch operation: activate, deactivate, or change_role."""
    if operation not in ('activate', 'deactivate', 'make_coach', 'make_trainee'):
        raise HTTPException(status_code=400, detail=f'Unknown operation: {operation}')

    users = db.query(User).filter(User.id.in_(user_ids), User.deleted_at.is_(None)).all()
    affected = 0

    for user in users:
        if user.id == admin.id:
            continue  # Skip self
        if operation == 'activate':
            user.is_active = True
        elif operation == 'deactivate':
            user.is_active = False
        elif operation == 'make_coach':
            user.role = UserRole.COACH
        elif operation == 'make_trainee':
            user.role = UserRole.TRAINEE
        affected += 1

    db.commit()
    return {'message': f'{operation} applied to {affected} users'}


# ── Dashboard & Statistics ───────────────────────────────────────────────────

def get_dashboard_stats(db: Session) -> dict:
    """Aggregated dashboard statistics for admin overview."""
    now = datetime.utcnow()

    # User counts
    total_users = db.query(func.count(User.id)).filter(User.deleted_at.is_(None)).scalar() or 0
    active_users = db.query(func.count(User.id)).filter(
        User.deleted_at.is_(None), User.is_active == True
    ).scalar() or 0
    deleted_count = db.query(func.count(User.id)).filter(
        User.deleted_at.isnot(None)
    ).scalar() or 0

    # Role distribution
    role_dist = {}
    for r in UserRole:
        role_dist[r.value] = (
            db.query(func.count(User.id))
            .filter(User.deleted_at.is_(None), User.role == r)
            .scalar() or 0
        )

    # Registration trend (last 30 days)
    thirty_days_ago = now - timedelta(days=30)
    reg_trend_rows = (
        db.query(
            func.date(User.created_at).label('date'),
            func.count(User.id).label('count'),
        )
        .filter(User.created_at >= thirty_days_ago, User.deleted_at.is_(None))
        .group_by(func.date(User.created_at))
        .order_by('date')
        .all()
    )
    registration_trend = [{'date': str(row.date), 'count': row.count} for row in reg_trend_rows]

    # DAU (today), WAU (7 days), MAU (30 days)
    dau = (
        db.query(func.count(func.distinct(User.id)))
        .filter(
            User.deleted_at.is_(None),
            User.last_active_at >= now.replace(hour=0, minute=0, second=0, microsecond=0),
        )
        .scalar() or 0
    )

    wau_start = now - timedelta(days=7)
    wau = (
        db.query(func.count(func.distinct(User.id)))
        .filter(User.deleted_at.is_(None), User.last_active_at >= wau_start)
        .scalar() or 0
    )

    mau_start = now - timedelta(days=30)
    mau = (
        db.query(func.count(func.distinct(User.id)))
        .filter(User.deleted_at.is_(None), User.last_active_at >= mau_start)
        .scalar() or 0
    )

    # DAU trend (last 7 days)
    dau_trend_rows = (
        db.query(
            func.date(User.last_active_at).label('date'),
            func.count(func.distinct(User.id)).label('count'),
        )
        .filter(User.last_active_at >= wau_start, User.deleted_at.is_(None))
        .group_by(func.date(User.last_active_at))
        .order_by('date')
        .all()
    )
    dau_trend = [{'date': str(row.date), 'count': row.count} for row in dau_trend_rows]

    # System activity counts
    fms_total = db.query(func.count(FMSRecord.id)).scalar() or 0
    assessment_total = db.query(func.count(AssessmentRecord.id)).scalar() or 0
    prescription_total = db.query(func.count(PrescriptionPlan.id)).scalar() or 0
    checkin_total = db.query(func.count(CheckInCard.id)).scalar() or 0

    # API request stats from SystemLog (last 7 days)
    api_rows = (
        db.query(SystemLog.action, func.count(SystemLog.id).label('count'))
        .filter(SystemLog.created_at >= wau_start)
        .group_by(SystemLog.action)
        .order_by(func.count(SystemLog.id).desc())
        .limit(20)
        .all()
    )
    api_stats = [{'action': row.action, 'count': row.count} for row in api_rows]

    # Error rate (actions containing 'error' or 'fail')
    total_logs = db.query(func.count(SystemLog.id)).filter(
        SystemLog.created_at >= wau_start
    ).scalar() or 0
    error_logs = db.query(func.count(SystemLog.id)).filter(
        SystemLog.created_at >= wau_start,
        (SystemLog.action.ilike('%error%')) | (SystemLog.action.ilike('%fail%')),
    ).scalar() or 0
    error_rate = round(error_logs / total_logs * 100, 2) if total_logs > 0 else 0.0

    return {
        'total_users': total_users,
        'active_users': active_users,
        'deleted_users': deleted_count,
        'role_distribution': role_dist,
        'dau': dau,
        'wau': wau,
        'mau': mau,
        'registration_trend': registration_trend,
        'dau_trend': dau_trend,
        'system_activity': {
            'fms_screens': fms_total,
            'assessments': assessment_total,
            'prescriptions': prescription_total,
            'checkins': checkin_total,
        },
        'api_stats': api_stats,
        'error_rate': error_rate,
    }


def get_storage_info() -> dict:
    """Get storage usage for uploads and model directories."""
    project_root = os.path.abspath(
        os.path.join(os.path.dirname(__file__), '..', '..')
    )

    def dir_size(path: str) -> int:
        total = 0
        if not os.path.exists(path):
            return 0
        for dirpath, _, filenames in os.walk(path):
            for f in filenames:
                fp = os.path.join(dirpath, f)
                try:
                    total += os.path.getsize(fp)
                except OSError:
                    pass
        return total

    uploads_path = os.path.join(project_root, 'uploads')
    models_path = os.path.join(project_root)

    uploads_size = dir_size(uploads_path)

    # Model files
    model_files = {}
    for fname in ['yolov8n-pose.pt', 'yolov8s-pose.pt']:
        fp = os.path.join(models_path, fname)
        if os.path.exists(fp):
            model_files[fname] = os.path.getsize(fp)

    return {
        'uploads_size_mb': round(uploads_size / (1024 * 1024), 2),
        'uploads_size_bytes': uploads_size,
        'model_files': {
            name: {'size_mb': round(size / (1024 * 1024), 2), 'size_bytes': size}
            for name, size in model_files.items()
        },
    }


# ── System Config ────────────────────────────────────────────────────────────

CONFIG_WHITELIST = {
    'model_path', 'high_precision_model_path', 'device',
    'rate_limit_auth_per_minute', 'assessment_confidence_threshold',
}


def get_system_config(db: Session) -> dict:
    """Get all system config entries."""
    rows = db.query(SystemConfig).all()
    result = {}
    for row in rows:
        result[row.config_key] = {
            'value': row.config_value,
            'description': row.description,
            'updated_at': str(row.updated_at) if row.updated_at else None,
        }
    return result


def update_system_config(db: Session, data: dict, admin: User) -> dict:
    """Upsert system config entries. Only whitelisted keys are allowed."""
    updated = []
    for key, value in data.items():
        if key not in CONFIG_WHITELIST:
            raise HTTPException(status_code=400, detail=f'Config key not editable: {key}')

        row = db.query(SystemConfig).filter(SystemConfig.config_key == key).first()
        if row:
            row.config_value = str(value)
            row.updated_by = admin.id
            row.updated_at = datetime.utcnow()
        else:
            db.add(SystemConfig(
                config_key=key,
                config_value=str(value),
                updated_by=admin.id,
            ))
        updated.append(key)

    db.commit()
    return {'message': f'Updated config keys: {updated}'}


# ── Logs ─────────────────────────────────────────────────────────────────────

def get_logs(
    db: Session,
    limit: int = 50,
    action_filter: Optional[str] = None,
    user_id: Optional[int] = None,
) -> List[dict]:
    """Get recent system logs with optional filters."""
    q = db.query(SystemLog).order_by(SystemLog.created_at.desc())

    if action_filter:
        q = q.filter(SystemLog.action.ilike(f'%{action_filter}%'))
    if user_id:
        q = q.filter(SystemLog.user_id == user_id)

    logs = q.limit(limit).all()
    return [
        {
            'id': l.id,
            'user_id': l.user_id,
            'action': l.action,
            'detail': l.detail,
            'ip_address': l.ip_address,
            'created_at': str(l.created_at),
        }
        for l in logs
    ]


# ── Export ───────────────────────────────────────────────────────────────────

def export_users_csv(db: Session) -> StreamingResponse:
    """Export all non-deleted users as CSV."""
    users = db.query(User).filter(User.deleted_at.is_(None)).order_by(User.id).all()

    output = io.StringIO()
    writer = csv.writer(output)
    writer.writerow(['ID', '用户名', '角色', '手机', '性别', '状态', '注册时间', '最后登录'])
    for u in users:
        writer.writerow([
            u.id,
            u.username,
            u.role.value,
            u.phone or '',
            u.gender or '',
            '活跃' if u.is_active else '停用',
            str(u.created_at),
            str(u.last_login_at) if u.last_login_at else '',
        ])

    output.seek(0)
    return StreamingResponse(
        iter([output.getvalue()]),
        media_type='text/csv',
        headers={'Content-Disposition': 'attachment; filename=users_export.csv'},
    )


def export_logs_csv(db: Session, limit: int = 1000) -> StreamingResponse:
    """Export recent logs as CSV."""
    logs = db.query(SystemLog).order_by(SystemLog.created_at.desc()).limit(limit).all()

    output = io.StringIO()
    writer = csv.writer(output)
    writer.writerow(['ID', '用户ID', '操作', '详情', 'IP地址', '时间'])
    for l in logs:
        writer.writerow([
            l.id,
            l.user_id or '',
            l.action,
            l.detail or '',
            l.ip_address or '',
            str(l.created_at),
        ])

    output.seek(0)
    return StreamingResponse(
        iter([output.getvalue()]),
        media_type='text/csv',
        headers={'Content-Disposition': 'attachment; filename=logs_export.csv'},
    )
