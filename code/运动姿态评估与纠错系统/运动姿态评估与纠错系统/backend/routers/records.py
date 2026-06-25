from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session
from backend.database.connection import get_db
from backend.services.report_service import ReportService
from backend.services.auth_service import get_current_user
from backend.database.models import User

router = APIRouter(prefix='/api/records', tags=['Records & Stats'])

@router.get('/stats')
def get_stats(db: Session = Depends(get_db), user: User = Depends(get_current_user)):
    svc = ReportService(db)
    return svc.get_training_stats(user.id)

@router.get('/history')
def get_history(days: int = 30, db: Session = Depends(get_db), user: User = Depends(get_current_user)):
    svc = ReportService(db)
    records = svc.get_training_history(user.id, days)
    from backend.schemas.business import TrainingRecordResponse
    return [TrainingRecordResponse.model_validate(r) for r in records]
