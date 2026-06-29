import os
import uuid
import shutil
from fastapi import APIRouter, Depends, WebSocket, UploadFile, File, HTTPException
from sqlalchemy.orm import Session
from typing import List
from backend.database.connection import get_db
from backend.schemas.business import FMSSubmitRequest, FMSResultResponse
from backend.services.fms_service import FMSService, RealtimeFMSService, VideoFMSService
from backend.services.auth_service import get_current_user
from backend.logger import get_logger

logger = get_logger(__name__)
from jose import jwt as jose_jwt
from config.settings import settings
from backend.database.models import User, FMSRecord

router = APIRouter(prefix='/api/fms', tags=['FMS Screening'])

UPLOAD_DIR = os.path.join(os.getcwd(), "uploads", "fms_videos")
os.makedirs(UPLOAD_DIR, exist_ok=True)


@router.post("/upload-video/{test_index}")
async def upload_fms_video(
    test_index: int,
    file: UploadFile = File(...),
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
):
    """上传单个 FMS 动作的视频，后端逐帧处理并返回该动作的评分

    test_index: 0-闭眼单腿站立, 1-过头深蹲, 2-肩活动度, 3-平板支撑, 4-弓步蹲
    """
    if test_index < 0 or test_index > 4:
        raise HTTPException(status_code=400, detail="test_index 必须为 0-4")
    if not file.filename:
        raise HTTPException(status_code=400, detail="未选择文件")

    ext = os.path.splitext(file.filename)[1] or ".mp4"
    filename = f"fms_{user.id}_{test_index}_{uuid.uuid4().hex}{ext}"
    filepath = os.path.join(UPLOAD_DIR, filename)

    with open(filepath, "wb") as f:
        shutil.copyfileobj(file.file, f)

    try:
        svc = VideoFMSService(db)
        result = await svc.process_single_test_video(filepath, test_index, user.id)
        return result
    except Exception as e:
        logger.exception("视频处理失败")
        raise HTTPException(status_code=500, detail=f"视频处理失败: {str(e)}")
    finally:
        try:
            os.remove(filepath)
        except:
            pass


@router.post("/upload-video-combine")
async def upload_fms_video_combine(
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
):
    """合并所有已上传的单个动作评分，生成最终 FMS 报告"""
    svc = VideoFMSService(db)
    result = await svc.combine_results(user.id)
    return result


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
