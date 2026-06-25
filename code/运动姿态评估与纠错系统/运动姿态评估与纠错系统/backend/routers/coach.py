from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from typing import List
from backend.database.connection import get_db
from backend.database import models
from backend.database.models import User, UserRole, ClassGroup
from backend.services.auth_service import get_current_user, require_role

router = APIRouter(prefix='/api/coach', tags=['Coach Management'])

@router.get('/students')
def list_students(class_id: int = None, db: Session = Depends(get_db), coach: User = Depends(require_role(UserRole.COACH))):
    if class_id:
        group = db.query(ClassGroup).filter(ClassGroup.id == class_id, ClassGroup.coach_id == coach.id).first()
        if not group:
            raise HTTPException(status_code=404, detail='Class not found')
        return [{'id': s.id, 'username': s.username, 'phone': s.phone} for s in group.students]
    groups = db.query(ClassGroup).filter(ClassGroup.coach_id == coach.id).all()
    students = []
    for g in groups:
        for s in g.students:
            students.append({'id': s.id, 'username': s.username, 'phone': s.phone, 'class': g.name})
    return students

@router.post('/classes')
def create_class(name: str, description: str = '', db: Session = Depends(get_db), coach: User = Depends(require_role(UserRole.COACH))):
    group = ClassGroup(coach_id=coach.id, name=name, description=description)
    db.add(group)
    db.commit()
    db.refresh(group)
    return {'id': group.id, 'name': group.name}

@router.post('/classes/{class_id}/students')
def add_student(class_id: int, student_id: int, db: Session = Depends(get_db), coach: User = Depends(require_role(UserRole.COACH))):
    group = db.query(ClassGroup).filter(ClassGroup.id == class_id, ClassGroup.coach_id == coach.id).first()
    if not group:
        raise HTTPException(status_code=404, detail='Class not found')
    student = db.query(User).filter(User.id == student_id, User.role == UserRole.TRAINEE).first()
    if not student:
        raise HTTPException(status_code=404, detail='Student not found')
    if student not in group.students:
        group.students.append(student)
        db.commit()
    return {'message': 'student added'}

from datetime import datetime, timedelta

@router.get('/classes')
def list_classes(db: Session = Depends(get_db), coach: User = Depends(require_role(UserRole.COACH))):
    """List all classes with overview statistics."""
    groups = db.query(ClassGroup).filter(ClassGroup.coach_id == coach.id).all()
    result = []
    for g in groups:
        student_count = len(g.students)
        result.append({
            'id': g.id, 'name': g.name, 'description': g.description,
            'student_count': student_count,
            'created_at': str(g.created_at),
        })
    return result

@router.get('/classes/{class_id}/stats')
def class_stats(class_id: int, db: Session = Depends(get_db), coach: User = Depends(require_role(UserRole.COACH))):
    """Detailed statistics for a single class."""
    group = db.query(ClassGroup).filter(
        ClassGroup.id == class_id, ClassGroup.coach_id == coach.id
    ).first()
    if not group:
        raise HTTPException(status_code=404, detail='Class not found')

    students = group.students
    total = len(students)
    now = datetime.utcnow()
    week_ago = now - timedelta(days=7)
    month_ago = now - timedelta(days=30)

    student_stats = []
    overall_fms_scores = []
    total_sessions_7d = 0
    total_sessions_30d = 0
    active_7d_count = 0

    for s in students:
        # Latest FMS record
        latest_fms = db.query(models.FMSRecord).filter(
            models.FMSRecord.user_id == s.id
        ).order_by(models.FMSRecord.test_date.desc()).first()

        # Latest assessment record
        latest_assessment = db.query(models.AssessmentRecord).filter(
            models.AssessmentRecord.user_id == s.id
        ).order_by(models.AssessmentRecord.test_date.desc()).first()

        # Training records
        sessions_7d = db.query(models.TrainingRecord).filter(
            models.TrainingRecord.user_id == s.id,
            models.TrainingRecord.start_time >= week_ago
        ).count()
        sessions_30d = db.query(models.TrainingRecord).filter(
            models.TrainingRecord.user_id == s.id,
            models.TrainingRecord.start_time >= month_ago
        ).count()

        if sessions_7d > 0:
            active_7d_count += 1
        total_sessions_7d += sessions_7d
        total_sessions_30d += sessions_30d

        # Check-in streak
        latest_card = db.query(models.CheckInCard).filter(
            models.CheckInCard.user_id == s.id
        ).order_by(models.CheckInCard.date.desc()).first()

        # Use assessment record if available, else FMS record
        best_record = latest_assessment if latest_assessment else latest_fms
        fms_scores = None
        if best_record:
            fms_scores = {
                'balance': best_record.balance_score,
                'flexibility': best_record.flexibility_score,
                'upper_limb': best_record.upper_limb_score,
                'core': best_record.core_score,
                'symmetry': best_record.symmetry_score,
                'overall': best_record.overall_score,
            }
            if best_record.overall_score:
                overall_fms_scores.append(best_record.overall_score)

        student_stats.append({
            'id': s.id,
            'username': s.username,
            'phone': s.phone or '-',
            'fms_scores': fms_scores,
            'sessions_7d': sessions_7d,
            'sessions_30d': sessions_30d,
            'streak_days': latest_card.streak_days if latest_card else 0,
            'risk_level': best_record.risk_level if best_record and hasattr(best_record, 'risk_level') else None,
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
            'sessions_per_student_7d': round(total_sessions_7d / max(total, 1), 1),
        },
        'students': student_stats,
    }

@router.get('/classes/{class_id}/trend')
def class_trend(class_id: int, days: int = 30, db: Session = Depends(get_db), coach: User = Depends(require_role(UserRole.COACH))):
    """Training trend data for charts (daily session counts)."""
    group = db.query(ClassGroup).filter(
        ClassGroup.id == class_id, ClassGroup.coach_id == coach.id
    ).first()
    if not group:
        raise HTTPException(status_code=404, detail='Class not found')

    student_ids = [s.id for s in group.students]
    if not student_ids:
        return {'trend': []}

    cutoff = datetime.utcnow() - timedelta(days=days)
    records = db.query(models.TrainingRecord).filter(
        models.TrainingRecord.user_id.in_(student_ids),
        models.TrainingRecord.start_time >= cutoff
    ).order_by(models.TrainingRecord.start_time).all()

    # Group by date
    from collections import defaultdict
    daily_counts = defaultdict(lambda: {'count': 0, 'total_score': 0.0, 'scored_count': 0})
    for r in records:
        day = r.start_time.strftime('%Y-%m-%d') if r.start_time else 'unknown'
        daily_counts[day]['count'] += 1
        if r.total_score:
            daily_counts[day]['total_score'] += r.total_score
            daily_counts[day]['scored_count'] += 1

    trend = []
    from datetime import date, timedelta as td
    for i in range(days):
        d = (datetime.utcnow() - td(days=days-1-i)).date()
        day_str = d.strftime('%Y-%m-%d')
        entry = daily_counts.get(day_str, {'count': 0, 'total_score': 0.0, 'scored_count': 0})
        avg_score = round(entry['total_score'] / entry['scored_count'], 1) if entry['scored_count'] > 0 else 0
        trend.append({
            'date': day_str,
            'session_count': entry['count'],
            'avg_score': avg_score,
        })

    return {'class_id': class_id, 'days': days, 'trend': trend}

@router.get('/summary')
def coach_summary(db: Session = Depends(get_db), coach: User = Depends(require_role(UserRole.COACH))):
    """Overall coach dashboard summary across all classes."""
    groups = db.query(ClassGroup).filter(ClassGroup.coach_id == coach.id).all()
    total_students = sum(len(g.students) for g in groups)

    week_ago = datetime.utcnow() - timedelta(days=7)
    month_ago = datetime.utcnow() - timedelta(days=30)

    all_student_ids = []
    for g in groups:
        all_student_ids.extend(s.id for s in g.students)
    all_student_ids = list(set(all_student_ids))

    if all_student_ids:
        sessions_7d = db.query(models.TrainingRecord).filter(
            models.TrainingRecord.user_id.in_(all_student_ids),
            models.TrainingRecord.start_time >= week_ago
        ).count()
        sessions_30d = db.query(models.TrainingRecord).filter(
            models.TrainingRecord.user_id.in_(all_student_ids),
            models.TrainingRecord.start_time >= month_ago
        ).count()
    else:
        sessions_7d = sessions_30d = 0

    return {
        'class_count': len(groups),
        'total_students': total_students,
        'sessions_7d': sessions_7d,
        'sessions_30d': sessions_30d,
    }

