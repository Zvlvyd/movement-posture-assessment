# -*- coding: utf-8 -*-
"""
Coach management service — class CRUD, student management, statistics.

Extracted from routers/coach.py to maintain clean layered architecture:
  routers (thin) → services (logic) → database/models
"""
import secrets
import string as _string
from datetime import datetime, timedelta
from collections import defaultdict
from typing import Optional, List

from sqlalchemy.orm import Session
from fastapi import HTTPException

from backend.database import models
from backend.database.models import (
    User, UserRole, ClassGroup, class_group_student,
    FMSRecord, AssessmentRecord, CheckInCard,
    Prescription, PrescriptionItem, PrescriptionStatus,
)


import json as _json

# ── Helpers ─────────────────────────────────────────────────────────────

def _parse_json(value):
    """Parse JSON string to dict/list, or return as-is if already parsed."""
    if value is None:
        return None
    if isinstance(value, (dict, list)):
        return value
    if isinstance(value, str):
        try:
            return _json.loads(value)
        except (_json.JSONDecodeError, TypeError):
            return value
    return value

def _generate_unique_invite_code(db: Session) -> str:
    """生成 8 位唯一邀请码（大写字母+数字），碰撞时重试最多10次"""
    chars = _string.ascii_uppercase + _string.digits
    for _ in range(10):
        code = ''.join(secrets.choice(chars) for _ in range(8))
        if not db.query(ClassGroup).filter(ClassGroup.invite_code == code).first():
            return code
    raise HTTPException(status_code=500, detail="无法生成唯一邀请码，请重试")


def _serialize_student_brief(user: User, class_id: int = None, class_name: str = None) -> dict:
    """Serialize a student into a brief dict for list views."""
    d = {'id': user.id, 'username': user.username, 'phone': user.phone}
    if class_name:
        d['class_id'] = class_id
        d['class'] = class_name
    return d


def _serialize_fms(record) -> Optional[dict]:
    """Serialize an FMS/Assessment record into a scores dict."""
    if not record:
        return None
    return {
        'balance': record.balance_score,
        'flexibility': record.flexibility_score,
        'upper_limb': record.upper_limb_score,
        'core': record.core_score,
        'symmetry': record.symmetry_score,
        'overall': record.overall_score,
    }


# ── Student listing ────────────────────────────────────────────────────

def list_students(db: Session, coach: User, class_id: int = None) -> List[dict]:
    """List students, optionally filtered by class."""
    if class_id:
        group = db.query(ClassGroup).filter(
            ClassGroup.id == class_id,
            ClassGroup.coach_id == coach.id,
        ).first()
        if not group:
            raise HTTPException(status_code=404, detail='Class not found')
        return [_serialize_student_brief(s, class_id=group.id, class_name=group.name) for s in group.students]

    groups = db.query(ClassGroup).filter(ClassGroup.coach_id == coach.id).all()
    students = []
    for g in groups:
        for s in g.students:
            students.append(_serialize_student_brief(s, class_id=g.id, class_name=g.name))
    return students


# ── Class CRUD ─────────────────────────────────────────────────────────

def create_class(db: Session, coach: User, name: str, description: str = '') -> dict:
    """Create a new class group with auto-generated invite code."""
    invite_code = _generate_unique_invite_code(db)
    group = ClassGroup(coach_id=coach.id, name=name, description=description, invite_code=invite_code)
    db.add(group)
    db.commit()
    db.refresh(group)
    return {'id': group.id, 'name': group.name, 'invite_code': group.invite_code}


def list_classes(db: Session, coach: User) -> List[dict]:
    """List all classes with overview statistics."""
    groups = db.query(ClassGroup).filter(ClassGroup.coach_id == coach.id).all()
    return [
        {
            'id': g.id,
            'name': g.name,
            'description': g.description,
            'invite_code': g.invite_code,
            'student_count': len(g.students),
            'created_at': str(g.created_at),
        }
        for g in groups
    ]


def add_student_to_class(db: Session, coach: User, class_id: int, student_id: int) -> dict:
    """Add a trainee to a class group."""
    group = db.query(ClassGroup).filter(
        ClassGroup.id == class_id,
        ClassGroup.coach_id == coach.id,
    ).first()
    if not group:
        raise HTTPException(status_code=404, detail='Class not found')

    student = db.query(User).filter(
        User.id == student_id,
        User.role == UserRole.TRAINEE,
    ).first()
    if not student:
        raise HTTPException(status_code=404, detail='Student not found')

    if student not in group.students:
        group.students.append(student)
        db.commit()
    return {'message': 'student added'}


def remove_student_from_class(db: Session, coach: User, class_id: int, student_id: int) -> dict:
    """Remove a trainee from a class group."""
    group = db.query(ClassGroup).filter(
        ClassGroup.id == class_id,
        ClassGroup.coach_id == coach.id,
    ).first()
    if not group:
        raise HTTPException(status_code=404, detail='Class not found')

    student = db.query(User).filter(User.id == student_id).first()
    if not student:
        raise HTTPException(status_code=404, detail='Student not found')

    if student in group.students:
        group.students.remove(student)
        db.commit()
    return {'message': 'student removed'}


def update_class(db: Session, coach: User, class_id: int, name: str = None, description: str = None) -> dict:
    """Update a class group's name and/or description."""
    group = db.query(ClassGroup).filter(
        ClassGroup.id == class_id,
        ClassGroup.coach_id == coach.id,
    ).first()
    if not group:
        raise HTTPException(status_code=404, detail='Class not found')

    if name is not None:
        group.name = name
    if description is not None:
        group.description = description
    db.commit()
    return {'id': group.id, 'name': group.name, 'description': group.description}


def delete_class(db: Session, coach: User, class_id: int) -> dict:
    """Delete a class group (cascade removes student associations)."""
    group = db.query(ClassGroup).filter(
        ClassGroup.id == class_id,
        ClassGroup.coach_id == coach.id,
    ).first()
    if not group:
        raise HTTPException(status_code=404, detail='Class not found')

    db.delete(group)
    db.commit()
    return {'message': f'Class "{group.name}" deleted'}


# ── Student Prescription Management ──────────────────────────────────────

def get_student_prescription_plans(db: Session, student_id: int, coach: User) -> List[dict]:
    """Get all v2 prescription plans for a student with full item details."""
    student = _verify_coach_access(db, student_id, coach)

    from backend.database.models_v2 import PrescriptionPlan, TrainingCompletion
    from sqlalchemy import func

    plans = db.query(PrescriptionPlan).filter(
        PrescriptionPlan.user_id == student_id,
    ).order_by(PrescriptionPlan.created_at.desc()).all()

    result = []
    for p in plans:
        items = []
        for item in (p.items or []):
            # 获取该 plan_item 的训练完成次数
            completions = db.query(func.count(TrainingCompletion.id)).filter(
                TrainingCompletion.plan_item_id == item.id,
            ).scalar() or 0

            # 获取最新评分
            latest = db.query(TrainingCompletion).filter(
                TrainingCompletion.plan_item_id == item.id,
            ).order_by(TrainingCompletion.created_at.desc()).first()

            items.append({
                'id': item.id,
                'action_id': item.action_id,
                'action_name': item.action_name,
                'family_name': item.family_name,
                'category': item.category,
                'phase': item.phase,
                'sets': item.sets,
                'reps': item.reps,
                'duration_seconds': item.duration_seconds,
                'order_index': item.order_index,
                'difficulty': item.difficulty,
                'intensity': item.intensity,
                'notes': item.notes,
                'is_substitution': item.is_substitution,
                'completions': completions,
                'latest_score': latest.best_score if latest else None,
            })

        result.append({
            'id': p.id,
            'plan_name': p.plan_name,
            'status': p.status,
            'generation_method': p.generation_method,
            'overall_strategy': p.overall_strategy,
            'created_at': str(p.created_at),
            'item_count': len(items),
            'items': items,
        })
    return result


def get_student_plan_detail(db: Session, student_id: int, plan_id: int, coach: User) -> dict:
    """Get full detail of a v2 prescription plan."""
    _verify_coach_access(db, student_id, coach)

    from backend.database.models_v2 import PrescriptionPlan
    plan = db.query(PrescriptionPlan).filter(
        PrescriptionPlan.id == plan_id,
        PrescriptionPlan.user_id == student_id,
    ).first()
    if not plan:
        raise HTTPException(status_code=404, detail='Plan not found')

    return {
        'id': plan.id,
        'user_id': plan.user_id,
        'plan_name': plan.plan_name,
        'overall_strategy': plan.overall_strategy,
        'status': plan.status,
        'generation_method': plan.generation_method,
        'template_version': plan.template_version,
        'plan_meta': plan.plan_meta,
        'created_at': str(plan.created_at),
        'items': [
            {
                'id': item.id,
                'action_id': item.action_id,
                'action_name': item.action_name,
                'family_name': item.family_name,
                'category': item.category,
                'phase': item.phase,
                'sets': item.sets,
                'reps': item.reps,
                'duration_seconds': item.duration_seconds,
                'order_index': item.order_index,
                'difficulty': item.difficulty,
                'intensity': item.intensity,
                'notes': item.notes,
                'is_substitution': item.is_substitution,
            }
            for item in (plan.items or [])
        ],
    }


def delete_student_prescription_plan(db: Session, student_id: int, plan_id: int, coach: User) -> dict:
    """Delete a v2 prescription plan, including bridge prescription if activated."""
    _verify_coach_access(db, student_id, coach)

    from backend.database.models_v2 import PrescriptionPlan, PrescriptionPlanItem
    plan = db.query(PrescriptionPlan).filter(
        PrescriptionPlan.id == plan_id,
        PrescriptionPlan.user_id == student_id,
    ).first()
    if not plan:
        raise HTTPException(status_code=404, detail='Plan not found')

    plan_name = plan.plan_name

    # 1. Delete training completion records (FK → plan_item)
    from backend.database.models_v2 import TrainingCompletion
    db.query(TrainingCompletion).filter(
        TrainingCompletion.plan_id == plan_id
    ).delete()

    # 2. Delete plan items
    db.query(PrescriptionPlanItem).filter(
        PrescriptionPlanItem.plan_id == plan_id
    ).delete()

    # 3. If activated, clean up the bridge Prescription record
    if plan.status == "active":
        bridge = db.query(Prescription).filter(
            Prescription.user_id == student_id,
            Prescription.fms_record_id == (plan.fms_record_id or 0),
            Prescription.assessment_record_id == plan.assessment_record_id,
            Prescription.phase == 1,
            Prescription.status == PrescriptionStatus.ACTIVE,
        ).order_by(Prescription.created_at.desc()).first()
        if bridge:
            db.query(PrescriptionItem).filter(
                PrescriptionItem.prescription_id == bridge.id
            ).delete()
            db.delete(bridge)

    db.delete(plan)
    db.commit()
    return {'message': f'Plan "{plan_name}" deleted'}


def _verify_coach_access(db: Session, student_id: int, coach: User) -> User:
    """Verify coach has access to a student. Returns the student."""
    student = db.query(User).filter(
        User.id == student_id,
        User.role == UserRole.TRAINEE,
        User.is_active == True,
    ).first()
    if not student:
        raise HTTPException(status_code=404, detail='学员未找到')

    if coach.role != UserRole.ADMIN:
        membership = db.query(class_group_student).join(
            ClassGroup, class_group_student.c.class_group_id == ClassGroup.id,
        ).filter(
            class_group_student.c.user_id == student_id,
            ClassGroup.coach_id == coach.id,
        ).first()
        if not membership:
            raise HTTPException(status_code=403, detail='无权操作该学员')

    return student

def _count_recent_sessions(db: Session, student_ids: List[int], days: int) -> int:
    """Count how many training completion records student_ids made in recent N days."""
    if not student_ids:
        return 0
    from backend.database.models_v2 import TrainingCompletion
    since = datetime.utcnow() - timedelta(days=days)
    return db.query(TrainingCompletion).filter(
        TrainingCompletion.user_id.in_(student_ids),
        TrainingCompletion.created_at >= since,
    ).count()


def _count_active_students(db: Session, student_ids: List[int], days: int) -> int:
    """Count how many distinct students had any training record in recent N days."""
    if not student_ids:
        return 0
    from backend.database.models_v2 import TrainingCompletion
    since = datetime.utcnow() - timedelta(days=days)
    users = set(
        r[0] for r in db.query(TrainingCompletion.user_id).filter(
            TrainingCompletion.user_id.in_(student_ids),
            TrainingCompletion.created_at >= since,
        ).distinct().all()
    )
    return len(users)


def get_class_stats(db: Session, coach: User, class_id: int) -> dict:
    """Detailed statistics for a single class."""
    group = db.query(ClassGroup).filter(
        ClassGroup.id == class_id,
        ClassGroup.coach_id == coach.id,
    ).first()
    if not group:
        raise HTTPException(status_code=404, detail='Class not found')

    students = group.students
    total = len(students)
    student_ids = [s.id for s in students]

    # Compute real activity counts from FMS + Assessment records
    total_sessions_7d = _count_recent_sessions(db, student_ids, 7)
    total_sessions_30d = _count_recent_sessions(db, student_ids, 30)
    active_7d_count = _count_active_students(db, student_ids, 7)

    student_stats = []
    overall_fms_scores = []

    for s in students:
        # Get the BEST (highest overall_score) FMS record for this student
        best_fms = db.query(FMSRecord).filter(
            FMSRecord.user_id == s.id,
        ).order_by(FMSRecord.overall_score.desc()).first()

        # Get the BEST (highest overall_score) Assessment record
        best_assessment = db.query(AssessmentRecord).filter(
            AssessmentRecord.user_id == s.id,
            AssessmentRecord.assessment_type != 'learning',
        ).order_by(AssessmentRecord.overall_score.desc()).first()

        # Get latest FMS for risk_level reference
        latest_fms = db.query(FMSRecord).filter(
            FMSRecord.user_id == s.id,
        ).order_by(FMSRecord.test_date.desc()).first()

        # For the "latest" card, still query by date
        latest_card = db.query(CheckInCard).filter(
            CheckInCard.user_id == s.id,
        ).order_by(CheckInCard.date.desc()).first()

        # Count this student's training completions in last 7/30 days
        from backend.database.models_v2 import TrainingCompletion
        since_7d = datetime.utcnow() - timedelta(days=7)
        since_30d = datetime.utcnow() - timedelta(days=30)
        sessions_7d = db.query(TrainingCompletion).filter(
            TrainingCompletion.user_id == s.id,
            TrainingCompletion.created_at >= since_7d,
        ).count()
        sessions_30d = db.query(TrainingCompletion).filter(
            TrainingCompletion.user_id == s.id,
            TrainingCompletion.created_at >= since_30d,
        ).count()

        # Pick the best record for display:
        #   - Prefer records with real dimension data (>=2 non-zero dimension scores)
        #   - Among those, pick highest overall_score
        #   - Fall back to whichever record exists
        def _dim_count(r):
            if not r: return 0
            dims = [r.balance_score, r.flexibility_score, r.upper_limb_score, r.core_score, r.symmetry_score]
            return sum(1 for v in dims if v and v > 0)

        fms_ok = _dim_count(best_fms) >= 2
        assessment_ok = _dim_count(best_assessment) >= 2
        fms_score = best_fms.overall_score if best_fms and best_fms.overall_score else 0
        assessment_score = best_assessment.overall_score if best_assessment and best_assessment.overall_score else 0

        if fms_ok and not assessment_ok:
            best_record = best_fms
        elif assessment_ok and not fms_ok:
            best_record = best_assessment
        elif fms_ok and assessment_ok:
            best_record = best_fms if fms_score >= assessment_score else best_assessment
        else:
            # Neither has dimension data — pick whichever has a score
            best_record = best_fms if fms_score >= assessment_score else best_assessment
            if not best_record:
                best_record = best_fms or best_assessment

        fms_scores = _serialize_fms(best_record)
        if best_record and best_record.overall_score:
            overall_fms_scores.append(best_record.overall_score)

        student_stats.append({
            'id': s.id,
            'username': s.username,
            'phone': s.phone or '-',
            'fms_scores': fms_scores,
            'sessions_7d': sessions_7d,
            'sessions_30d': sessions_30d,
            'streak_days': latest_card.streak_days if latest_card else 0,
            'risk_level': getattr(latest_fms or best_record, 'risk_level', None),
        })

    avg_overall = sum(overall_fms_scores) / len(overall_fms_scores) if overall_fms_scores else 0
    completion_rate = round(active_7d_count / total * 100, 1) if total > 0 else 0

    return {
        'class_id': class_id,
        'class_name': group.name,
        'student_count': total,
        'summary': {
            'avg_overall_score': round(avg_overall, 1),
            'active_7d_count': active_7d_count,
            'active_7d_rate': completion_rate,
            'total_sessions_7d': total_sessions_7d,
            'total_sessions_30d': total_sessions_30d,
            'sessions_per_student_7d': round(total_sessions_7d / total, 1) if total > 0 else 0.0,
        },
        'students': student_stats,
    }


def get_class_trend(db: Session, coach: User, class_id: int, days: int = 30) -> dict:
    """Training trend data — daily training completion counts + avg best_score."""
    group = db.query(ClassGroup).filter(
        ClassGroup.id == class_id,
        ClassGroup.coach_id == coach.id,
    ).first()
    if not group:
        raise HTTPException(status_code=404, detail='Class not found')

    student_ids = [s.id for s in group.students]
    if not student_ids:
        from datetime import date, timedelta as td
        trend = []
        for i in range(days):
            d = (datetime.utcnow() - td(days=days - 1 - i)).date()
            trend.append({'date': d.strftime('%Y-%m-%d'), 'session_count': 0, 'avg_score': 0})
        return {'class_id': class_id, 'days': days, 'trend': trend}

    since = datetime.utcnow() - timedelta(days=days)
    from datetime import date, timedelta as td
    from sqlalchemy import func
    from backend.database.models_v2 import TrainingCompletion

    daily_rows = db.query(
        func.date(TrainingCompletion.created_at).label('d'),
        func.count(TrainingCompletion.id).label('cnt'),
        func.avg(TrainingCompletion.best_score).label('avg_s'),
    ).filter(
        TrainingCompletion.user_id.in_(student_ids),
        TrainingCompletion.created_at >= since,
    ).group_by(func.date(TrainingCompletion.created_at)).all()

    daily = {}
    for row in daily_rows:
        d_str = str(row.d)
        daily[d_str] = {
            'session_count': row.cnt,
            'avg_score': round(row.avg_s, 1) if row.avg_s else 0,
        }

    trend = []
    for i in range(days):
        d = (datetime.utcnow() - td(days=days - 1 - i)).date()
        d_str = d.strftime('%Y-%m-%d')
        entry = daily.get(d_str, {'session_count': 0, 'avg_score': 0})
        trend.append({
            'date': d_str,
            'session_count': entry['session_count'],
            'avg_score': entry['avg_score'],
        })

    return {'class_id': class_id, 'days': days, 'trend': trend}


# ── Coach summary ──────────────────────────────────────────────────────

def get_coach_summary(db: Session, coach: User) -> dict:
    """Overall coach dashboard summary across all classes."""
    groups = db.query(ClassGroup).filter(ClassGroup.coach_id == coach.id).all()
    total_students = sum(len(g.students) for g in groups)
    all_student_ids = [s.id for g in groups for s in g.students]

    return {
        'class_count': len(groups),
        'total_students': total_students,
        'sessions_7d': _count_recent_sessions(db, all_student_ids, 7),
        'sessions_30d': _count_recent_sessions(db, all_student_ids, 30),
    }


# ── Available trainees search ──────────────────────────────────────────

def search_available_trainees(db: Session, keyword: str = '') -> List[dict]:
    """Search trainee users by username (for coach to add students)."""
    query = db.query(User).filter(
        User.role == UserRole.TRAINEE,
        User.is_active == True,
    )
    if keyword:
        query = query.filter(User.username.contains(keyword))
    trainees = query.limit(20).all()
    return [
        {'id': t.id, 'username': t.username, 'phone': t.phone or '-'}
        for t in trainees
    ]


# ── Student profile ────────────────────────────────────────────────────

def get_student_profile(db: Session, student_id: int, coach: User) -> dict:
    """Get full student profile (FMS, assessment, prescriptions, badges, etc.).

    Coaches can only view students in their own classes; admins can view anyone.
    """
    student = db.query(User).filter(
        User.id == student_id,
        User.role == UserRole.TRAINEE,
        User.is_active == True,
    ).first()
    if not student:
        raise HTTPException(status_code=404, detail='学员未找到')

    # Permission check: must be in coach's class (admin exempt)
    if coach.role != UserRole.ADMIN:
        membership = db.query(class_group_student).join(
            ClassGroup, class_group_student.c.class_group_id == ClassGroup.id,
        ).filter(
            class_group_student.c.user_id == student_id,
            ClassGroup.coach_id == coach.id,
        ).first()
        if not membership:
            raise HTTPException(status_code=403, detail='无权查看该学员，学员不在您的班级中')

    profile = {
        'id': student.id,
        'username': student.username,
        'phone': student.phone or '-',
        'gender': student.gender or '-',
        'created_at': str(student.created_at),
    }

    # Latest FMS record
    latest_fms = db.query(FMSRecord).filter(
        FMSRecord.user_id == student_id,
    ).order_by(FMSRecord.test_date.desc()).first()
    profile['fms'] = _serialize_fms_detail(latest_fms)

    # All FMS history
    all_fms = db.query(FMSRecord).filter(
        FMSRecord.user_id == student_id,
    ).order_by(FMSRecord.test_date.desc()).all()
    profile['fms_history'] = [_serialize_fms_detail(r) for r in all_fms]

    # Latest assessment
    latest_assessment = db.query(AssessmentRecord).filter(
        AssessmentRecord.user_id == student_id,
        AssessmentRecord.assessment_type != 'learning',
    ).order_by(AssessmentRecord.test_date.desc()).first()
    profile['assessment'] = _serialize_assessment_detail(latest_assessment)

    # All assessment history
    all_assessments = db.query(AssessmentRecord).filter(
        AssessmentRecord.user_id == student_id,
        AssessmentRecord.assessment_type != 'learning',
    ).order_by(AssessmentRecord.test_date.desc()).all()
    profile['assessment_history'] = [_serialize_assessment_detail(r) for r in all_assessments]

    # Note: V1 Prescriptions have been deprecated — use V2 PrescriptionPlan via /students/{id}/plans

    # Training records (module removed)
    profile['recent_trainings'] = []

    # Check-in stats
    latest_card = db.query(CheckInCard).filter(
        CheckInCard.user_id == student_id,
    ).order_by(CheckInCard.date.desc()).first()
    total_checkins = db.query(CheckInCard).filter(
        CheckInCard.user_id == student_id,
    ).count()
    profile['checkin'] = {
        'streak_days': latest_card.streak_days if latest_card else 0,
        'total_checkins': total_checkins,
    }

    # Badges
    badges = db.query(models.Badge).filter(
        models.Badge.user_id == student_id,
    ).all()
    profile['badges'] = [
        {
            'id': b.id,
            'badge_type': b.badge_type,
            'name': b.name,
            'description': b.description,
            'earned_at': str(b.earned_at),
        }
        for b in badges
    ]

    return profile


# ── Private serialization helpers ──────────────────────────────────────

def _serialize_fms_detail(record) -> Optional[dict]:
    """Serialize an FMS record with full detail."""
    if not record:
        return None
    return {
        'id': record.id,
        'test_date': str(record.test_date),
        'balance_score': record.balance_score,
        'flexibility_score': record.flexibility_score,
        'upper_limb_score': record.upper_limb_score,
        'core_score': record.core_score,
        'symmetry_score': record.symmetry_score,
        'overall_score': record.overall_score,
        'risk_level': record.risk_level.value if record.risk_level else None,
    }


def _serialize_assessment_detail(record) -> Optional[dict]:
    """Serialize an assessment record with full detail."""
    if not record:
        return None
    return {
        'id': record.id,
        'test_date': str(record.test_date),
        'assessment_type': record.assessment_type or 'standard',
        'balance_score': record.balance_score,
        'flexibility_score': record.flexibility_score,
        'upper_limb_score': record.upper_limb_score,
        'core_score': record.core_score,
        'symmetry_score': record.symmetry_score,
        'overall_score': record.overall_score,
        'risk_level': record.risk_level.value if record.risk_level else None,
        'report_data': record.report_data,
        'muscle_findings': _parse_json(record.muscle_findings),
    }


def _serialize_prescription(rx) -> dict:
    """Serialize a prescription with its items."""
    items = []
    for item in rx.items:
        items.append({
            'id': item.id,
            'action_name': item.action.name if item.action else '未知动作',
            'phase': item.phase.value if item.phase else None,
            'sets': item.sets,
            'reps': item.reps,
            'duration': item.duration,
            'order_index': item.order_index,
            'difficulty': item.action.difficulty if item.action else 0,
        })
    return {
        'id': rx.id,
        'phase': rx.phase,
        'status': rx.status.value if rx.status else None,
        'difficulty': rx.difficulty,
        'created_at': str(rx.created_at),
        'items': items,
    }


# ── Training records ─────────────────────────────────────────────────────

def get_student_training_records(db: Session, student_id: int, coach: User, days: int = 30) -> dict:
    """Get a student's training completion records with plan context."""
    _verify_coach_access(db, student_id, coach)

    from backend.database.models_v2 import TrainingCompletion, PrescriptionPlan
    since = datetime.utcnow() - timedelta(days=days)

    records = db.query(TrainingCompletion).filter(
        TrainingCompletion.user_id == student_id,
        TrainingCompletion.created_at >= since,
    ).order_by(TrainingCompletion.created_at.desc()).limit(200).all()

    # Collect plan names
    plan_ids = list(set(r.plan_id for r in records))
    plans = {}
    if plan_ids:
        plan_rows = db.query(PrescriptionPlan).filter(
            PrescriptionPlan.id.in_(plan_ids)
        ).all()
        plans = {p.id: p.plan_name for p in plan_rows}

    return {
        'student_id': student_id,
        'days': days,
        'records': [
            {
                'id': r.id,
                'plan_id': r.plan_id,
                'plan_name': plans.get(r.plan_id, '标准学习'),
                'action_name': r.action_name,
                'best_score': r.best_score,
                'rep_count': r.rep_count,
                'hold_time_seconds': r.hold_time_seconds,
                'duration_seconds': r.duration_seconds,
                'created_at': str(r.created_at),
            }
            for r in records
        ],
    }


# ── Invite Code Management ──────────────────────────────────────────────

def regenerate_invite_code(db: Session, coach: User, class_id: int) -> dict:
    """重新生成班级邀请码（教练操作）"""
    group = db.query(ClassGroup).filter(
        ClassGroup.id == class_id,
        ClassGroup.coach_id == coach.id,
    ).first()
    if not group:
        raise HTTPException(status_code=404, detail='Class not found')

    new_code = _generate_unique_invite_code(db)
    group.invite_code = new_code
    db.commit()
    return {'invite_code': new_code, 'message': '邀请码已更新'}


def get_student_training_stats(db: Session, student_id: int, coach: User) -> dict:
    """Get aggregate training stats for a student."""
    _verify_coach_access(db, student_id, coach)

    from backend.database.models_v2 import TrainingCompletion, PrescriptionPlan
    from sqlalchemy import func

    # All-time stats
    all_time = db.query(
        func.count(TrainingCompletion.id).label('total'),
        func.avg(TrainingCompletion.best_score).label('avg_score'),
        func.sum(TrainingCompletion.duration_seconds).label('total_duration'),
    ).filter(
        TrainingCompletion.user_id == student_id,
    ).first()

    # 7-day stats
    since_7d = datetime.utcnow() - timedelta(days=7)
    week_stats = db.query(
        func.count(TrainingCompletion.id).label('total'),
        func.avg(TrainingCompletion.best_score).label('avg_score'),
        func.sum(TrainingCompletion.duration_seconds).label('total_duration'),
    ).filter(
        TrainingCompletion.user_id == student_id,
        TrainingCompletion.created_at >= since_7d,
    ).first()

    # Active plans with progress
    active_plans = db.query(PrescriptionPlan).filter(
        PrescriptionPlan.user_id == student_id,
        PrescriptionPlan.status == 'active',
    ).all()

    plans_progress = []
    for plan in active_plans:
        total_items = len(plan.items) if plan.items else 0
        completed = db.query(TrainingCompletion).filter(
            TrainingCompletion.plan_id == plan.id,
        ).count()
        # Get latest score for this plan
        latest = db.query(TrainingCompletion).filter(
            TrainingCompletion.plan_id == plan.id,
        ).order_by(TrainingCompletion.created_at.desc()).first()
        plans_progress.append({
            'plan_id': plan.id,
            'plan_name': plan.plan_name,
            'total_items': total_items,
            'completed_sessions': completed,
            'latest_score': latest.best_score if latest else None,
            'created_at': str(plan.created_at),
        })

    return {
        'student_id': student_id,
        'all_time': {
            'total': all_time.total or 0,
            'avg_score': round(all_time.avg_score, 1) if all_time and all_time.avg_score else 0,
            'total_duration_minutes': round((all_time.total_duration or 0) / 60, 1),
        },
        'week': {
            'total': week_stats.total or 0,
            'avg_score': round(week_stats.avg_score, 1) if week_stats and week_stats.avg_score else 0,
            'total_duration_minutes': round((week_stats.total_duration or 0) / 60, 1),
        },
        'active_plans': plans_progress,
    }


