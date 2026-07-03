# -*- coding: utf-8 -*-
"""
Plan edit service — modify plan items, submit for coach approval, coach review.

Flow:
  Student not in class → direct save
  Student in class → create PlanChangeRequest → coach reviews → approve/adjust/reject
"""
import json
from datetime import datetime
from typing import List, Optional

from sqlalchemy.orm import Session
from fastapi import HTTPException

from backend.database.models import User, ClassGroup, class_group_student, PlanChangeRequest
from backend.database.models_v2 import PrescriptionPlan, PrescriptionPlanItem


# ── Helpers ────────────────────────────────────────────────────────

def _check_in_class(db: Session, student: User) -> Optional[User]:
    """Return the student's coach if they are in any class, else None."""
    membership = db.query(class_group_student).filter(
        class_group_student.c.user_id == student.id,
    ).first()
    if not membership:
        return None
    group = db.query(ClassGroup).filter(
        ClassGroup.id == membership.class_group_id,
    ).first()
    return group.coach if group else None


def _snapshot_items(plan: PrescriptionPlan) -> List[dict]:
    """Create a JSON snapshot of current plan items."""
    return [
        {
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
        }
        for item in (plan.items or [])
    ]


def _apply_items(db: Session, plan: PrescriptionPlan, items_data: List[dict]):
    """Replace plan items with the given data."""
    # Delete existing items
    for item in list(plan.items or []):
        db.delete(item)
    db.flush()
    # Create new items
    for i, item_data in enumerate(items_data):
        new_item = PrescriptionPlanItem(
            plan_id=plan.id,
            action_id=item_data.get('action_id', ''),
            action_name=item_data.get('action_name', ''),
            family_name=item_data.get('family_name', ''),
            category=item_data.get('category', ''),
            phase=item_data.get('phase', 'main'),
            sets=item_data.get('sets', 3),
            reps=item_data.get('reps', 10),
            duration_seconds=item_data.get('duration_seconds', 0),
            order_index=item_data.get('order_index', i + 1),
            difficulty=item_data.get('difficulty', 1),
            intensity=item_data.get('intensity', 'MEDIUM'),
            notes=item_data.get('notes', ''),
        )
        db.add(new_item)
    plan.status = 'draft'
    db.commit()


# ── Student: Edit Plan ────────────────────────────────────────────

def edit_plan(db: Session, student: User, plan_id: int, data: dict) -> dict:
    """
    Edit a plan. If student is in a class, create a change request.
    If not in any class, apply changes directly.
    """
    plan = db.query(PrescriptionPlan).filter(
        PrescriptionPlan.id == plan_id,
        PrescriptionPlan.user_id == student.id,
    ).first()
    if not plan:
        raise HTTPException(status_code=404, detail="计划不存在")

    coach = _check_in_class(db, student)
    new_items = data.get('items')

    if coach and new_items:
        # In a class → create change request
        original = _snapshot_items(plan)
        cr = PlanChangeRequest(
            plan_id=plan.id,
            student_id=student.id,
            coach_id=coach.id,
            status='pending',
            original_snapshot=json.dumps(original, ensure_ascii=False),
            proposed_items=json.dumps(new_items, ensure_ascii=False),
            student_notes=data.get('student_notes', ''),
        )
        db.add(cr)
        db.commit()
        db.refresh(cr)

        # Auto-create message for coach
        from backend.database.models import Message
        msg = Message(
            sender_id=student.id,
            receiver_id=coach.id,
            content=f"学员「{student.username}」提交了计划「{plan.plan_name}」的修改请求，请审批。",
            related_type='change_request',
            related_id=cr.id,
        )
        db.add(msg)
        db.commit()

        return {
            'message': '修改请求已提交，等待教练审批',
            'change_request_id': cr.id,
            'status': 'pending',
            'coach_name': coach.username,
        }
    else:
        # Not in any class → apply directly
        if data.get('plan_name'):
            plan.plan_name = data['plan_name']
        if data.get('overall_strategy'):
            plan.overall_strategy = data['overall_strategy']
        if new_items:
            _apply_items(db, plan, new_items)
        else:
            db.commit()

        return {
            'message': '计划已更新',
            'status': 'applied',
            'plan_id': plan.id,
        }


# ── Student: Submit Change Request ─────────────────────────────────

def submit_change_request(db: Session, student: User, plan_id: int, notes: str = '') -> dict:
    """Explicitly submit a plan change for coach approval."""
    coach = _check_in_class(db, student)
    if not coach:
        raise HTTPException(status_code=400, detail="你没有加入任何班级，可以直接修改计划")

    plan = db.query(PrescriptionPlan).filter(
        PrescriptionPlan.id == plan_id,
        PrescriptionPlan.user_id == student.id,
    ).first()
    if not plan:
        raise HTTPException(status_code=404, detail="计划不存在")

    original = _snapshot_items(plan)
    cr = PlanChangeRequest(
        plan_id=plan.id,
        student_id=student.id,
        coach_id=coach.id,
        status='pending',
        original_snapshot=json.dumps(original, ensure_ascii=False),
        proposed_items=json.dumps(original, ensure_ascii=False),
        student_notes=notes,
    )
    db.add(cr)
    db.commit()
    db.refresh(cr)

    from backend.database.models import Message
    msg = Message(
        sender_id=student.id,
        receiver_id=coach.id,
        content=f"学员「{student.username}」请求审批计划「{plan.plan_name}」{('：' + notes) if notes else ''}",
        related_type='change_request',
        related_id=cr.id,
    )
    db.add(msg)
    db.commit()

    return {'message': '已提交审批', 'change_request_id': cr.id}


# ── Student: List My Change Requests ───────────────────────────────

def list_my_change_requests(db: Session, student: User) -> List[dict]:
    crs = db.query(PlanChangeRequest).filter(
        PlanChangeRequest.student_id == student.id,
    ).order_by(PlanChangeRequest.created_at.desc()).all()

    return [_serialize_cr(cr) for cr in crs]


# ── Coach: List Pending Change Requests ────────────────────────────

def list_coach_change_requests(db: Session, coach: User, status: str = None) -> dict:
    q = db.query(PlanChangeRequest).filter(PlanChangeRequest.coach_id == coach.id)
    if status:
        q = q.filter(PlanChangeRequest.status == status)
    else:
        q = q.filter(PlanChangeRequest.status == 'pending')
    crs = q.order_by(PlanChangeRequest.created_at.desc()).all()

    return {
        'requests': [_serialize_cr(cr) for cr in crs],
        'total': len(crs),
    }


# ── Coach: Get Change Request Detail ───────────────────────────────

def get_change_request_detail(db: Session, coach: User, cr_id: int) -> dict:
    cr = db.query(PlanChangeRequest).filter(
        PlanChangeRequest.id == cr_id,
        PlanChangeRequest.coach_id == coach.id,
    ).first()
    if not cr:
        raise HTTPException(status_code=404, detail="审批请求不存在")
    return _serialize_cr(cr)


# ── Coach: Approve ─────────────────────────────────────────────────

def approve_change_request(db: Session, coach: User, cr_id: int) -> dict:
    cr = _get_cr_for_coach(db, coach, cr_id)
    if cr.status != 'pending':
        raise HTTPException(status_code=400, detail="该请求已处理")

    plan = db.query(PrescriptionPlan).filter(PrescriptionPlan.id == cr.plan_id).first()
    if not plan:
        raise HTTPException(status_code=404, detail="计划不存在")

    # Apply proposed items
    proposed = json.loads(cr.proposed_items) if cr.proposed_items else []
    _apply_items(db, plan, proposed)
    plan.status = 'active'
    cr.status = 'approved'
    cr.updated_at = datetime.utcnow()
    db.commit()

    # Notify student
    from backend.database.models import Message
    msg = Message(
        sender_id=coach.id,
        receiver_id=cr.student_id,
        content=f"教练「{coach.username}」已通过你对计划「{plan.plan_name}」的修改。",
        related_type='change_request',
        related_id=cr.id,
    )
    db.add(msg)
    db.commit()

    return {'message': '已通过审批，计划已更新', 'status': 'approved'}


# ── Coach: Adjust ─────────────────────────────────────────────────

def adjust_change_request(db: Session, coach: User, cr_id: int, items: List[dict], notes: str = '') -> dict:
    cr = _get_cr_for_coach(db, coach, cr_id)
    if cr.status != 'pending':
        raise HTTPException(status_code=400, detail="该请求已处理")

    plan = db.query(PrescriptionPlan).filter(PrescriptionPlan.id == cr.plan_id).first()
    if not plan:
        raise HTTPException(status_code=404, detail="计划不存在")

    _apply_items(db, plan, items)
    plan.status = 'active'
    cr.status = 'adjusted'
    cr.coach_items = json.dumps(items, ensure_ascii=False)
    cr.coach_notes = notes
    cr.updated_at = datetime.utcnow()
    db.commit()

    from backend.database.models import Message
    msg = Message(
        sender_id=coach.id,
        receiver_id=cr.student_id,
        content=f"教练「{coach.username}」已调整并通过对计划「{plan.plan_name}」的修改{('：' + notes) if notes else ''}",
        related_type='change_request',
        related_id=cr.id,
    )
    db.add(msg)
    db.commit()

    return {'message': '已调整并通过，计划已更新', 'status': 'adjusted'}


# ── Coach: Reject ──────────────────────────────────────────────────

def reject_change_request(db: Session, coach: User, cr_id: int, notes: str) -> dict:
    cr = _get_cr_for_coach(db, coach, cr_id)
    if cr.status != 'pending':
        raise HTTPException(status_code=400, detail="该请求已处理")

    cr.status = 'rejected'
    cr.coach_notes = notes
    cr.updated_at = datetime.utcnow()
    db.commit()

    from backend.database.models import Message
    plan = db.query(PrescriptionPlan).filter(PrescriptionPlan.id == cr.plan_id).first()
    plan_name = plan.plan_name if plan else "未知计划"
    msg = Message(
        sender_id=coach.id,
        receiver_id=cr.student_id,
        content=f"教练「{coach.username}」拒绝了你的计划「{plan_name}」修改请求。原因：{notes}",
        related_type='change_request',
        related_id=cr.id,
    )
    db.add(msg)
    db.commit()

    return {'message': '已拒绝修改请求', 'status': 'rejected'}


# ── Internal ───────────────────────────────────────────────────────

def _get_cr_for_coach(db: Session, coach: User, cr_id: int) -> PlanChangeRequest:
    cr = db.query(PlanChangeRequest).filter(
        PlanChangeRequest.id == cr_id,
        PlanChangeRequest.coach_id == coach.id,
    ).first()
    if not cr:
        raise HTTPException(status_code=404, detail="审批请求不存在")
    return cr


def _serialize_cr(cr: PlanChangeRequest) -> dict:
    plan = None
    try:
        plan = cr.plan_id
    except:
        pass
    return {
        'id': cr.id,
        'plan_id': cr.plan_id,
        'plan_name': getattr(cr, '_plan_name', ''),
        'student_id': cr.student_id,
        'student_name': cr.student.username if cr.student else '',
        'coach_id': cr.coach_id,
        'status': cr.status,
        'original_snapshot': cr.original_snapshot,
        'proposed_items': cr.proposed_items,
        'coach_items': cr.coach_items,
        'coach_notes': cr.coach_notes,
        'student_notes': cr.student_notes,
        'created_at': str(cr.created_at),
        'updated_at': str(cr.updated_at) if cr.updated_at else None,
    }
