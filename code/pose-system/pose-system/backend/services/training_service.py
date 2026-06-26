from sqlalchemy.orm import Session
from fastapi import HTTPException, WebSocket
from backend.database import models
from backend.schemas.business import TrainingRecordResponse, TrainingSessionResponse
from models.scoring import DualModeScorer
from models.angle_calculator import AngleCalculator
from models.action_recognizer.squat_fsm import get_fsm_for_action, get_initial_state, get_fsm_context
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
        # prescription_id 为 None 或 0 表示实时训练（不关联处方）
        if prescription_id:
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

    def process_frame(self, keypoints_data: list, action_name: str, mode: str, fsm=None) -> dict:
        if not keypoints_data:
            return {'error': 'no keypoints'}
        keypoints = np.array(keypoints_data, dtype=np.float32)
        angles = self.angle_calc.compute_all_angles(keypoints)

        if mode == 'basic':
            result = DualModeScorer.score_basic(angles, action_name)
        else:
            result = DualModeScorer.score_advanced(angles, action_name)

        fsm_ctx = get_fsm_context(action_name, angles)
        if fsm is not None:
            try:
                fsm.update(fsm_ctx)
                result['fsm_state'] = fsm.get_state()
                result['fsm_progress'] = fsm.get_progress()
            except Exception:
                result['fsm_state'] = 'unknown'
                result['fsm_progress'] = 0.0
        else:
            result['fsm_state'] = 'initializing'
            result['fsm_progress'] = 0.0

        result['angles'] = {k: v for k, v in angles.items() if v is not None}
        return result


class TrainingWebSocketHandler:
    def __init__(self, training_service: TrainingService):
        self.service = training_service
        self.yolo = None
        # Persist FSM instances keyed by (session_id, action_name)
        self._fsm_store: dict = {}

    def _get_yolo(self):
        if self.yolo is None:
            from models.yolo_pose_engine import YOLOPoseEngine
            from config.settings import settings
            self.yolo = YOLOPoseEngine(model_path=settings.MODEL_PATH, device=settings.DEVICE)
        return self.yolo

    def _decode_base64_frame(self, b64_str: str):
        try:
            img_data = base64.b64decode(b64_str.split(",")[-1] if "," in b64_str else b64_str)
            np_arr = np.frombuffer(img_data, np.uint8)
            frame = cv2.imdecode(np_arr, cv2.IMREAD_COLOR)
            return frame
        except:
            return None

    def _get_or_create_fsm(self, session_id: int, action_name: str, initial_ctx: dict):
        key = (session_id, action_name)
        if key not in self._fsm_store:
            fsm = get_fsm_for_action(action_name)
            init_state = get_initial_state(action_name)
            fsm.start(init_state, initial_ctx)
            self._fsm_store[key] = fsm
        return self._fsm_store[key]

    def _guidance_for_state(self, action_name: str, fsm_state: str) -> str:
        action = action_name.lower()
        guidance_map = {
            'squat': {
                'standing': '准备好了吗？开始下蹲！',
                'descending': '很好，继续蹲下去...',
                'bottom': '到达底部！保持住，然后慢慢站起',
                'ascending': '正在站起，控制动作',
                'complete': '完成一次深蹲！继续下一次',
            },
            'lunge': {
                'standing': '准备好，向前迈出弓步！',
                'lunging': '继续下蹲，前膝不要超过脚尖',
                'bottom': '到达弓步最低点，保持稳定',
                'recovering': '回收前腿，控制节奏',
                'complete': '完成一次弓步！换腿继续',
            },
            'pushup': {
                'top': '手臂伸直，保持身体一条直线',
                'descending': '缓慢下降，肘部贴近身体',
                'bottom': '到达底部，胸接近地面',
                'ascending': '推起身体，保持核心收紧',
                'complete': '完成一次俯卧撑！',
            },
            'plank': {
                'ready': '准备进入平板支撑姿势',
                'holding': '保持！身体成一条直线',
                'drooping': '臀部下降太多，收紧核心抬起',
                'recovering': '调整姿势中...',
                'complete': '平板支撑完成！',
            },
            'shoulder_press': {
                'rest': '准备开始肩推，哑铃在肩部高度',
                'pressing': '向上推起，手臂伸直',
                'top': '到达顶部，不要锁死肘关节',
                'lowering': '缓慢下放，控制动作',
                'complete': '完成一次肩推！',
            },
            'jumping_jack': {
                'standing': '准备开始开合跳！',
                'jumping_up': '跳起，手臂上举，双腿打开',
                'open': '到达最高点，保持姿势',
                'closing': '下落回收，手臂放下',
                'complete': '完成一次开合跳！继续',
            },
            'deadlift': {
                'standing': '准备开始硬拉，保持背部挺直',
                'lowering': '屈髋下放，保持背部挺直',
                'bottom': '到达底部，准备拉起',
                'lifting': '伸髋拉起，收紧臀部',
                'complete': '完成一次硬拉！',
            },
        }
        action_guide = guidance_map.get(action, {})
        return action_guide.get(fsm_state, '请保持标准姿势')

    async def handle(self, ws: WebSocket, user_id: int):
        await ws.accept()
        session_id = None
        action_name = 'squat'
        mode = 'basic'
        self._fsm_store.clear()
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
                    # Clear any stale FSM for this session
                    stale_keys = [k for k in self._fsm_store if k[0] == session_id]
                    for k in stale_keys:
                        del self._fsm_store[k]
                    await ws.send_json({
                        'type': 'started', 'session_id': session_id,
                        'guidance': '准备开始训练，请站在画面中央'
                    })

                elif msg_type == 'frame':
                    if session_id is None:
                        await ws.send_json({'type': 'error', 'message': 'session not started'})
                        continue

                    try:
                        action_name = msg.get('action_name', action_name)
                        b64 = msg.get('image', '')
                        keypoints_data = msg.get('keypoints', [])

                        if b64 and not keypoints_data:
                            frame = self._decode_base64_frame(b64)
                            if frame is not None:
                                yolo = self._get_yolo()
                                persons, _ = yolo.process_frame(frame)
                                if persons:
                                    kps = persons[0].get("keypoints", [])
                                    keypoints_data = kps
                                else:
                                    await ws.send_json({
                                        'type': 'result', 'fms_status': 'no_person',
                                        'guidance': '请让全身入镜，站在画面中央',
                                        'keypoints': []
                                    })
                                    continue

                        if keypoints_data:
                            # Get or create persistent FSM for (session, action)
                            fsm = self._get_or_create_fsm(session_id, action_name, {})
                            result = self.service.process_frame(keypoints_data, action_name, mode, fsm)
                            result['type'] = 'result'
                            result['keypoints'] = keypoints_data[:17] if len(keypoints_data) > 17 else keypoints_data

                            fsm_state = result.get('fsm_state', '')
                            result['guidance'] = self._guidance_for_state(action_name, fsm_state)
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
                            await ws.send_json({'type': 'error', 'message': f'处理帧失败: {str(e)}'})
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
        finally:
            # Clean up FSM store for this session
            stale_keys = [k for k in self._fsm_store if k[0] == session_id]
            for k in stale_keys:
                del self._fsm_store[k]

