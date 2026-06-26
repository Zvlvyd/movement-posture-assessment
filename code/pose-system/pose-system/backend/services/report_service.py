from sqlalchemy.orm import Session
from sqlalchemy import func
from backend.database import models
from datetime import datetime, timedelta
from typing import List, Dict

class ReportService:
    def __init__(self, db: Session):
        self.db = db

    def get_training_history(self, user_id: int, days: int = 30):
        start_date = datetime.utcnow() - timedelta(days=days)
        return self.db.query(models.TrainingRecord).filter(
            models.TrainingRecord.user_id == user_id,
            models.TrainingRecord.start_time >= start_date
        ).order_by(models.TrainingRecord.start_time.desc()).all()

    def get_training_stats(self, user_id: int) -> Dict:
        now = datetime.utcnow()
        last_7 = now - timedelta(days=7)
        last_30 = now - timedelta(days=30)
        total_count_7 = self.db.query(func.count(models.TrainingRecord.id)).filter(
            models.TrainingRecord.user_id == user_id,
            models.TrainingRecord.start_time >= last_7
        ).scalar() or 0
        total_count_30 = self.db.query(func.count(models.TrainingRecord.id)).filter(
            models.TrainingRecord.user_id == user_id,
            models.TrainingRecord.start_time >= last_30
        ).scalar() or 0
        avg_score = self.db.query(func.avg(models.TrainingRecord.total_score)).filter(
            models.TrainingRecord.user_id == user_id,
            models.TrainingRecord.total_score.isnot(None)
        ).scalar() or 0
        streak = self._compute_streak(user_id)
        return {
            'total_sessions_7d': total_count_7,
            'total_sessions_30d': total_count_30,
            'average_score': round(float(avg_score), 1),
            'current_streak': streak,
        }

    def _compute_streak(self, user_id: int) -> int:
        today = datetime.utcnow().date()
        streak = 0
        for i in range(365):
            check_date = today - timedelta(days=i)
            card = self.db.query(models.CheckInCard).filter(
                models.CheckInCard.user_id == user_id,
                func.date(models.CheckInCard.date) == check_date
            ).first()
            if card:
                streak += 1
            else:
                break
        return streak

class RetestService:
    def __init__(self, db: Session):
        self.db = db

    def check_retest_needed(self, user_id: int) -> dict:
        last_fms = self.db.query(models.FMSRecord).filter(
            models.FMSRecord.user_id == user_id
        ).order_by(models.FMSRecord.test_date.desc()).first()
        if not last_fms:
            return {'needed': True, 'reason': 'no_previous_test'}
        days_since = (datetime.utcnow() - last_fms.test_date).days
        if days_since >= 30:
            return {'needed': True, 'reason': 'monthly_retest', 'days_since_last': days_since}
        if last_fms.overall_score < 40:
            return {'needed': True, 'reason': 'high_risk', 'days_since_last': days_since}
        return {'needed': False, 'days_since_last': days_since}

class CycleService:
    def __init__(self, db: Session):
        self.db = db

    def get_or_create_config(self, user_id: int):
        config = self.db.query(models.UserCycleConfig).filter(
            models.UserCycleConfig.user_id == user_id
        ).first()
        if not config:
            config = models.UserCycleConfig(user_id=user_id)
            self.db.add(config)
            self.db.commit()
            self.db.refresh(config)
        return config

    def update_config(self, user_id: int, cycle_length: int, last_period_date: datetime):
        config = self.get_or_create_config(user_id)
        config.cycle_length = cycle_length
        config.last_period_date = last_period_date
        self.db.commit()
        return config

    def get_current_phase(self, user_id: int) -> str:
        config = self.db.query(models.UserCycleConfig).filter(
            models.UserCycleConfig.user_id == user_id
        ).first()
        if not config or not config.last_period_date:
            return 'unknown'
        days_since = (datetime.utcnow().date() - config.last_period_date.date()).days % config.cycle_length
        if days_since <= 5:
            return 'menstrual'
        elif days_since <= 13:
            return 'follicular'
        elif days_since <= 15:
            return 'ovulation'
        else:
            return 'luteal'

class BadgeService:
    BADGES = [
        {'type': 'streak_7', 'name': '坚持一周', 'description': '连续打卡7天', 'condition': lambda s: s.get('streak', 0) >= 7},
        {'type': 'streak_30', 'name': '月度达人', 'description': '连续打卡30天', 'condition': lambda s: s.get('streak', 0) >= 30},
        {'type': 'sessions_100', 'name': '百练成钢', 'description': '完成100次训练', 'condition': lambda s: s.get('total_sessions', 0) >= 100},
        {'type': 'score_90', 'name': '动作大师', 'description': '平均评分达到90分', 'condition': lambda s: s.get('avg_score', 0) >= 90},
        {'type': 'fms_first', 'name': '初次筛查', 'description': '完成首次FMS筛查', 'condition': lambda s: s.get('fms_completed', False)},
    ]

    def __init__(self, db: Session):
        self.db = db

    def check_and_award(self, user_id: int, stats: Dict):
        existing = {b.badge_type for b in self.db.query(models.Badge).filter(models.Badge.user_id == user_id).all()}
        awarded = []
        for badge in self.BADGES:
            if badge['type'] not in existing and badge['condition'](stats):
                b = models.Badge(user_id=user_id, badge_type=badge['type'], name=badge['name'], description=badge['description'])
                self.db.add(b)
                awarded.append(badge)
        if awarded:
            self.db.commit()
        return awarded
