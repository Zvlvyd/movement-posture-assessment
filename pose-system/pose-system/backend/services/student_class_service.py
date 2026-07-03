# -*- coding: utf-8 -*-
"""
Student class management service — join class by invite code, list my classes, leave class.

Follows the same layered architecture:
  routers (thin) → services (logic) → database/models
"""
import secrets
import string as _string
from typing import List

from sqlalchemy.orm import Session
from fastapi import HTTPException

from backend.database.models import User, UserRole, ClassGroup, class_group_student


# ── Invite code generation ──────────────────────────────────────────────

def _generate_invite_code() -> str:
    """生成 8 位大写字母+数字组合邀请码"""
    chars = _string.ascii_uppercase + _string.digits
    return ''.join(secrets.choice(chars) for _ in range(8))


def _generate_unique_invite_code(db: Session) -> str:
    """生成唯一邀请码，碰撞时重试最多10次"""
    for _ in range(10):
        code = _generate_invite_code()
        if not db.query(ClassGroup).filter(ClassGroup.invite_code == code).first():
            return code
    raise HTTPException(status_code=500, detail="无法生成唯一邀请码，请重试")


# ── Serialization helpers ───────────────────────────────────────────────

def _serialize_class_for_student(group: ClassGroup) -> dict:
    """将班级序列化为学员视角的字典（包含教练信息和学员人数）"""
    coach = group.coach
    return {
        'class_id': group.id,
        'class_name': group.name,
        'description': group.description,
        'invite_code': group.invite_code,
        'coach': {
            'id': coach.id,
            'username': coach.username,
            'phone': coach.phone,
        },
        'student_count': len(group.students) if group.students else 0,
        'created_at': str(group.created_at),
    }


# ── Student class operations ────────────────────────────────────────────

def join_class_by_code(db: Session, student: User, invite_code: str) -> dict:
    """学员通过邀请码加入班级"""
    # 验证邀请码存在
    group = db.query(ClassGroup).filter(
        ClassGroup.invite_code == invite_code.strip().upper()
    ).first()
    if not group:
        raise HTTPException(status_code=404, detail='邀请码无效，未找到对应班级')

    # 验证是否已在该班级中
    if student in group.students:
        raise HTTPException(status_code=400, detail='你已在该班级中，无需重复加入')

    # 加入班级
    group.students.append(student)
    db.commit()
    db.refresh(group)

    return {
        'message': f'成功加入班级「{group.name}」',
        'class_info': _serialize_class_for_student(group),
    }


def list_my_classes(db: Session, student: User) -> List[dict]:
    """列出学员已加入的班级，包含教练信息"""
    # 通过关联表查询（student.class_groups 不存在，需手动查）
    groups = db.query(ClassGroup).join(
        class_group_student,
        ClassGroup.id == class_group_student.c.class_group_id,
    ).filter(
        class_group_student.c.user_id == student.id,
    ).all()

    return [_serialize_class_for_student(g) for g in groups]


def get_my_class_detail(db: Session, student: User, class_id: int) -> dict:
    """获取单个班级详情（学员视角），验证学员在该班级中"""
    group = db.query(ClassGroup).filter(ClassGroup.id == class_id).first()
    if not group:
        raise HTTPException(status_code=404, detail='班级不存在')

    if student not in group.students:
        raise HTTPException(status_code=403, detail='你不在该班级中')

    return _serialize_class_for_student(group)


def leave_class(db: Session, student: User, class_id: int) -> dict:
    """学员退出班级"""
    group = db.query(ClassGroup).filter(ClassGroup.id == class_id).first()
    if not group:
        raise HTTPException(status_code=404, detail='班级不存在')

    if student not in group.students:
        raise HTTPException(status_code=400, detail='你不在该班级中')

    group.students.remove(student)
    db.commit()

    return {'message': f'已退出班级「{group.name}」'}
