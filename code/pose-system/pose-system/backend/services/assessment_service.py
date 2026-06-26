# -*- coding: utf-8 -*-
"""
评估服务 - 替代 fms_service.py
处理静态姿态评估 + 实时运动评估 + 报告存储
"""
import json, math, time
from typing import Dict, List, Optional, Any
from datetime import datetime
from fastapi import WebSocket, HTTPException
from sqlalchemy.orm import Session
import numpy as np

from backend.database import models
from models.assessment import (
    ROMTracker, AsymmetryAnalyzer, UnifiedScoringEngine, ReportGenerator,
    MOVEMENTS, get_movement,
)
from models.assessment.rom_tracker import MovementROMResult
from models.posture_analyzer import PostureAnalyzer
from models.angle_calculator import AngleCalculator


class AssessmentService:
    """评估服务 - 处理评估提交和历史查询"""
    
    def __init__(self, db: Session):
        self.db = db
        self.engine = UnifiedScoringEngine()
        self.posture_analyzer = PostureAnalyzer()
    
    def submit_assessment(
        self, 
        user_id: int,
        keypoints_front: List[List[float]],
        keypoints_side: Optional[List[List[float]]] = None,
        movement_frames: Optional[List[List[List[float]]]] = None,
    ) -> models.AssessmentRecord:
        """
        提交评估数据，运行完整分析管道，存入数据库
        """
        # 1. 静态姿态分析
        measurements = self.posture_analyzer.analyze_from_keypoints(keypoints_front, keypoints_side)
        posture_report = self.posture_analyzer.generate_report(measurements)
        posture_problems = posture_report.get("problems", [])
        flags = measurements.get("flags", [])
        
        # 2. ROM 追踪（如果有运动帧数据）
        movement_results = []
        rom_data_raw = {}
        asymmetry_findings = []
        
        if movement_frames and len(movement_frames) > 1:
            tracker = ROMTracker()
            for frame_kps in movement_frames:
                kp_array = np.array(frame_kps, dtype=np.float32)
                tracker.feed_keypoints(kp_array)
            
            # 提取各关节 ROM
            angle_keys = ["left_knee","right_knee","left_hip","right_hip",
                         "left_shoulder","right_shoulder","left_elbow","right_elbow",
                         "trunk_tilt","neck_tilt"]
            joint_roms = []
            for key in angle_keys:
                side = "left" if "left_" in key else ("right" if "right_" in key else "bilateral")
                rom = tracker.get_joint_rom(key, side, key)
                if rom:
                    joint_roms.append(rom)
                    rom_data_raw[key] = {
                        "rom_deg": rom.rom_deg,
                        "peak_angle": rom.peak_angle,
                        "min_angle": rom.min_angle,
                        "plateau_detected": rom.plateau_detected,
                        "trajectory": rom.trajectory,
                    }
            
            movement_results.append(MovementROMResult(
                0, "realtime_movement", joint_roms,
                len(movement_frames) / 30.0, len(movement_frames)
            ))
            
            # 不对称分析
            pairs = [("left_knee","right_knee"),("left_hip","right_hip"),
                    ("left_shoulder","right_shoulder"),("left_elbow","right_elbow")]
            for lk, rk in pairs:
                lr = next((r for r in joint_roms if r.joint == lk), None)
                rr = next((r for r in joint_roms if r.joint == rk), None)
                if lr and rr:
                    n = self.engine.norms.get(lk, {})
                    f = AsymmetryAnalyzer.analyze_bilateral(
                        lr, rr, n.get("min", 60), n.get("max", 120)
                    )
                    if f:
                        asymmetry_findings.append(f)
        
        # 3. 评分
        scores = self.engine.compute_all(movement_results, flags, asymmetry_findings)
        overall = self.engine.compute_overall(scores)
        risk_level = self.engine.get_risk_level(overall, scores)
        
        # 4. 生成报告
        report = ReportGenerator.generate(
            scores=scores,
            overall=overall,
            risk_level=risk_level,
            posture_problems=posture_problems,
            movement_results=movement_results,
            asymmetry_findings=asymmetry_findings,
        )
        
        # 5. 序列化并存储到数据库
        record = models.AssessmentRecord(
            user_id=user_id,
            balance_score=next((s.score for s in scores if s.dimension == "balance"), 0),
            flexibility_score=next((s.score for s in scores if s.dimension == "flexibility"), 0),
            upper_limb_score=next((s.score for s in scores if s.dimension == "upper_limb"), 0),
            core_score=next((s.score for s in scores if s.dimension == "core"), 0),
            symmetry_score=next((s.score for s in scores if s.dimension == "symmetry"), 0),
            overall_score=overall,
            risk_level=risk_level,
            posture_data=json.dumps({
                "problems": posture_problems,
                "flags": flags,
                "measurements": {k: v for k, v in measurements.items() if k != "flags"},
            }, ensure_ascii=False),
            movement_data=json.dumps({
                "rom_data": rom_data_raw,
                "asymmetry_findings": [
                    {"joint": f.joint, "side_limited": f.side_limited, 
                     "diff_pct": f.diff_pct, "severity": f.severity}
                    for f in asymmetry_findings
                ],
            }, ensure_ascii=False),
            rom_data=json.dumps(rom_data_raw, ensure_ascii=False),
            muscle_findings=json.dumps({
                "tight_muscles": report.muscle_analysis.get("tight_muscles", []),
                "weak_muscles": report.muscle_analysis.get("weak_muscles", []),
            }, ensure_ascii=False),
            report_data=json.dumps({
                "overall_score": report.overall_score,
                "risk_level": report.risk_level,
                "dimensions": [{k: v for k, v in d.items() if k != "details"} for d in report.dimensions],
                "chart_data": report.chart_data,
                "suggestions": report.suggestions,
                "summary": report.summary,
            }, ensure_ascii=False),
        )
        
        self.db.add(record)
        self.db.commit()
        self.db.refresh(record)
        return record
    
    def get_user_records(self, user_id: int) -> List[models.AssessmentRecord]:
        """获取用户所有评估记录"""
        return (
            self.db.query(models.AssessmentRecord)
            .filter(models.AssessmentRecord.user_id == user_id)
            .order_by(models.AssessmentRecord.test_date.desc())
            .all()
        )
    
    def get_record_detail(self, record_id: int, user_id: int) -> models.AssessmentRecord:
        """获取单条评估详情"""
        record = (
            self.db.query(models.AssessmentRecord)
            .filter(
                models.AssessmentRecord.id == record_id,
                models.AssessmentRecord.user_id == user_id,
            )
            .first()
        )
        if not record:
            raise HTTPException(status_code=404, detail="评估记录未找到")
        return record
    
    def build_detail_response(self, record: models.AssessmentRecord) -> Dict:
        """构建包含展开数据的详细响应"""
        response = {
            "id": record.id,
            "user_id": record.user_id,
            "test_date": record.test_date,
            "balance_score": record.balance_score,
            "flexibility_score": record.flexibility_score,
            "upper_limb_score": record.upper_limb_score,
            "core_score": record.core_score,
            "symmetry_score": record.symmetry_score,
            "overall_score": record.overall_score,
            "risk_level": record.risk_level,
        }
        
        # 展开 JSON 字段
        if record.posture_data:
            pd = json.loads(record.posture_data)
            response["posture_problems"] = pd.get("problems", [])
        if record.movement_data:
            md = json.loads(record.movement_data)
            response["asymmetry_findings"] = md.get("asymmetry_findings", [])
        if record.rom_data:
            rd = json.loads(record.rom_data)
            response["rom_analysis"] = [
                {"joint": k, "side": "left" if "left" in k else ("right" if "right" in k else "bilateral"), **v}
                for k, v in rd.items()
            ]
        if record.muscle_findings:
            response["muscle_analysis"] = json.loads(record.muscle_findings)
        if record.report_data:
            rd = json.loads(record.report_data)
            response["chart_data"] = rd.get("chart_data")
            response["suggestions"] = rd.get("suggestions", [])
            response["summary"] = rd.get("summary", "")
        
        return response


    def check_re_test_status(self, user_id: int) -> dict:
        """Check if user is due for periodic re-test."""
        from datetime import datetime, timedelta
        latest_fms = self.db.query(models.FMSRecord).filter(
            models.FMSRecord.user_id == user_id
        ).order_by(models.FMSRecord.test_date.desc()).first()

        latest_assessment = self.db.query(models.AssessmentRecord).filter(
            models.AssessmentRecord.user_id == user_id
        ).order_by(models.AssessmentRecord.test_date.desc()).first()

        active_rx = self.db.query(models.Prescription).filter(
            models.Prescription.user_id == user_id,
            models.Prescription.status == 'active'
        ).order_by(models.Prescription.created_at.desc()).first()

        now = datetime.utcnow()
        days_since_last_test = 999
        last_test_date = None

        if latest_assessment:
            delta = now - latest_assessment.test_date.replace(tzinfo=None) if latest_assessment.test_date else timedelta(days=999)
            days_since_last_test = delta.days
            last_test_date = latest_assessment.test_date
        elif latest_fms:
            delta = now - latest_fms.test_date.replace(tzinfo=None) if latest_fms.test_date else timedelta(days=999)
            days_since_last_test = delta.days
            last_test_date = latest_fms.test_date

        due_for_retest = days_since_last_test >= 14  # Every 2 weeks
        next_phase_available = False
        if active_rx:
            training_count = self.db.query(models.TrainingRecord).filter(
                models.TrainingRecord.user_id == user_id,
                models.TrainingRecord.prescription_id == active_rx.id
            ).count()
            avg_score_record = self.db.query(models.TrainingRecord).filter(
                models.TrainingRecord.user_id == user_id,
                models.TrainingRecord.prescription_id == active_rx.id,
                models.TrainingRecord.total_score.isnot(None)
            ).order_by(models.TrainingRecord.end_time.desc()).first()
            avg_score = avg_score_record.total_score if avg_score_record else 0
            next_phase_available = PrescriptionEngine.should_unlock_next(
                active_rx.phase, training_count, avg_score or 0
            )

        return {
            "due_for_retest": due_for_retest,
            "days_since_last_test": days_since_last_test,
            "last_test_date": str(last_test_date) if last_test_date else None,
            "next_phase_available": next_phase_available,
            "current_phase": active_rx.phase if active_rx else 0,
            "current_difficulty": active_rx.difficulty if active_rx else 0,
        }

    def trigger_phase_upgrade(self, user_id: int, prescription_id: int) -> dict:
        """Upgrade to next phase and prepare for re-test."""
        rx = self.db.query(models.Prescription).filter(
            models.Prescription.id == prescription_id,
            models.Prescription.user_id == user_id
        ).first()
        if not rx:
            raise HTTPException(status_code=404, detail='Prescription not found')

        new_phase = rx.phase + 1
        new_difficulty = rx.difficulty + 1

        # Mark old prescription as completed
        rx.status = 'completed'

        # Create new phase prescription
        new_rx = models.Prescription(
            user_id=user_id,
            fms_record_id=rx.fms_record_id,
            phase=new_phase,
            status='active',
            difficulty=new_difficulty,
            unlocked_at=datetime.utcnow(),
        )
        self.db.add(new_rx)
        self.db.commit()
        return {
            "message": "Phase upgraded successfully",
            "old_phase": rx.phase,
            "new_phase": new_phase,
            "new_prescription_id": new_rx.id,
            "new_difficulty": new_difficulty,
        }

class RealtimeAssessmentService:
    """
    实时评估 WebSocket 服务

    支持两种模式：
    1. 标准模式（无 capture 阶段）：直接开始 5 组引导动作
    2. 三视角捕获模式：先拍正/背/侧三张 → 静态分析 → 定向验证

    三视角模式消息流：
      Client → start
      Server → capture_ready {view: "front", instruction: "..."}
      Client → capture_view {view: "front", data: "<b64>"}
      Server → capture_ready {view: "back"}
      Client → capture_view {view: "back", data: "<b64>"}
      Server → capture_ready {view: "side"}
      Client → capture_view {view: "side", data: "<b64>"}
      Server → static_analysis {findings, summary}
      Server → verification_plan {movements: [...]}
      Server → movement_ready {index: 0, ...}
      (后续与标准模式相同)
    """

    # 三视角捕获顺序
    CAPTURE_ORDER = ["front", "back", "side"]
    CAPTURE_INSTRUCTIONS = {
        "front": "请正对摄像头，双脚与肩同宽，双臂自然下垂，保持站立姿势",
        "back": "请背对摄像头，同样保持自然站立姿势",
        "side": "请侧对摄像头（右侧朝向镜头），保持自然站立姿势",
    }

    def __init__(self, db: Session):
        self.db = db
        self.angle_calc = AngleCalculator()
        self.tracker = ROMTracker()
        self.scoring_engine = UnifiedScoringEngine()
        self.posture_analyzer = PostureAnalyzer()
        self.yolo = None
        self._frames_buffer: List[np.ndarray] = []
        self._best_keypoints: Optional[np.ndarray] = None
        # 三视角捕获状态
        self._capture_keypoints: dict = {}  # {view: keypoints_array}
        self._capture_idx: int = 0
        self._capture_phase: bool = False
        self._verification_plan = None
    
    def _get_yolo(self):
        if self.yolo is None:
            from ultralytics import YOLO
            from config.settings import settings
            self.yolo = YOLO(settings.MODEL_PATH)
        return self.yolo
    
    async def handle(self, ws: WebSocket, user_id: int):
        """Handle alias — delegates to handle_session for unified router interface."""
        return await self.handle_session(ws, user_id)

    async def handle_session(self, ws: WebSocket, user_id: int):
        """处理 WebSocket 实时评估会话（含三视角捕获模式）"""
        current_movement_idx = 0
        self._capture_phase = True  # 默认进入三视角捕获模式
        self._capture_keypoints = {}
        self._capture_idx = 0

        try:
            while True:
                raw = await ws.receive_text()
                msg = json.loads(raw)
                msg_type = msg.get("type", "")

                if msg_type == "start":
                    current_movement_idx = 0
                    self.tracker.reset()
                    self._frames_buffer = []
                    self._best_keypoints = None
                    self._capture_keypoints = {}
                    self._capture_idx = 0
                    self._capture_phase = True

                    # 发送第一个视角的捕获指令
                    first_view = self.CAPTURE_ORDER[0]
                    await ws.send_json({
                        "type": "capture_ready",
                        "view": first_view,
                        "view_index": 0,
                        "total_views": len(self.CAPTURE_ORDER),
                        "instruction": self.CAPTURE_INSTRUCTIONS[first_view],
                    })

                elif msg_type == "capture_view":
                    # 接收三视角捕获帧
                    if not self._capture_phase:
                        await ws.send_json({"type": "error", "message": "不在捕获阶段"})
                        continue

                    view = msg.get("view", "")
                    frame_b64 = msg.get("data", "")

                    if view not in self.CAPTURE_ORDER:
                        await ws.send_json({"type": "error", "message": f"未知视角: {view}"})
                        continue

                    # 解码并提取关键点
                    import base64 as b64_mod
                    import cv2
                    kp_array = None
                    if frame_b64:
                        try:
                            img_data = b64_mod.b64decode(frame_b64.split(",")[-1])
                            nparr = np.frombuffer(img_data, np.uint8)
                            frame = cv2.imdecode(nparr, cv2.IMREAD_COLOR)
                            if frame is not None:
                                h, w = frame.shape[:2]
                                if w > 640:
                                    frame = cv2.resize(frame, (640, int(h * 640 / w)))
                                yolo = self._get_yolo()
                                results = yolo(frame, verbose=False)
                                if results and results[0].keypoints is not None:
                                    kps = results[0].keypoints.data.cpu().numpy()
                                    if kps.shape[0] > 0 and kps.shape[1] >= 17:
                                        kp_array = kps[0, :, :2].tolist()
                        except Exception as e:
                            print(f"[Capture] {view} decode error: {e}")

                    if kp_array is None:
                        await ws.send_json({
                            "type": "capture_error",
                            "view": view,
                            "message": f"未检测到人体，请调整位置后点击「重新拍摄」",
                        })
                        continue

                    self._capture_keypoints[view] = kp_array

                    # 发送骨架数据给前端预览
                    await ws.send_json({
                        "type": "capture_ok",
                        "view": view,
                        "keypoints": kp_array,
                    })

                    # 前进到下一个视角或完成捕获
                    self._capture_idx += 1
                    if self._capture_idx < len(self.CAPTURE_ORDER):
                        next_view = self.CAPTURE_ORDER[self._capture_idx]
                        await ws.send_json({
                            "type": "capture_ready",
                            "view": next_view,
                            "view_index": self._capture_idx,
                            "total_views": len(self.CAPTURE_ORDER),
                            "instruction": self.CAPTURE_INSTRUCTIONS[next_view],
                        })
                    else:
                        # 三个视角全部捕获完成 → 静态分析 + 生成验证计划
                        self._capture_phase = False
                        await self._on_capture_complete(ws)

                elif msg_type == "skip_capture":
                    # 跳过三视角捕获，直接进入标准 5 组动作模式
                    self._capture_phase = False
                    self._capture_keypoints = {}
                    await self._start_standard_flow(ws)

                elif msg_type == "retry_view":
                    # 重新拍摄某个视角
                    view = msg.get("view", "")
                    if view in self.CAPTURE_ORDER:
                        self._capture_keypoints.pop(view, None)
                        # 回退 capture_idx
                        target_idx = self.CAPTURE_ORDER.index(view)
                        self._capture_idx = target_idx
                        await ws.send_json({
                            "type": "capture_ready",
                            "view": view,
                            "view_index": target_idx,
                            "total_views": len(self.CAPTURE_ORDER),
                            "instruction": self.CAPTURE_INSTRUCTIONS[view],
                        })

                elif msg_type == "frame":
                    # 仅在非捕获阶段处理运动帧
                    if self._capture_phase:
                        continue
                    # 收到视频帧（base64 编码的图像）
                    import base64
                    import cv2
                    
                    frame_b64 = msg.get("data", "")
                    if not frame_b64:
                        continue
                    
                    # 解码图像
                    img_data = base64.b64decode(frame_b64.split(",")[-1])
                    nparr = np.frombuffer(img_data, np.uint8)
                    frame = cv2.imdecode(nparr, cv2.IMREAD_COLOR)
                    
                    if frame is None:
                        continue
                    
                    # YOLO 姿态检测
                    h, w = frame.shape[:2]
                    if w > 640:
                        frame = cv2.resize(frame, (640, int(h * 640 / w)))
                    
                    yolo = self._get_yolo()
                    results = yolo(frame, verbose=False)
                    
                    if results and results[0].keypoints is not None:
                        kps = results[0].keypoints.data.cpu().numpy()
                        if kps.shape[0] > 0 and kps.shape[1] >= 17:
                            kp_array = kps[0, :, :2]
                            kp_confs = kps[0, :, 2].tolist() if kps.shape[1] >= 3 else [1.0] * 17
                            self._frames_buffer.append(kp_array)

                            # 保存最佳帧（检测到最多关键点的帧）
                            if self._best_keypoints is None or kps[0, :, 2].mean() > 0.5:
                                self._best_keypoints = kp_array.copy()

                            # ROM 追踪
                            angles = self.tracker.feed_keypoints(kp_array)

                            # 关键点列表（前端骨架绘制需要）
                            keypoints_list = [{
                                "keypoints": kp_array.tolist(),
                                "confidences": kp_confs,
                                "bbox": None,
                            }]

                            # 获取当前动作的目标角度
                            movement = get_movement(current_movement_idx)
                            if movement:
                                target_keys = [t.angle_key for t in movement.targets]
                                current_angles = {
                                    k: round(v, 1) for k, v in angles.items()
                                    if v is not None and k in target_keys
                                }
                                plateau = self.tracker.is_all_plateau(target_keys)
                            else:
                                current_angles = {}
                                plateau = False

                            await ws.send_json({
                                "type": "angles_update",
                                "angles": current_angles,
                                "keypoints": keypoints_list,
                                "frame_count": self.tracker._frame_count,
                                "plateau_detected": plateau,
                            })
                
                elif msg_type == "movement_done":
                    # 当前动作完成
                    movement = get_movement(current_movement_idx)
                    if movement:
                        # 提取 ROM
                        joint_specs = [
                            (t.joint_name, 
                             "left" if "left" in t.angle_key else ("right" if "right" in t.angle_key else "bilateral"),
                             t.angle_key)
                            for t in movement.targets
                        ]
                        target_keys = [t.angle_key for t in movement.targets]
                        
                        rom_summary = self.tracker.get_current_angles_summary(target_keys)
                        
                        await ws.send_json({
                            "type": "movement_completed",
                            "index": current_movement_idx,
                            "name": movement.name,
                            "rom_summary": rom_summary,
                            "frame_count": self.tracker._frame_count,
                        })
                    
                    # 前进到下一个动作
                    current_movement_idx += 1
                    next_movement = get_movement(current_movement_idx)
                    if next_movement:
                        self.tracker.reset()
                        await ws.send_json({
                            "type": "movement_ready",
                            "index": current_movement_idx,
                            "name": next_movement.name,
                            "instruction": next_movement.instruction,
                        })
                    else:
                        # 所有动作完成，生成最终报告
                        await self._send_final_report(ws, user_id)
                
                elif msg_type == "finish":
                    # 用户手动完成
                    await self._send_final_report(ws, user_id)
                    
        except Exception as e:
            try:
                await ws.send_json({"type": "error", "message": str(e)})
            except:
                pass
    
    async def _send_final_report(self, ws: WebSocket, user_id: int):
        """生成并发送最终评估报告"""
        try:
            # 使用最佳帧做静态分析
            if self._best_keypoints is not None:
                kp_list = self._best_keypoints.tolist()
            elif self._frames_buffer:
                kp_list = self._frames_buffer[len(self._frames_buffer) // 3].tolist()
            else:
                await ws.send_json({"type": "error", "message": "没有足够的姿态数据"})
                return
            
            # 1. 静态分析
            measurements = self.posture_analyzer.analyze_from_keypoints(kp_list)
            posture_report = self.posture_analyzer.generate_report(measurements)
            posture_problems = posture_report.get("problems", [])
            flags = measurements.get("flags", [])
            
            # 2. ROM 数据
            angle_keys = ["left_knee","right_knee","left_hip","right_hip",
                         "left_shoulder","right_shoulder","left_elbow","right_elbow",
                         "trunk_tilt","neck_tilt"]
            joint_roms = []
            rom_data_raw = {}
            for key in angle_keys:
                side = "left" if "left_" in key else ("right" if "right_" in key else "bilateral")
                rom = self.tracker.get_joint_rom(key, side, key)
                if rom:
                    joint_roms.append(rom)
                    rom_data_raw[key] = {
                        "rom_deg": rom.rom_deg, "peak_angle": rom.peak_angle,
                        "min_angle": rom.min_angle, "plateau_detected": rom.plateau_detected,
                    }
            
            movement_results = [MovementROMResult(
                0, "assessment_session", joint_roms,
                len(self._frames_buffer) / 30.0, len(self._frames_buffer)
            )]
            
            # 3. 不对称
            asymmetry_findings = []
            pairs = [("left_knee","right_knee"),("left_hip","right_hip"),
                    ("left_shoulder","right_shoulder"),("left_elbow","right_elbow")]
            for lk, rk in pairs:
                lr = next((r for r in joint_roms if r.joint == lk), None)
                rr = next((r for r in joint_roms if r.joint == rk), None)
                if lr and rr:
                    n = self.scoring_engine.norms.get(lk, {})
                    f = AsymmetryAnalyzer.analyze_bilateral(lr, rr, n.get("min", 60), n.get("max", 120))
                    if f:
                        asymmetry_findings.append(f)
            
            # 4. 评分
            scores = self.scoring_engine.compute_all(movement_results, flags, asymmetry_findings)
            overall = self.scoring_engine.compute_overall(scores)
            risk_level = self.scoring_engine.get_risk_level(overall, scores)
            
            # 5. 报告
            report = ReportGenerator.generate(
                scores=scores, overall=overall, risk_level=risk_level,
                posture_problems=posture_problems,
                movement_results=movement_results,
                asymmetry_findings=asymmetry_findings,
            )
            
            # 6. 存入数据库
            record = models.AssessmentRecord(
                user_id=user_id,
                balance_score=next((s.score for s in scores if s.dimension == "balance"), 0),
                flexibility_score=next((s.score for s in scores if s.dimension == "flexibility"), 0),
                upper_limb_score=next((s.score for s in scores if s.dimension == "upper_limb"), 0),
                core_score=next((s.score for s in scores if s.dimension == "core"), 0),
                symmetry_score=next((s.score for s in scores if s.dimension == "symmetry"), 0),
                overall_score=overall,
                risk_level=risk_level,
                posture_data=json.dumps({"problems": posture_problems, "flags": flags}, ensure_ascii=False),
                movement_data=json.dumps({
                    "asymmetry_findings": [
                        {"joint": f.joint, "side_limited": f.side_limited,
                         "diff_pct": f.diff_pct, "severity": f.severity}
                        for f in asymmetry_findings
                    ],
                }, ensure_ascii=False),
                rom_data=json.dumps(rom_data_raw, ensure_ascii=False),
                muscle_findings=json.dumps({
                    "tight_muscles": report.muscle_analysis.get("tight_muscles", []),
                    "weak_muscles": report.muscle_analysis.get("weak_muscles", []),
                }, ensure_ascii=False),
                report_data=json.dumps({
                    "overall_score": report.overall_score,
                    "risk_level": report.risk_level,
                    "chart_data": report.chart_data,
                    "suggestions": report.suggestions,
                    "summary": report.summary,
                }, ensure_ascii=False),
            )
            
            self.db.add(record)
            self.db.commit()
            self.db.refresh(record)
            
            # 7. 发送完整报告
            await ws.send_json({
                "type": "assessment_complete",
                "record_id": record.id,
                "overall_score": overall,
                "risk_level": risk_level,
                "dimensions": [{k: v for k, v in d.items() if k != "details"} for d in report.dimensions],
                "chart_data": report.chart_data,
                "posture_problems": [
                    {"name": p.get("name"), "severity": p.get("severity")}
                    for p in posture_problems
                ],
                "asymmetry_findings": [
                    {"joint": f.joint, "diff_pct": f.diff_pct, "severity": f.severity}
                    for f in asymmetry_findings
                ],
                "muscle_analysis": {
                    "tight_count": report.muscle_analysis.get("tight_count", 0),
                    "weak_count": report.muscle_analysis.get("weak_count", 0),
                },
                "suggestions": report.suggestions,
                "summary": report.summary,
            })

        except Exception as e:
            await ws.send_json({"type": "error", "message": str(e)})

    async def _on_capture_complete(self, ws: WebSocket):
        """三视角捕获完成 → 静态分析 + 定向验证计划。"""
        try:
            front_kps = self._capture_keypoints.get("front")
            back_kps = self._capture_keypoints.get("back")
            side_kps = self._capture_keypoints.get("side")

            from models.assessment.multi_view_analyzer import MultiViewAnalyzer
            from models.assessment.verification_mapper import VerificationMapper

            analyzer = MultiViewAnalyzer()
            merged = analyzer.analyze(
                front_kps=front_kps, back_kps=back_kps, side_kps=side_kps,
            )
            severity_map = {f.flag: f.severity for f in merged.findings}
            plan = VerificationMapper.build_plan(merged.flags, severity_map)
            skipped = VerificationMapper.get_skipped_notes(merged.flags)
            self._verification_plan = plan

            await ws.send_json({
                "type": "static_analysis",
                "findings": [
                    {"flag": f.flag, "name": f.name, "severity": f.severity,
                     "value": f.value, "unit": f.unit, "normal_range": f.normal_range,
                     "source_views": f.source_views}
                    for f in merged.findings
                ],
                "summary": merged.summary,
                "skipped_notes": skipped,
            })
            await ws.send_json({
                "type": "verification_plan",
                "movements": [
                    {"index": vm.movement_def.index, "name": vm.movement_def.name,
                     "instruction": vm.instruction_override or vm.movement_def.instruction,
                     "trigger_problems": vm.trigger_problems,
                     "has_velocity_check": len(vm.velocity_pairs) > 0}
                    for vm in plan
                ],
                "total_movements": len(plan),
                "is_targeted": len(plan) < 5,
            })
            if plan:
                first = plan[0]
                await ws.send_json({
                    "type": "movement_ready",
                    "index": first.movement_def.index, "name": first.movement_def.name,
                    "instruction": first.instruction_override or first.movement_def.instruction,
                    "is_verification": True,
                })
            else:
                await ws.send_json({
                    "type": "assessment_complete", "overall_score": 100.0,
                    "risk_level": "low",
                    "message": "静态分析未发现需要验证的体态问题",
                })
        except Exception as e:
            await ws.send_json({"type": "error", "message": f"静态分析失败: {str(e)}"})

    async def _start_standard_flow(self, ws: WebSocket):
        """跳过三视角捕获，直接开始标准5组动作。"""
        movement = get_movement(0)
        await ws.send_json({
            "type": "assessment_started",
            "total_movements": len(MOVEMENTS),
            "movements": [
                {"index": m.index, "name": m.name, "instruction": m.instruction,
                 "duration_hint": m.duration_hint}
                for m in MOVEMENTS
            ],
        })
        await ws.send_json({
            "type": "movement_ready", "index": 0,
            "name": movement.name if movement else "",
            "instruction": movement.instruction if movement else "",
        })


class VerificationWebSocketHandler:
    """
    WebSocket handler for targeted ROM verification based on static findings.
    Replaces the standard 5-movement flow when verification_mode=true.

    WS message flow:
      Server → client: verification_plan (movement list)
      Client → server: start_movement {movement_index}
      Server → client: movement_ready {index, name, instruction}
      Client → server: frame {image_b64 / keypoints}
      Server → client: angles_update {angles, keypoints, plateaus}
      Server → client: velocity_alert {joint, severity} (if asymmetry detected)
      Client → server: movement_done
      Server → client: movement_completed {rom_summary}
      Client → server: finish
      Server → client: verification_complete {fusion_report}
    """

    def __init__(self, db: Session):
        self.db = db
        self.angle_calc = AngleCalculator()
        self.tracker = ROMTracker()
        self.velocity_analyzer = None  # Lazy init
        self.yolo = None

    def _get_velocity_analyzer(self):
        if self.velocity_analyzer is None:
            from models.assessment.velocity_analyzer import VelocityAnalyzer
            self.velocity_analyzer = VelocityAnalyzer()
        return self.velocity_analyzer

    def _get_yolo(self):
        if self.yolo is None:
            from ultralytics import YOLO
            from config.settings import settings
            self.yolo = YOLO(settings.MODEL_PATH)
        return self.yolo

    async def handle(self, ws: WebSocket, user_id: int):
        """
        Handle verification-mode WebSocket session.
        ws.accept() must be called by the router before this.
        """
        from models.assessment.multi_view_session import multi_view_session_store
        from models.assessment import VerificationMapper, FusionEngine

        current_movement_idx = -1
        all_velocity_findings = []
        all_rom_ratios = {}
        all_movement_results = {}
        verification_plan = None
        session_id = None

        try:
            while True:
                raw = await ws.receive_text()
                msg = json.loads(raw)
                msg_type = msg.get("type", "")

                if msg_type == "start":
                    # Begin verification for a multi-view session
                    session_id = msg.get("session_id", "")
                    session = multi_view_session_store.get(session_id) if session_id else None

                    if session is None:
                        await ws.send_json({"type": "error", "message": "无效或过期的验证会话"})
                        continue

                    verification_plan = session.verification_plan
                    self.tracker.reset()
                    all_velocity_findings = []
                    all_rom_ratios = {}
                    all_movement_results = {}

                    await ws.send_json({
                        "type": "verification_plan",
                        "session_id": session_id,
                        "movements": [
                            {
                                "index": vm.movement_def.index,
                                "name": vm.movement_def.name,
                                "instruction": vm.instruction_override or vm.movement_def.instruction,
                                "trigger_problems": vm.trigger_problems,
                                "key_rom_track": vm.key_rom_track,
                                "has_velocity_check": len(vm.velocity_pairs) > 0,
                            }
                            for vm in verification_plan
                        ],
                        "total_movements": len(verification_plan),
                    })

                elif msg_type == "start_movement":
                    mov_idx = msg.get("movement_index", 0)
                    current_movement_idx = mov_idx
                    self.tracker.reset()

                    vm = next(
                        (v for v in verification_plan if v.movement_def.index == mov_idx),
                        None
                    ) if verification_plan else None

                    if vm:
                        await ws.send_json({
                            "type": "movement_ready",
                            "index": mov_idx,
                            "name": vm.movement_def.name,
                            "instruction": vm.instruction_override or vm.movement_def.instruction,
                            "has_velocity_check": len(vm.velocity_pairs) > 0,
                        })

                elif msg_type == "frame":
                    if current_movement_idx < 0:
                        await ws.send_json({"type": "error", "message": "请先 start_movement"})
                        continue

                    import base64 as b64_mod
                    import cv2

                    frame_b64 = msg.get("data", "")
                    keypoints_list = []

                    if frame_b64:
                        img_data = b64_mod.b64decode(frame_b64.split(",")[-1])
                        nparr = np.frombuffer(img_data, np.uint8)
                        frame = cv2.imdecode(nparr, cv2.IMREAD_COLOR)

                        if frame is not None:
                            h, w = frame.shape[:2]
                            if w > 640:
                                frame = cv2.resize(frame, (640, int(h * 640 / w)))

                            yolo = self._get_yolo()
                            results = yolo(frame, verbose=False)

                            if results and results[0].keypoints is not None:
                                kps = results[0].keypoints.data.cpu().numpy()
                                if kps.shape[0] > 0 and kps.shape[1] >= 17:
                                    kp_array = kps[0, :, :2]
                                    kp_confs = kps[0, :, 2].tolist() if kps.shape[1] >= 3 else [1.0] * 17
                                    angles = self.tracker.feed_keypoints(kp_array)

                                    keypoints_list = [{
                                        "keypoints": kp_array.tolist(),
                                        "confidences": kp_confs,
                                        "bbox": None,
                                    }]

                                    # Get current angles for target keys
                                    vm = next(
                                        (v for v in verification_plan if v.movement_def.index == current_movement_idx),
                                        None
                                    ) if verification_plan else None

                                    current_angles = {}
                                    velocity_alert = None

                                    if vm and vm.key_rom_track:
                                        current_angles = {
                                            k: round(v, 1) for k, v in angles.items()
                                            if v is not None and k in vm.key_rom_track
                                        }

                                        # Real-time velocity check
                                        if vm.velocity_pairs:
                                            v_analyzer = self._get_velocity_analyzer()
                                            for left_key, right_key in vm.velocity_pairs:
                                                left_hist = self.tracker.get_velocity_history(left_key)
                                                right_hist = self.tracker.get_velocity_history(right_key)
                                                if left_hist and right_hist:
                                                    alert = v_analyzer.compare_velocity_realtime(
                                                        left_hist, right_hist
                                                    )
                                                    if alert:
                                                        velocity_alert = {
                                                            "joint": left_key.replace("left_", ""),
                                                            "severity": alert["severity"],
                                                            "max_diff_pct": alert["max_diff_pct"],
                                                            "duration_frames": alert["duration_frames"],
                                                        }

                                    await ws.send_json({
                                        "type": "angles_update",
                                        "angles": current_angles,
                                        "keypoints": keypoints_list,
                                        "frame_count": self.tracker._frame_count,
                                        "velocity_alert": velocity_alert,
                                    })

                elif msg_type == "movement_done":
                    vm = next(
                        (v for v in verification_plan if v.movement_def.index == current_movement_idx),
                        None
                    ) if verification_plan else None

                    if vm:
                        # Extract ROM for key tracking joints
                        for key in vm.key_rom_track:
                            rom = self.tracker.get_joint_rom(key, "bilateral", key)
                            if rom and hasattr(rom, 'rom_deg') and rom.rom_deg > 0:
                                from models.assessment.scoring import UnifiedScoringEngine
                                engine = UnifiedScoringEngine()
                                norm = engine.norms.get(key, {})
                                norm_min = norm.get("min", 60)
                                if norm_min > 0:
                                    ratio = rom.rom_deg / norm_min
                                    all_rom_ratios[key] = min(ratio, 1.5)

                        # Run velocity analysis on paired joints
                        if vm.velocity_pairs:
                            v_analyzer = self._get_velocity_analyzer()
                            vel_findings = v_analyzer.analyze_pairs(self.tracker, vm.velocity_pairs)
                            all_velocity_findings.extend(vel_findings)

                        # Collect ROM summary
                        rom_summary = self.tracker.get_current_angles_summary(vm.key_rom_track)
                        all_movement_results[current_movement_idx] = {
                            "movement_index": current_movement_idx,
                            "movement_name": vm.movement_def.name,
                            "rom_summary": rom_summary,
                            "frame_count": self.tracker._frame_count,
                            "velocity_findings": [
                                {"joint": vf.joint, "severity": vf.severity,
                                 "max_diff_pct": vf.max_velocity_diff_pct,
                                 "duration_frames": vf.duration_frames}
                                for vf in all_velocity_findings
                            ],
                        }

                        await ws.send_json({
                            "type": "movement_completed",
                            "index": current_movement_idx,
                            "name": vm.movement_def.name,
                            "rom_summary": rom_summary,
                            "velocity_findings": [
                                {"joint": vf.joint, "severity": vf.severity,
                                 "detail": vf.detail}
                                for vf in all_velocity_findings
                            ],
                            "frame_count": self.tracker._frame_count,
                        })

                elif msg_type == "finish":
                    await self._send_verification_result(
                        ws, user_id, session_id, all_rom_ratios, all_velocity_findings,
                        all_movement_results
                    )

        except Exception as e:
            try:
                await ws.send_json({"type": "error", "message": str(e)})
            except:
                pass

    async def _send_verification_result(self, ws, user_id, session_id,
                                         all_rom_ratios, all_velocity_findings,
                                         all_movement_results):
        """Generate and send the final fusion report via WebSocket."""
        try:
            from models.assessment.multi_view_session import multi_view_session_store
            from models.assessment import FusionEngine

            session = multi_view_session_store.get(session_id) if session_id else None
            if session is None or session.merged_findings is None:
                await ws.send_json({"type": "error", "message": "会话数据不完整"})
                return

            # Run fusion
            fusion_engine = FusionEngine()
            fusion_result = fusion_engine.fuse(
                static_findings=session.merged_findings.findings,
                rom_ratios=all_rom_ratios,
                velocity_findings=all_velocity_findings,
            )

            session.velocity_findings = all_velocity_findings
            session.rom_ratios = all_rom_ratios
            session.fusion_result = fusion_result
            session.status = "fused"

            # Persist to DB
            from backend.database import models as db_models
            import json as json_mod

            scores = self._compute_dimension_scores(fusion_result)
            overall = fusion_result.fused_overall_score

            if overall >= 70:
                risk = "low"
            elif overall >= 40:
                risk = "medium"
            else:
                risk = "high"

            record = db_models.AssessmentRecord(
                user_id=user_id,
                balance_score=scores.get("balance", 0),
                flexibility_score=scores.get("flexibility", 0),
                upper_limb_score=scores.get("upper_limb", 0),
                core_score=scores.get("core", 0),
                symmetry_score=scores.get("symmetry", 0),
                overall_score=overall,
                risk_level=risk,
                assessment_type="multi_view",
                session_id=session_id,
                fusion_data=json_mod.dumps({
                    "validations": [{
                        "flag": v.problem_flag, "verdict": v.verdict,
                        "final_confidence": v.final_confidence,
                    } for v in fusion_result.validations],
                    "confirmed": fusion_result.confirmed_count,
                    "rejected": fusion_result.rejected_count,
                    "adjusted": fusion_result.adjusted_count,
                }, ensure_ascii=False),
                velocity_data=json_mod.dumps({
                    "findings": [{
                        "joint": f.joint, "severity": f.severity,
                        "max_diff_pct": f.max_velocity_diff_pct,
                        "duration_frames": f.duration_frames,
                    } for f in all_velocity_findings],
                }, ensure_ascii=False),
                rom_data=json_mod.dumps(all_rom_ratios, ensure_ascii=False),
                report_data=json_mod.dumps({
                    "dimensions": [{
                        "dimension": d, "label": l, "score": scores.get(d, 0),
                    } for d, l in [
                        ("balance","平衡"), ("flexibility","灵活性"),
                        ("upper_limb","上肢"), ("core","核心"), ("symmetry","对称性"),
                    ]],
                }, ensure_ascii=False),
            )

            db.add(record)
            db.commit()
            db.refresh(record)
            session.record_id = record.id

            await ws.send_json({
                "type": "verification_complete",
                "record_id": record.id,
                "validations": [{
                    "problem_flag": v.problem_flag,
                    "problem_name": v.problem_name,
                    "static_severity": v.static_severity,
                    "final_confidence": v.final_confidence,
                    "verdict": v.verdict,
                    "adjusted_severity": v.adjusted_severity,
                    "explanation": v.explanation,
                } for v in fusion_result.validations],
                "fused_overall_score": fusion_result.fused_overall_score,
                "confirmed_count": fusion_result.confirmed_count,
                "rejected_count": fusion_result.rejected_count,
                "adjusted_count": fusion_result.adjusted_count,
                "unverified_count": fusion_result.unverified_count,
            })

        except Exception as e:
            await ws.send_json({"type": "error", "message": str(e)})

    def _compute_dimension_scores(self, fusion_result) -> dict:
        """Compute 5-dimension scores from validated findings."""
        flag_dimension = {
            "shoulder_imbalance": "symmetry",
            "pelvic_lateral_tilt": "symmetry",
            "head_forward_posture": "upper_limb",
            "knee_hyperextension": "flexibility",
            "pelvic_anterior_tilt": "core",
            "pelvic_posterior_tilt": "core",
            "possible_scoliosis": "symmetry",
        }
        penalty_map = {"severe": 30, "moderate": 20, "mild": 10, "normal": 0}

        dimension_penalties = {d: 0 for d in ["balance", "flexibility", "upper_limb", "core", "symmetry"]}

        for v in fusion_result.validations:
            if v.verdict == "rejected":
                continue
            dim = flag_dimension.get(v.problem_flag)
            if dim:
                dimension_penalties[dim] += penalty_map.get(v.adjusted_severity, 0)

        return {d: max(0, 100 - p) for d, p in dimension_penalties.items()}
