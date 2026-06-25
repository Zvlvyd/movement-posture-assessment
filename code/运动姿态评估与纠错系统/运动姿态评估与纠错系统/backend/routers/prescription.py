from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session
from typing import List
from backend.database.connection import get_db
from backend.schemas.business import PrescriptionResponse
from backend.services.prescription_service import PrescriptionService
from backend.services.auth_service import get_current_user
from backend.database.models import User

router = APIRouter(prefix='/api/prescription', tags=['Prescription'])

@router.post('/generate/{fms_record_id}', response_model=PrescriptionResponse)
def generate_prescription(fms_record_id: int, db: Session = Depends(get_db), user: User = Depends(get_current_user)):
    svc = PrescriptionService(db)
    return svc.generate_from_fms(user.id, fms_record_id)

@router.get('', response_model=List[PrescriptionResponse])
def list_prescriptions(db: Session = Depends(get_db), user: User = Depends(get_current_user)):
    svc = PrescriptionService(db)
    return svc.get_user_prescriptions(user.id)

@router.get('/{rx_id}', response_model=PrescriptionResponse)
def get_prescription(rx_id: int, db: Session = Depends(get_db), user: User = Depends(get_current_user)):
    svc = PrescriptionService(db)
    return svc.get_prescription(rx_id, user.id)
