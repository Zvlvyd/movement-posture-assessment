from sqlalchemy.orm import Session
from fastapi import HTTPException
from typing import Optional, List
from backend.database import models
from models.fms.scoring import FMSScoringEngine
from models.fms.radar_report import RadarReport
from models.fms.problem_tagger import ProblemTagger
from backend.schemas.business import FMSSubmitRequest, FMSResultResponse

class FMSService:
    def __init__(self, db: Session):
        self.db = db
        self.engine = FMSScoringEngine()

    def process_screening(self, user_id: int, data: FMSSubmitRequest):
        scores = []
        if data.balance_duration is not None:
            scores.append(self.engine.score_balance(data.balance_duration))
        if data.flexibility_depth is not None:
            scores.append(self.engine.score_flexibility(data.flexibility_depth, data.flexibility_trunk or 0, data.flexibility_arm or 1.0))
        if data.upper_limb_distance is not None:
            scores.append(self.engine.score_upper_limb(data.upper_limb_distance))
        if data.core_duration is not None:
            scores.append(self.engine.score_core(data.core_duration))
        if data.symmetry_left is not None and data.symmetry_right is not None:
            scores.append(self.engine.score_symmetry(data.symmetry_left, data.symmetry_right))
        overall = self.engine.compute_overall(scores)
        risk_level = self.engine.get_risk_level(overall, scores)
        record = models.FMSRecord(user_id=user_id, balance_score=next((s.score for s in scores if s.dimension == "balance"), None), flexibility_score=next((s.score for s in scores if s.dimension == "flexibility"), None), upper_limb_score=next((s.score for s in scores if s.dimension == "upper_limb"), None), core_score=next((s.score for s in scores if s.dimension == "core"), None), symmetry_score=next((s.score for s in scores if s.dimension == "symmetry"), None), overall_score=overall, risk_level=risk_level)
        self.db.add(record); self.db.commit(); self.db.refresh(record)
        radar = RadarReport.generate(scores, overall, risk_level)
        tags = ProblemTagger.tag(scores)
        result = FMSResultResponse.model_validate(record)
        result.radar_data = radar; result.problem_tags = tags
        return result

    def get_user_records(self, user_id: int):
        return self.db.query(models.FMSRecord).filter(models.FMSRecord.user_id == user_id).order_by(models.FMSRecord.test_date.desc()).all()

    def get_record_detail(self, record_id: int, user_id: int):
        record = self.db.query(models.FMSRecord).filter(models.FMSRecord.id == record_id, models.FMSRecord.user_id == user_id).first()
        if not record: raise HTTPException(status_code=404, detail="Record not found")
        return FMSResultResponse.model_validate(record)

import json, math, time
from typing import Dict, List, Optional, Any
from fastapi import WebSocket
from sqlalchemy.orm import Session
from datetime import datetime
import numpy as np

from backend.database import models
from backend.services.fms_service import FMSService
from backend.schemas.business import FMSSubmitRequest
from models.fms.scoring import FMSScoringEngine
from models.angle_calculator import AngleCalculator

