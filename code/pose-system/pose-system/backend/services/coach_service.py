# -*- coding: utf-8 -*-
"""
Coach management service — class CRUD, student management, statistics.

Extracted from routers/coach.py to maintain clean layered architecture:
  routers (thin) → services (logic) → database/models
"""
from datetime import datetime, timedelta
from collections import defaultdict
from typing import Optional, List

from sqlalchemy.orm import Session
from fastapi import HTTPException

from backend.database import models
from backend.database.models import (
    User, UserRole, ClassGroup, class_group_student,
    FMSRecord, AssessmentRecord, CheckInCard, Prescription,
)


# ── Helpers ─────────────────────────────────────────────────────────────

def _serialize_student_brief(user: User, class_name: str = None) -> dict:
    """Serialize a student into a brief dict for list views."""
    d = {'id': user.id, 'username': user.username, 'phone': user.phone}
    if class_name:
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
        return [_serialize_student_brief(s) for s in group.students]

    groups = db.query(ClassGroup).filter(ClassGroup.coach_id == coach.id).all()
    students = []
    for g in groups:
        for s in g.students:
            students.append(_serialize_student_brief(s, class_name=g.name))
    return students


# ── Class CRUD ─────────────────────────────────────────────────────────

def create_class(db: Session, coach: User, name: str, description: str = '') -> dict:
    """Create a new class group."""
    group = ClassGroup(coach_id=coach.id, name=name, description=description)
    db.add(group)
    db.commit()
    db.refresh(group)
    return {'id': group.id, 'name': group.name}


def list_classes(db: Session, coach: User) -> List[dict]:
    """List all classes with overview statistics."""
    groups = db.query(ClassGroup).filter(ClassGroup.coach_id == coach.id).all()
    return [
        {
            'id': g.id,
            'name': g.name,
            'description': g.description,
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
    """Get all v2 prescription plans for a student (coach must have access)."""
    student = _verify_coach_access(db, student_id, coach)

    from backend.database.models_v2 import PrescriptionPlan
    plans = db.query(PrescriptionPlan).filter(
        PrescriptionPlan.user_id == student_id,
    ).order_by(PrescriptionPlan.created_at.desc()).all()

    return [
        {
            'id': p.id,
            'plan_name': p.plan_name,
            'status': p.status,
            'generation_method': p.generation_method,
            'overall_strategy': p.overall_strategy,
            'created_at': str(p.created_at),
            'item_count': len(p.items) if p.items else 0,
        }
        for p in plans
    ]


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
    """Delete a v2 prescription plan (cascade deletes items)."""
    _verify_coach_access(db, student_id, coach)

    from backend.database.models_v2 import PrescriptionPlan
    plan = db.query(PrescriptionPlan).filter(
        PrescriptionPlan.id == plan_id,
        PrescriptionPlan.user_id == student_id,
    ).first()
    if not plan:
        raise HTTPException(status_code=404, detail='Plan not found')

    plan_name = plan.plan_name
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

    student_stats = []
    overall_fms_scores = []
    active_7d_count = 0

    for s in students:
        latest_fms = db.query(FMSRecord).filter(
            FMSRecord.user_id == s.id,
        ).order_by(FMSRecord.test_date.desc()).first()

        latest_assessment = db.query(AssessmentRecord).filter(
            AssessmentRecord.user_id == s.id,
        ).order_by(AssessmentRecord.test_date.desc()).first()

        # Training module removed — stub zero counts
        sessions_7d = 0
        if sessions_7d > 0:
            active_7d_count += 1

        latest_card = db.query(CheckInCard).filter(
            CheckInCard.user_id == s.id,
        ).order_by(CheckInCard.date.desc()).first()

        best_record = latest_assessment if latest_assessment else latest_fms
        fms_scores = _serialize_fms(best_record)
        if best_record and best_record.overall_score:
            overall_fms_scores.append(best_record.overall_score)

        student_stats.append({
            'id': s.id,
            'username': s.username,
            'phone': s.phone or '-',
            'fms_scores': fms_scores,
            'sessions_7d': sessions_7d,
            'sessions_30d': 0,
            'streak_days': latest_card.streak_days if latest_card else 0,
            'risk_level': getattr(best_record, 'risk_level', None),
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
            'total_sessions_7d': 0,
            'total_sessions_30d': 0,
            'sessions_per_student_7d': 0.0,
        },
        'students': student_stats,
    }


def get_class_trend(db: Session, coach: User, class_id: int, days: int = 30) -> dict:
    """Training trend data for charts (daily session counts)."""
    group = db.query(ClassGroup).filter(
        ClassGroup.id == class_id,
        ClassGroup.coach_id == coach.id,
    ).first()
    if not group:
        raise HTTPException(status_code=404, detail='Class not found')

    # Training module removed — return empty trend
    trend = []
    from datetime import date, timedelta as td
    for i in range(days):
        d = (datetime.utcnow() - td(days=days - 1 - i)).date()
        trend.append({
            'date': d.strftime('%Y-%m-%d'),
            'session_count': 0,
            'avg_score': 0,
        })

    return {'class_id': class_id, 'days': days, 'trend': trend}


# ── Coach summary ──────────────────────────────────────────────────────

def get_coach_summary(db: Session, coach: User) -> dict:
    """Overall coach dashboard summary across all classes."""
    groups = db.query(ClassGroup).filter(ClassGroup.coach_id == coach.id).all()
    total_students = sum(len(g.students) for g in groups)

    return {
        'class_count': len(groups),
        'total_students': total_students,
        'sessions_7d': 0,
        'sessions_30d': 0,
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
    ).order_by(AssessmentRecord.test_date.desc()).first()
    profile['assessment'] = _serialize_assessment_detail(latest_assessment)

    # All assessment history
    all_assessments = db.query(AssessmentRecord).filter(
        AssessmentRecord.user_id == student_id,
    ).order_by(AssessmentRecord.test_date.desc()).all()
    profile['assessment_history'] = [_serialize_assessment_detail(r) for r in all_assessments]

    # Prescriptions
    prescriptions = db.query(Prescription).filter(
        Prescription.user_id == student_id,
    ).order_by(Prescription.created_at.desc()).all()
    profile['prescriptions'] = [_serialize_prescription(rx) for rx in prescriptions]

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
        'muscle_findings': record.muscle_findings,
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


