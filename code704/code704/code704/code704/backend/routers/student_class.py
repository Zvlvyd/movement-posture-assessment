# -*- coding: utf-8 -*-
"""
Student class router — join by invite code, list my classes, leave class.

All endpoints require trainee role authentication.
"""
from fastapi import APIRouter, Depends
from backend.database.connection import get_db
from backend.services.auth_service import get_current_user, require_role
from backend.database.models import User, UserRole
from backend.services import student_class_service
from backend.schemas.student_class import (
    JoinClassRequest, JoinClassResponse,
    MyClassListResponse, MyClassResponse,
    LeaveClassResponse,
)

router = APIRouter(prefix="/api/class", tags=["Student Class"])


@router.post("/join", response_model=JoinClassResponse, summary="通过邀请码加入班级")
def join_class(
    req: JoinClassRequest,
    student: User = Depends(require_role(UserRole.TRAINEE)),
    db=Depends(get_db),
):
    """学员输入8位邀请码加入对应班级"""
    return student_class_service.join_class_by_code(db, student, req.invite_code)


@router.get("/my-classes", response_model=MyClassListResponse, summary="查看我已加入的班级")
def list_my_classes(
    student: User = Depends(require_role(UserRole.TRAINEE)),
    db=Depends(get_db),
):
    """返回学员已加入的所有班级（含教练信息）"""
    classes = student_class_service.list_my_classes(db, student)
    return {"classes": classes}


@router.get("/my-classes/{class_id}", response_model=MyClassResponse, summary="查看班级详情")
def get_my_class_detail(
    class_id: int,
    student: User = Depends(require_role(UserRole.TRAINEE)),
    db=Depends(get_db),
):
    """获取学员视角下的单个班级详情"""
    return student_class_service.get_my_class_detail(db, student, class_id)


@router.delete("/my-classes/{class_id}/leave", response_model=LeaveClassResponse, summary="退出班级")
def leave_class(
    class_id: int,
    student: User = Depends(require_role(UserRole.TRAINEE)),
    db=Depends(get_db),
):
    """学员退出指定班级"""
    return student_class_service.leave_class(db, student, class_id)
