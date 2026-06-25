from fastapi import APIRouter, Depends, WebSocket, WebSocketDisconnect
from sqlalchemy.orm import Session
from typing import List
from backend.database.connection import get_db
from backend.schemas.business import TrainingStartRequest, TrainingRecordResponse, TrainingSessionResponse
from backend.services.training_service import TrainingService, TrainingWebSocketHandler
from backend.services.auth_service import get_current_user
from backend.database.models import User

router = APIRouter(prefix='/api/training', tags=['Training'])

@router.post('/start', response_model=TrainingRecordResponse)
def start_training(data: TrainingStartRequest, db: Session = Depends(get_db), user: User = Depends(get_current_user)):
    svc = TrainingService(db)
    record = svc.start_session(user.id, data.prescription_id, data.mode)
    return TrainingRecordResponse.model_validate(record)

@router.post('/{record_id}/end', response_model=TrainingRecordResponse)
def end_training(record_id: int, db: Session = Depends(get_db), user: User = Depends(get_current_user), score: float = None):
    svc = TrainingService(db)
    return svc.end_session(record_id, user.id, score)

@router.get('/records', response_model=List[TrainingRecordResponse])
def get_training_records(db: Session = Depends(get_db), user: User = Depends(get_current_user)):
    from backend.services.report_service import ReportService
    svc = ReportService(db)
    records = svc.get_training_history(user.id)
    return [TrainingRecordResponse.model_validate(r) for r in records]

@router.websocket('/ws')
async def training_websocket(ws: WebSocket, db: Session = Depends(get_db)):
    # Note: WebSocket auth via query param token
    from jose import jwt as jose_jwt
    from backend.config import settings
    from backend.database import models as db_models
    token = ws.query_params.get('token')
    if not token:
        await ws.close(code=4001, reason='Missing token')
        return
    try:
        payload = jose_jwt.decode(token, settings.SECRET_KEY, algorithms=[settings.ALGORITHM])
        user_id = int(payload.get('sub'))
        user = db.query(User).filter(User.id == user_id).first()
        if not user:
            await ws.close(code=4003, reason='User not found')
            return
    except Exception:
        await ws.close(code=4001, reason='Invalid token')
        return
    svc = TrainingService(db)
    handler = TrainingWebSocketHandler(svc)
    await handler.handle(ws, user_id)
