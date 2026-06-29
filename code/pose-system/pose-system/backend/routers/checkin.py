from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session
from datetime import datetime, date
from backend.database.connection import get_db
from backend.database import models
from backend.services.report_service import ReportService, BadgeService
from backend.services.auth_service import get_current_user
from backend.database.models import User

router = APIRouter(prefix='/api/checkin', tags=['Check-in & Badges'])

@router.post('')
def check_in(db: Session = Depends(get_db), user: User = Depends(get_current_user)):
    today = datetime.utcnow()
    today_date = today.date()

    # 检查今天是否已签到
    existing_today = db.query(models.CheckInCard).filter(
        models.CheckInCard.user_id == user.id,
        models.CheckInCard.date >= today_date
    ).first()
    if existing_today:
        return {
            'message': 'already checked in today',
            'streak_days': existing_today.streak_days,
            'new_badges': [],
        }

    yesterday_card = db.query(models.CheckInCard).filter(
        models.CheckInCard.user_id == user.id
    ).order_by(models.CheckInCard.date.desc()).first()
    diff_days = (today - yesterday_card.date).days if yesterday_card else None
    streak = (yesterday_card.streak_days + 1) if yesterday_card and diff_days == 1 else 1
    card = models.CheckInCard(user_id=user.id, date=today, streak_days=streak)
    db.add(card)
    db.commit()
    db.refresh(card)
    report_svc = ReportService(db)
    stats = report_svc.get_training_stats(user.id)
    badge_svc = BadgeService(db)
    new_badges = badge_svc.check_and_award(user.id, {'streak': streak, 'total_sessions': stats['total_sessions_30d'], 'avg_score': stats['average_score']})
    return {'message': 'check-in successful', 'streak_days': streak, 'new_badges': new_badges}

@router.get('/status')
def get_checkin_status(db: Session = Depends(get_db), user: User = Depends(get_current_user)):
    report_svc = ReportService(db)
    stats = report_svc.get_training_stats(user.id)
    cards = db.query(models.CheckInCard).filter(
        models.CheckInCard.user_id == user.id
    ).order_by(models.CheckInCard.date.desc()).limit(30).all()
    return {
        'streak_days': stats['current_streak'],
        'recent_cards': [{'date': str(c.date), 'streak': c.streak_days} for c in cards],
    }

@router.get('/badges')
def get_badges(db: Session = Depends(get_db), user: User = Depends(get_current_user)):
    badges = db.query(models.Badge).filter(models.Badge.user_id == user.id).all()
    return [{'type': b.badge_type, 'name': b.name, 'description': b.description, 'earned_at': str(b.earned_at)} for b in badges]
