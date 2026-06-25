from fastapi import APIRouter, Depends, WebSocket, WebSocketDisconnect
from sqlalchemy.orm import Session
from typing import List
from backend.database.connection import get_db
from backend.schemas.business import FMSSubmitRequest, FMSResultResponse
from backend.services.fms_service import FMSService, RealtimeFMSService
from backend.services.auth_service import get_current_user
from jose import jwt as jose_jwt
from backend.config import settings
from backend.database.models import User, FMSRecord

router = APIRouter(prefix='/api/fms', tags=['FMS Screening'])

@router.post('/screen', response_model=FMSResultResponse)
def submit_screening(data: FMSSubmitRequest, db: Session = Depends(get_db), user: User = Depends(get_current_user)):
    svc = FMSService(db)
    return svc.process_screening(user.id, data)

@router.get('/records', response_model=List[FMSResultResponse])
def get_records(db: Session = Depends(get_db), user: User = Depends(get_current_user)):
    svc = FMSService(db)
    records = svc.get_user_records(user.id)
    return [FMSResultResponse.model_validate(r) for r in records]

@router.get('/records/{record_id}', response_model=FMSResultResponse)
def get_record_detail(record_id: int, db: Session = Depends(get_db), user: User = Depends(get_current_user)):
    svc = FMSService(db)
    return svc.get_record_detail(record_id, user.id)

@router.websocket('/ws')
async def fms_websocket(ws: WebSocket, db: Session = Depends(get_db)):
    await ws.accept()
    token = ws.query_params.get('token')
    if not token:
        await ws.send_json({'type': 'error', 'message': '缺少认证令牌'})
        await ws.close(code=4001)
        return
    try:
        payload = jose_jwt.decode(token, settings.SECRET_KEY, algorithms=[settings.ALGORITHM])
        user_id = int(payload.get('sub'))
        user = db.query(User).filter(User.id == user_id).first()
        if not user:
            await ws.send_json({'type': 'error', 'message': '用户不存在'})
            await ws.close(code=4003)
            return
    except Exception:
        await ws.send_json({'type': 'error', 'message': '令牌无效或已过期'})
        await ws.close(code=4001)
        return
    svc = RealtimeFMSService(db)
    try:
        await svc.handle_session(ws, user_id)
    except Exception as e:
        try:
            await ws.send_json({'type': 'error', 'message': f'会话异常: {str(e)}'})
        except:
            pass
