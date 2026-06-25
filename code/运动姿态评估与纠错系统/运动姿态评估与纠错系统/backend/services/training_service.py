from sqlalchemy.orm import Session
from fastapi import HTTPException, WebSocket
from backend.database import models
from backend.schemas.business import TrainingRecordResponse, TrainingSessionResponse
from models.scoring import DualModeScorer
from models.angle_calculator import AngleCalculator
from models.action_recognizer.squat_fsm import get_fsm_for_action
import json
import numpy as np
import base64
import cv2
from datetime import datetime

class TrainingService:
    def __init__(self, db: Session):
        self.db = db
        self.angle_calc = AngleCalculator()

    def start_session(self, user_id: int, prescription_id: int, mode: str) -> models.TrainingRecord:
        rx = self.db.query(models.Prescription).filter(
            models.Prescription.id == prescription_id, models.Prescription.user_id == user_id
        ).first()
        if not rx:
            raise HTTPException(status_code=404, detail='Prescription not found')
        record = models.TrainingRecord(
            user_id=user_id, prescription_id=prescription_id,
            start_time=datetime.utcnow(), mode=mode
        )
        self.db.add(record)
        self.db.commit()
        self.db.refresh(record)
        return record

    def end_session(self, record_id: int, user_id: int, score: float = None) -> TrainingRecordResponse:
        record = self.db.query(models.TrainingRecord).filter(
            models.TrainingRecord.id == record_id, models.TrainingRecord.user_id == user_id
        ).first()
        if not record:
            raise HTTPException(status_code=404, detail='Training record not found')
        record.end_time = datetime.utcnow()
        if score is not None:
            record.total_score = score
        self.db.commit()
        self.db.refresh(record)
        return TrainingRecordResponse.model_validate(record)

    def process_frame(self, keypoints_data: list, action_name: str, mode: str) -> dict:
        if not keypoints_data:
            return {'error': 'no keypoints'}
        keypoints = np.array(keypoints_data, dtype=np.float32)
        angles = self.angle_calc.compute_all_angles(keypoints)
        knee_angle = angles.get('left_knee') or angles.get('right_knee') or 180.0
        if mode == 'basic':
            result = DualModeScorer.score_basic(angles, action_name)
        else:
            result = DualModeScorer.score_advanced(angles, action_name)
        fsm = get_fsm_for_action(action_name)
        fsm.start('standing', {'knee_angle': knee_angle})
        fsm.update({'knee_angle': knee_angle})
        result['fsm_state'] = fsm.get_state()
        result['fsm_progress'] = fsm.get_progress()
        result['angles'] = {k: v for k, v in angles.items() if v is not None}
        return result

class TrainingWebSocketHandler:
    def __init__(self, training_service: TrainingService):
        self.service = training_service
        self.yolo = None

    def _get_yolo(self):
        if self.yolo is None:
            from models.yolo_pose_engine import YOLOPoseEngine
            from backend.config import settings
            self.yolo = YOLOPoseEngine(model_path=settings.MODEL_PATH, device=settings.DEVICE)
        return self.yolo

    def _decode_base64_frame(self, b64_str: str):
        """Decode base64 image string to numpy array"""
        try:
            img_data = base64.b64decode(b64_str.split(",")[-1] if "," in b64_str else b64_str)
            np_arr = np.frombuffer(img_data, np.uint8)
            frame = cv2.imdecode(np_arr, cv2.IMREAD_COLOR)
            return frame
        except:
            return None

    async def handle(self, ws: WebSocket, user_id: int):
        await ws.accept()
        session_id = None
        action_name = 'squat'
        mode = 'basic'
        try:
            while True:
                data = await ws.receive_text()
                msg = json.loads(data)
                msg_type = msg.get('type')
                
                if msg_type == 'start':
                    rx_id = msg.get('prescription_id')
                    mode = msg.get('mode', 'basic')
                    action_name = msg.get('action_name', 'squat')
                    record = self.service.start_session(user_id, rx_id, mode)
                    session_id = record.id
                    await ws.send_json({
                        'type': 'started', 'session_id': session_id,
                        'guidance': '准备开始训练，请站在画面中央'
                    })
                    
                elif msg_type == 'frame':
                    if session_id is None:
                        await ws.send_json({'type': 'error', 'message': 'session not started'})
                        continue
                    
                    try:
                        action_name = msg.get('action_name', 'squat')
                        b64 = msg.get('image', '')
                    
                        # Try base64 image first, fallback to keypoints
                        keypoints_data = msg.get('keypoints', [])
                    
                        if b64 and not keypoints_data:
                            # Run YOLO on base64 frame
                            frame = self._decode_base64_frame(b64)
                            if frame is not None:
                                yolo = self._get_yolo()
                                persons, _ = yolo.process_frame(frame)
                                if persons:
                                    kps = persons[0].get("keypoints", [])
                                    confs = persons[0].get("confidences", [1.0]*len(kps))
                                    keypoints_data = kps
                                    # Include keypoints for frontend overlay
                                else:
                                    await ws.send_json({
                                        'type': 'result', 'fms_status': 'no_person',
                                        'guidance': '请让全身入镜，站在画面中央',
                                        'keypoints': []
                                    })
                                    continue
                        
                        if keypoints_data:
                            result = self.service.process_frame(keypoints_data, action_name, mode)
                            result['type'] = 'result'
                            result['keypoints'] = keypoints_data[:17] if len(keypoints_data) > 17 else keypoints_data
                        
                            # Add guidance based on FSM state
                            fsm_state = result.get('fsm_state', '')
                            if fsm_state == 'standing':
                                result['guidance'] = '准备好了吗？开始下蹲！'
                            elif fsm_state == 'squatting':
                                result['guidance'] = '很好，继续蹲下去...'
                            elif fsm_state == 'bottom':
                                result['guidance'] = '到达底部！保持住，然后慢慢站起'
                            elif fsm_state == 'rising':
                                result['guidance'] = '正在站起，控制动作'
                            else:
                                result['guidance'] = '请保持标准姿势'
                        
                            await ws.send_json(result)
                        else:
                            await ws.send_json({
                                'type': 'result', 'error': 'no person detected',
                                'guidance': '未检测到人体，请调整站位',
                                'keypoints': []
                            })
                        
                    except Exception as e:
                        import traceback
                        print(f'Training frame error: {e}')
                        traceback.print_exc()
                        try:
                            await ws.send_json({'type':'error','message':f'处理帧失败: {str(e)}'})
                        except:
                            pass
                elif msg_type == 'end':
                    if session_id is not None:
                        score = msg.get('score')
                        self.service.end_session(session_id, user_id, score)
                    await ws.send_json({'type': 'ended', 'session_id': session_id, 'guidance': '训练结束！'})
                    break
                    
                elif msg_type == 'ping':
                    await ws.send_json({'type': 'pong'})
                    
        except Exception as e:
            if session_id is not None:
                try:
                    self.service.end_session(session_id, user_id)
                except:
                    pass
            try:
                await ws.send_json({'type': 'error', 'message': str(e)})
            except:
                pass
