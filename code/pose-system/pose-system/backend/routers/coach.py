from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session
from backend.database.connection import get_db
from backend.database.models import User, UserRole
from backend.services.auth_service import require_role
from backend.services import coach_service

router = APIRouter(prefix='/api/coach', tags=['Coach Management'])

COACH_OR_ADMIN = (UserRole.COACH, UserRole.ADMIN)


@router.get('/students')
def list_students(
    class_id: int = None,
    db: Session = Depends(get_db),
    coach: User = Depends(require_role(*COACH_OR_ADMIN)),
):
    return coach_service.list_students(db, coach, class_id)


@router.post('/classes')
def create_class(
    name: str,
    description: str = '',
    db: Session = Depends(get_db),
    coach: User = Depends(require_role(*COACH_OR_ADMIN)),
):
    return coach_service.create_class(db, coach, name, description)


@router.post('/classes/{class_id}/students')
def add_student(
    class_id: int,
    student_id: int,
    db: Session = Depends(get_db),
    coach: User = Depends(require_role(*COACH_OR_ADMIN)),
):
    return coach_service.add_student_to_class(db, coach, class_id, student_id)


@router.get('/classes')
def list_classes(
    db: Session = Depends(get_db),
    coach: User = Depends(require_role(*COACH_OR_ADMIN)),
):
    return coach_service.list_classes(db, coach)


@router.get('/classes/{class_id}/stats')
def class_stats(
    class_id: int,
    db: Session = Depends(get_db),
    coach: User = Depends(require_role(*COACH_OR_ADMIN)),
):
    return coach_service.get_class_stats(db, coach, class_id)


@router.get('/classes/{class_id}/trend')
def class_trend(
    class_id: int,
    days: int = 30,
    db: Session = Depends(get_db),
    coach: User = Depends(require_role(*COACH_OR_ADMIN)),
):
    return coach_service.get_class_trend(db, coach, class_id, days)


@router.get('/summary')
def coach_summary(
    db: Session = Depends(get_db),
    coach: User = Depends(require_role(*COACH_OR_ADMIN)),
):
    return coach_service.get_coach_summary(db, coach)


@router.get('/available-trainees')
def search_available_trainees(
    keyword: str = '',
    db: Session = Depends(get_db),
    _: User = Depends(require_role(*COACH_OR_ADMIN)),
):
    return coach_service.search_available_trainees(db, keyword)


@router.get('/students/{student_id}/profile')
def get_student_profile(
    student_id: int,
    db: Session = Depends(get_db),
    coach: User = Depends(require_role(*COACH_OR_ADMIN)),
):
    return coach_service.get_student_profile(db, student_id, coach)
