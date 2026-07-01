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


@router.delete('/classes/{class_id}/students/{student_id}')
def remove_student(
    class_id: int,
    student_id: int,
    db: Session = Depends(get_db),
    coach: User = Depends(require_role(*COACH_OR_ADMIN)),
):
    return coach_service.remove_student_from_class(db, coach, class_id, student_id)


@router.put('/classes/{class_id}')
def update_class(
    class_id: int,
    name: str = None,
    description: str = None,
    db: Session = Depends(get_db),
    coach: User = Depends(require_role(*COACH_OR_ADMIN)),
):
    return coach_service.update_class(db, coach, class_id, name, description)


@router.delete('/classes/{class_id}')
def delete_class(
    class_id: int,
    db: Session = Depends(get_db),
    coach: User = Depends(require_role(*COACH_OR_ADMIN)),
):
    return coach_service.delete_class(db, coach, class_id)


@router.get('/students/{student_id}/profile')
def get_student_profile(
    student_id: int,
    db: Session = Depends(get_db),
    coach: User = Depends(require_role(*COACH_OR_ADMIN)),
):
    return coach_service.get_student_profile(db, student_id, coach)


@router.get('/students/{student_id}/plans')
def list_student_plans(
    student_id: int,
    db: Session = Depends(get_db),
    coach: User = Depends(require_role(*COACH_OR_ADMIN)),
):
    return coach_service.get_student_prescription_plans(db, student_id, coach)


@router.get('/students/{student_id}/plans/{plan_id}')
def get_student_plan_detail(
    student_id: int,
    plan_id: int,
    db: Session = Depends(get_db),
    coach: User = Depends(require_role(*COACH_OR_ADMIN)),
):
    return coach_service.get_student_plan_detail(db, student_id, plan_id, coach)


@router.delete('/students/{student_id}/plans/{plan_id}')
def delete_student_plan(
    student_id: int,
    plan_id: int,
    db: Session = Depends(get_db),
    coach: User = Depends(require_role(*COACH_OR_ADMIN)),
):
    return coach_service.delete_student_prescription_plan(db, student_id, plan_id, coach)
