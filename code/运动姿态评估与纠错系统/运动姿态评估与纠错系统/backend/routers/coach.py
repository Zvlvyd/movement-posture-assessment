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
