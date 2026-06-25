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


class RealtimeAssessmentService:
    """实时评估 WebSocket 服务"""
    
    def __init__(self, db: Session):
        self.db = db
        self.angle_calc = AngleCalculator()
        self.tracker = ROMTracker()
        self.scoring_engine = UnifiedScoringEngine()
        self.posture_analyzer = PostureAnalyzer()
        self.yolo = None
        self._frames_buffer: List[np.ndarray] = []
        self._best_keypoints: Optional[np.ndarray] = None
    
    def _get_yolo(self):
        if self.yolo is None:
            from ultralytics import YOLO
            from backend.config import settings
            self.yolo = YOLO(settings.MODEL_PATH)
        return self.yolo
    
    async def handle_session(self, ws: WebSocket, user_id: int):
        """处理 WebSocket 实时评估会话
        注意：ws.accept() 已在路由层调用，此处不再重复。
        """
        current_movement_idx = 0
        
        try:
            while True:
                raw = await ws.receive_text()
                msg = json.loads(raw)
                msg_type = msg.get("type", "")
                
                if msg_type == "start":
                    # 开始评估
                    current_movement_idx = 0
                    self.tracker.reset()
                    self._frames_buffer = []
                    self._best_keypoints = None
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
                        "type": "movement_ready",
                        "index": 0,
                        "name": movement.name if movement else "",
                        "instruction": movement.instruction if movement else "",
                    })
                
                elif msg_type == "frame":
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
                            self._frames_buffer.append(kp_array)
                            
                            # 保存最佳帧（检测到最多关键点的帧）
                            if self._best_keypoints is None or kps[0, :, 2].mean() > 0.5:
                                self._best_keypoints = kp_array.copy()
                            
                            # ROM 追踪
                            angles = self.tracker.feed_keypoints(kp_array)
                            
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
