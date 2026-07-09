# -*- coding: utf-8 -*-
"""
Multi-View Assessment Router
Endpoints for three-photo upload posture assessment with ROM verification.

POST  /api/assessment/multi-view/upload           — upload 3 photos → static analysis + verification plan
GET   /api/assessment/multi-view/verification-plan/{sid}  — get verification plan
POST  /api/assessment/multi-view/submit-verification/{sid} — submit ROM data → fusion report
"""
import json
import base64
import numpy as np
import cv2
from datetime import datetime
from fastapi import APIRouter, Depends, HTTPException
from backend.logger import get_logger

logger = get_logger(__name__)
from sqlalchemy.orm import Session

from backend.database.connection import get_db
from backend.database import models as db_models
from backend.schemas.business import (
    MultiViewUploadRequest, MultiViewUploadResponse,
    StaticFindingSchema, VerificationMovementSchema,
    VerificationSubmitRequest, FusionReportResponse, FindingValidationSchema,
)
from backend.services.auth_service import get_current_user
from backend.database.models import User
from models.assessment import (
    MultiViewAnalyzer, VerificationMapper, VelocityAnalyzer, FusionEngine,
)
from models.assessment.rom_tracker import ROMTracker, MovementROMResult
from models.assessment.multi_view_session import multi_view_session_store, MultiViewSession
from models.assessment.movement_definitions import get_movement

router = APIRouter(prefix="/api/assessment/multi-view", tags=["Multi-View Assessment"])


def _decode_b64_to_keypoints(b64_str: str):
    """
    Decode base64 image, run YOLO-Pose, return keypoints for the first detected person.
    Returns (17, 3) numpy array or None.
    """
    if not b64_str:
        return None

    try:
        img_data = base64.b64decode(b64_str.split(",")[-1] if "," in b64_str else b64_str)
        np_arr = np.frombuffer(img_data, np.uint8)
        frame = cv2.imdecode(np_arr, cv2.IMREAD_COLOR)
        if frame is None:
            return None

        from ultralytics import YOLO
        from config.settings import settings

        yolo = YOLO(settings.MODEL_PATH)
        results = yolo(frame, verbose=False)

        if results and results[0].keypoints is not None:
            kps = results[0].keypoints.data.cpu().numpy()
            if kps.shape[0] > 0 and kps.shape[1] >= 17:
                return kps[0]  # (17, 3) [x, y, conf]

        return None
    except Exception as e:
        logger.warning("[MultiView] Keypoint extraction error: %s", e)
        return None


@router.post("/upload", response_model=MultiViewUploadResponse)
def upload_photos(
    data: MultiViewUploadRequest,
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
):
    """
    Upload 3 photos (front/back/side), run YOLO-Pose on each,
    perform multi-view static analysis, and generate verification plan.
    """
    # Decode each photo → keypoints
    front_kps = _decode_b64_to_keypoints(data.front_image_b64)
    back_kps = _decode_b64_to_keypoints(data.back_image_b64)
    side_kps = _decode_b64_to_keypoints(data.side_image_b64)

    if front_kps is None and back_kps is None and side_kps is None:
        raise HTTPException(status_code=400, detail="所有照片均未检测到人体，请重新拍摄")

    # Multi-view analysis
    analyzer = MultiViewAnalyzer()
    merged = analyzer.analyze(
        front_kps=front_kps.tolist() if front_kps is not None else None,
        back_kps=back_kps.tolist() if back_kps is not None else None,
        side_kps=side_kps.tolist() if side_kps is not None else None,
    )

    # Build verification plan
    severity_map = {f.flag: f.severity for f in merged.findings}
    plan = VerificationMapper.build_plan(merged.flags, severity_map)
    skipped = VerificationMapper.get_skipped_notes(merged.flags)

    # Create session
    session = multi_view_session_store.create(user.id)
    session.front_keypoints = front_kps.tolist() if front_kps is not None else None
    session.back_keypoints = back_kps.tolist() if back_kps is not None else None
    session.side_keypoints = side_kps.tolist() if side_kps is not None else None
    session.merged_findings = merged
    session.verification_plan = plan
    session.status = "analyzed"

    # Build response
    static_findings = [
        StaticFindingSchema(
            flag=f.flag,
            name=f.name,
            severity=f.severity,
            value=f.value,
            unit=f.unit,
            normal_range=f.normal_range,
            source_views=f.source_views,
        )
        for f in merged.findings
    ]

    verification_plan_schema = [
        VerificationMovementSchema(
            movement_index=vm.movement_def.index,
            movement_name=vm.movement_def.name,
            instruction=vm.instruction_override or vm.movement_def.instruction,
            trigger_problems=vm.trigger_problems,
            priority=vm.priority,
            key_rom_track=vm.key_rom_track,
            velocity_pairs=[list(p) for p in vm.velocity_pairs],
            instruction_override=vm.instruction_override,
        )
        for vm in plan
    ]

    return MultiViewUploadResponse(
        session_id=session.session_id,
        status=session.status,
        static_findings=static_findings,
        static_summary=merged.summary,
        verification_plan=verification_plan_schema,
        skipped_notes=skipped,
    )


@router.get("/verification-plan/{session_id}")
def get_verification_plan(
    session_id: str,
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
):
    """Retrieve the verification plan for a session."""
    session = multi_view_session_store.get(session_id)
    if session is None:
        raise HTTPException(status_code=404, detail="会话不存在或已过期")
    if session.user_id != user.id:
        raise HTTPException(status_code=403, detail="无权访问此会话")

    plan_schema = [
        VerificationMovementSchema(
            movement_index=vm.movement_def.index,
            movement_name=vm.movement_def.name,
            instruction=vm.instruction_override or vm.movement_def.instruction,
            trigger_problems=vm.trigger_problems,
            priority=vm.priority,
            key_rom_track=vm.key_rom_track,
            velocity_pairs=[list(p) for p in vm.velocity_pairs],
            instruction_override=vm.instruction_override,
        )
        for vm in session.verification_plan
    ]

    return {
        "session_id": session_id,
        "status": session.status,
        "verification_plan": plan_schema,
    }


@router.post("/submit-verification/{session_id}", response_model=FusionReportResponse)
def submit_verification(
    session_id: str,
    data: VerificationSubmitRequest,
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
):
    """
    Submit ROM tracking data from verification movements.
    Runs velocity analysis + fusion, returns validated report.
    """
    session = multi_view_session_store.get(session_id)
    if session is None:
        raise HTTPException(status_code=404, detail="会话不存在或已过期")
    if session.user_id != user.id:
        raise HTTPException(status_code=403, detail="无权访问此会话")

    if session.merged_findings is None:
        raise HTTPException(status_code=400, detail="请先完成照片上传和静态分析")

    # Run ROM tracking per movement
    velocity_analyzer = VelocityAnalyzer()
    all_velocity_findings = []
    all_rom_ratios = {}

    for mov_idx_str, frames_list in data.movement_data.items():
        mov_idx = int(mov_idx_str)
        frames = frames_list  # List[List[List[float]]] — per-frame keypoints

        if not frames:
            continue

        tracker = ROMTracker()
        for frame_kps in frames:
            kp_array = np.array(frame_kps, dtype=np.float32)
            tracker.feed_keypoints(kp_array)

        # Get the verification movement config
        vm = next((v for v in session.verification_plan if v.movement_def.index == mov_idx), None)
        if vm is None:
            continue

        # Extract ROM for key tracking joints
        for key in vm.key_rom_track:
            rom = tracker.get_joint_rom(key, "bilateral", key)
            if rom and hasattr(rom, 'rom_deg') and rom.rom_deg > 0:
                # Find norm for this key
                from models.assessment.scoring import UnifiedScoringEngine
                engine = UnifiedScoringEngine()
                norm = engine.norms.get(key, {})
                norm_min = norm.get("min", 60)
                if norm_min > 0:
                    ratio = rom.rom_deg / norm_min
                    all_rom_ratios[key] = min(ratio, 1.5)

        # Run velocity analysis on paired joints
        if vm.velocity_pairs:
            vel_findings = velocity_analyzer.analyze_pairs(tracker, vm.velocity_pairs)
            all_velocity_findings.extend(vel_findings)

        # Store result
        joint_roms = []
        for key in vm.key_rom_track:
            rom = tracker.get_joint_rom(key, "bilateral", key)
            if rom:
                joint_roms.append(rom)

        result = MovementROMResult(
            movement_index=mov_idx,
            movement_name=vm.movement_def.name,
            joint_roms=joint_roms,
            duration_seconds=len(frames) / 30.0,
            total_frames=len(frames),
        )
        if mov_idx not in session.verification_results:
            session.verification_results[mov_idx] = []
        session.verification_results[mov_idx].append(result)

    session.velocity_findings = all_velocity_findings
    session.rom_ratios = all_rom_ratios

    # Run fusion
    fusion_engine = FusionEngine()

    # Build list of StaticFinding-compatible objects from session
    static_findings = None
    if session.merged_findings:
        static_findings = session.merged_findings.findings

    if static_findings:
        fusion_result = fusion_engine.fuse(
            static_findings=static_findings,
            rom_ratios=all_rom_ratios,
            velocity_findings=all_velocity_findings,
        )
        session.fusion_result = fusion_result
        session.status = "fused"

        # Persist to DB
        from backend.database import models as db_models
        import json as json_mod

        # Compute 5-dimension scores from validated findings
        scores = _compute_dimension_scores(fusion_result)
        overall = fusion_result.fused_overall_score

        if overall >= 70:
            risk = "low"
        elif overall >= 40:
            risk = "medium"
        else:
            risk = "high"

        record = db_models.AssessmentRecord(
            user_id=user.id,
            balance_score=scores.get("balance", 0),
            flexibility_score=scores.get("flexibility", 0),
            upper_limb_score=scores.get("upper_limb", 0),
            core_score=scores.get("core", 0),
            symmetry_score=scores.get("symmetry", 0),
            overall_score=overall,
            risk_level=risk,
            assessment_type="multi_view",
            session_id=session_id,
            posture_data=json_mod.dumps({
                "problems": [
                    {"flag": v.problem_flag, "name": v.problem_name,
                     "severity": v.adjusted_severity, "verdict": v.verdict}
                    for v in fusion_result.validations
                ],
                "flags": session.merged_findings.flags if session.merged_findings else [],
            }, ensure_ascii=False),
            movement_data=json_mod.dumps({
                "asymmetry_findings": [
                    {"joint": f.joint, "diff_pct": f.max_velocity_diff_pct,
                     "severity": f.severity, "duration_frames": f.duration_frames}
                    for f in all_velocity_findings
                ],
            }, ensure_ascii=False),
            rom_data=json_mod.dumps(all_rom_ratios, ensure_ascii=False),
            fusion_data=json_mod.dumps({
                "validations": [
                    {"flag": v.problem_flag, "verdict": v.verdict,
                     "final_confidence": v.final_confidence,
                     "static_confidence": v.static_confidence,
                     "rom_score": v.rom_score, "velocity_score": v.velocity_score}
                    for v in fusion_result.validations
                ],
                "confirmed": fusion_result.confirmed_count,
                "rejected": fusion_result.rejected_count,
                "adjusted": fusion_result.adjusted_count,
            }, ensure_ascii=False),
            report_data=json_mod.dumps({
                "chart_data": {
                    "dimensions": [
                        {"dimension": d, "label": l, "score": scores.get(d, 0)}
                        for d, l in [("balance","平衡"), ("flexibility","灵活性"),
                                     ("upper_limb","上肢"), ("core","核心"), ("symmetry","对称性")]
                    ],
                },
            }, ensure_ascii=False),
        )

        db.add(record)
        db.commit()
        db.refresh(record)
        session.record_id = record.id

        return FusionReportResponse(
            session_id=session_id,
            record_id=record.id,
            validations=[
                FindingValidationSchema(
                    problem_flag=v.problem_flag,
                    problem_name=v.problem_name,
                    static_severity=v.static_severity,
                    static_confidence=v.static_confidence,
                    rom_score=v.rom_score,
                    velocity_score=v.velocity_score,
                    final_confidence=v.final_confidence,
                    verdict=v.verdict,
                    adjusted_severity=v.adjusted_severity,
                    explanation=v.explanation,
                    velocity_findings=[
                        {"joint": vf.joint, "severity": vf.severity,
                         "max_diff_pct": vf.max_velocity_diff_pct,
                         "duration_frames": vf.duration_frames}
                        for vf in v.velocity_findings
                    ],
                )
                for v in fusion_result.validations
            ],
            fused_overall_score=fusion_result.fused_overall_score,
            confirmed_count=fusion_result.confirmed_count,
            rejected_count=fusion_result.rejected_count,
            adjusted_count=fusion_result.adjusted_count,
            unverified_count=fusion_result.unverified_count,
        )
    else:
        raise HTTPException(status_code=500, detail="Fusion failed: no static findings available")


def _compute_dimension_scores(fusion_result) -> dict:
    """
    Compute 5-dimension scores based on validated (confirmed + adjusted) findings.
    Rejected findings are excluded. This gives a cleaner picture based on verified issues.
    """
    from models.assessment.fusion_engine import FusionEngine

    severity_score = FusionEngine.SEVERITY_SCORE

    # Start from 100, subtract based on validated findings
    dimension_penalties = {
        "balance": 0,
        "flexibility": 0,
        "upper_limb": 0,
        "core": 0,
        "symmetry": 0,
    }

    # Map flags to dimensions
    flag_dimension = {
        "shoulder_imbalance": "symmetry",
        "pelvic_lateral_tilt": "symmetry",
        "head_forward_posture": "upper_limb",
        "knee_hyperextension": "flexibility",
        "pelvic_anterior_tilt": "core",
        "pelvic_posterior_tilt": "core",
        "possible_scoliosis": "symmetry",
    }

    for v in fusion_result.validations:
        if v.verdict == "rejected":
            continue  # Excluded from scoring
        dim = flag_dimension.get(v.problem_flag)
        if dim is None:
            continue
        # Penalty based on adjusted severity
        sev = v.adjusted_severity
        penalty_map = {"severe": 30, "moderate": 20, "mild": 10, "normal": 0}
        dimension_penalties[dim] += penalty_map.get(sev, 0)

    scores = {}
    for dim, penalty in dimension_penalties.items():
        scores[dim] = max(0, 100 - penalty)

    return scores
