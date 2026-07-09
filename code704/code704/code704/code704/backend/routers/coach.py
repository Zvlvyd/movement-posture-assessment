from typing import Optional
from pydantic import BaseModel
from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session
from backend.database.connection import get_db
from backend.database.models import User, UserRole
from backend.services.auth_service import require_role
from backend.services import coach_service

router = APIRouter(prefix='/api/coach', tags=['Coach Management'])


class UpdateClassRequest(BaseModel):
    name: Optional[str] = None
    description: Optional[str] = None

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
    body: UpdateClassRequest,
    db: Session = Depends(get_db),
    coach: User = Depends(require_role(*COACH_OR_ADMIN)),
):
    return coach_service.update_class(db, coach, class_id, body.name, body.description)


@router.delete('/classes/{class_id}')
def delete_class(
    class_id: int,
    db: Session = Depends(get_db),
    coach: User = Depends(require_role(*COACH_OR_ADMIN)),
):
    return coach_service.delete_class(db, coach, class_id)


@router.post('/classes/{class_id}/regenerate-code')
def regenerate_class_code(
    class_id: int,
    db: Session = Depends(get_db),
    coach: User = Depends(require_role(*COACH_OR_ADMIN)),
):
    """重新生成班级邀请码"""
    return coach_service.regenerate_invite_code(db, coach, class_id)


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


@router.get('/students/{student_id}/training-records')
def get_student_training_records(
    student_id: int,
    days: int = Query(30, ge=1, le=365),
    db: Session = Depends(get_db),
    coach: User = Depends(require_role(*COACH_OR_ADMIN)),
):
    """获取学员的训练完成记录（计划训练 + 标准学习）"""
    return coach_service.get_student_training_records(db, student_id, coach, days)


@router.get('/students/{student_id}/training-stats')
def get_student_training_stats(
    student_id: int,
    db: Session = Depends(get_db),
    coach: User = Depends(require_role(*COACH_OR_ADMIN)),
):
    """获取学员训练统计概览"""
    return coach_service.get_student_training_stats(db, student_id, coach)


# ── Plan Change Request Approval ──────────────────────────────────

@router.get('/change-requests', summary="查看待审批的计划变更")
def list_change_requests(
    status: str = None,
    db: Session = Depends(get_db),
    coach: User = Depends(require_role(*COACH_OR_ADMIN)),
):
    from backend.services import plan_edit_service
    return plan_edit_service.list_coach_change_requests(db, coach, status)


@router.get('/change-requests/{cr_id}', summary="查看变更请求详情")
def get_change_request_detail(
    cr_id: int,
    db: Session = Depends(get_db),
    coach: User = Depends(require_role(*COACH_OR_ADMIN)),
):
    from backend.services import plan_edit_service
    return plan_edit_service.get_change_request_detail(db, coach, cr_id)


@router.put('/change-requests/{cr_id}/approve', summary="通过计划变更")
def approve_change_request(
    cr_id: int,
    db: Session = Depends(get_db),
    coach: User = Depends(require_role(*COACH_OR_ADMIN)),
):
    from backend.services import plan_edit_service
    return plan_edit_service.approve_change_request(db, coach, cr_id)


@router.put('/change-requests/{cr_id}/adjust', summary="调整后通过")
def adjust_change_request(
    cr_id: int,
    data: dict,
    db: Session = Depends(get_db),
    coach: User = Depends(require_role(*COACH_OR_ADMIN)),
):
    from backend.services import plan_edit_service
    items = data.get('items', [])
    notes = data.get('coach_notes', '')
    return plan_edit_service.adjust_change_request(db, coach, cr_id, items, notes)


@router.put('/change-requests/{cr_id}/reject', summary="拒绝计划变更")
def reject_change_request(
    cr_id: int,
    data: dict,
    db: Session = Depends(get_db),
    coach: User = Depends(require_role(*COACH_OR_ADMIN)),
):
    from backend.services import plan_edit_service
    notes = data.get('coach_notes', '')
    if not notes:
        from fastapi import HTTPException
        raise HTTPException(status_code=400, detail="拒绝时必须填写原因")
    return plan_edit_service.reject_change_request(db, coach, cr_id, notes)
