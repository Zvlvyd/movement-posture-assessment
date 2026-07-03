from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session
from typing import List
from backend.database.connection import get_db
from backend.schemas.business import PrescriptionResponse
from backend.services.prescription_service import PrescriptionService
from backend.services.auth_service import get_current_user
from backend.database.models import User

router = APIRouter(prefix='/api/prescription', tags=['Prescription'])



from pydantic import BaseModel

class PlanOption(BaseModel):
    plan_id: int
    plan_name: str
    recommended: bool
    difficulty: int
    items: List[dict]

class PlanOptionsResponse(BaseModel):
    fms_record_id: int
    plans: List[PlanOption]

@router.post('/generate-plans/{fms_record_id}', response_model=PlanOptionsResponse)
def generate_plans(fms_record_id: int, db: Session = Depends(get_db), user: User = Depends(get_current_user)):
    """Generate 3 plan options for the user. Plans are not saved yet - user picks one."""
    svc = PrescriptionService(db)
    plans_data = svc.generate_plan_options(user.id, fms_record_id)
    return PlanOptionsResponse(fms_record_id=fms_record_id, plans=plans_data)

@router.post('/activate/{fms_record_id}', response_model=PrescriptionResponse)
def activate_plan(fms_record_id: int, plan_id: int, db: Session = Depends(get_db), user: User = Depends(get_current_user)):
    """Activate a chosen plan by saving it to the database."""
    svc = PrescriptionService(db)
    return svc.activate_plan(user.id, fms_record_id, plan_id)

@router.post('/posture-plan/{assessment_record_id}')
def generate_posture_plan(
    assessment_record_id: int,
    use_equipment: bool = True,
    intensity: str = 'medium',
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
):
    """Generate prescription based on detected posture problems.
    
    Args:
        assessment_record_id: assessment record ID (contains detected problems)
        use_equipment: whether to include equipment-based exercises
        intensity: low / medium / high
    """
    svc = PrescriptionService(db)
    plan = svc.generate_posture_plan(user.id, assessment_record_id, use_equipment, intensity)
    return plan

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



