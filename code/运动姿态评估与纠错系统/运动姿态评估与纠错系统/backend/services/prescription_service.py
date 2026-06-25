from sqlalchemy.orm import Session
from fastapi import HTTPException
from backend.database import models
from backend.schemas.business import PrescriptionResponse, PrescriptionItemResponse
from models.prescription.recommendation_engine import PrescriptionEngine, Phase as RxPhase
from typing import List, Dict, Optional

class PrescriptionService:
    def __init__(self, db: Session):
        self.db = db

    def generate_from_fms(self, user_id: int, fms_record_id: int) -> PrescriptionResponse:
        fms_record = self.db.query(models.FMSRecord).filter(
            models.FMSRecord.id == fms_record_id, models.FMSRecord.user_id == user_id
        ).first()
        if not fms_record:
            raise HTTPException(status_code=404, detail='FMS record not found')

        tags = self._build_tags(fms_record)
        cycle = self.db.query(models.UserCycleConfig).filter(
            models.UserCycleConfig.user_id == user_id
        ).first()
        cycle_phase = None
        if cycle:
            cycle_phase = 'follicular'

        rx_data = PrescriptionEngine.generate(tags, difficulty=1, cycle_phase=cycle_phase)
        rx = models.Prescription(
            user_id=user_id, fms_record_id=fms_record_id,
            phase=1, status='active', difficulty=1
        )
        self.db.add(rx)
        self.db.flush()
        for item_data in rx_data['items']:
            action = self.db.query(models.ActionLibrary).filter(
                models.ActionLibrary.name == item_data['name']
            ).first()
            if not action:
                action = models.ActionLibrary(name=item_data['name'], category='general', difficulty=item_data['difficulty'])
                self.db.add(action)
                self.db.flush()
            rx_item = models.PrescriptionItem(
                prescription_id=rx.id, action_id=action.id,
                phase=item_data['phase'], sets=item_data['sets'],
                reps=item_data['reps'], duration=item_data.get('duration', 0),
                order_index=item_data.get('order_index', 0)
            )
            self.db.add(rx_item)
        self.db.commit()
        self.db.refresh(rx)
        return self._to_response(rx)

    def get_user_prescriptions(self, user_id: int) -> List[PrescriptionResponse]:
        rxs = self.db.query(models.Prescription).filter(
            models.Prescription.user_id == user_id
        ).order_by(models.Prescription.created_at.desc()).all()
        return [self._to_response(rx) for rx in rxs]

    def get_prescription(self, rx_id: int, user_id: int) -> PrescriptionResponse:
        rx = self.db.query(models.Prescription).filter(
            models.Prescription.id == rx_id, models.Prescription.user_id == user_id
        ).first()
        if not rx:
            raise HTTPException(status_code=404, detail='Prescription not found')
        return self._to_response(rx)

    def _to_response(self, rx: models.Prescription) -> PrescriptionResponse:
        items = []
        for item in rx.items:
            action = self.db.query(models.ActionLibrary).filter(models.ActionLibrary.id == item.action_id).first()
            items.append(PrescriptionItemResponse(
                id=item.id, action_name=action.name if action else '',
                phase=item.phase.value if hasattr(item.phase, 'value') else str(item.phase),
                sets=item.sets or 0, reps=item.reps or 0, duration=item.duration or 0,
                order_index=item.order_index or 0, difficulty=action.difficulty if action else 1,
                description=action.description if action else ''
            ))
        return PrescriptionResponse(
            id=rx.id, user_id=rx.user_id, fms_record_id=rx.fms_record_id,
            phase=rx.phase or 1, status=rx.status.value if hasattr(rx.status, 'value') else str(rx.status),
            difficulty=rx.difficulty or 1, created_at=rx.created_at, unlocked_at=rx.unlocked_at,
            items=items
        )

    def _build_tags(self, fms_record) -> List[Dict]:
        tags = []
        if fms_record.balance_score is not None and fms_record.balance_score < 60:
            tags.append({'name': 'balance_weak', 'dimension': 'balance'})
        if fms_record.flexibility_score is not None and fms_record.flexibility_score < 60:
            tags.append({'name': 'flexibility_weak', 'dimension': 'flexibility'})
        if fms_record.upper_limb_score is not None and fms_record.upper_limb_score < 60:
            tags.append({'name': 'upper_limb_weak', 'dimension': 'upper_limb'})
        if fms_record.core_score is not None and fms_record.core_score < 60:
            tags.append({'name': 'core_weak', 'dimension': 'core'})
        if fms_record.symmetry_score is not None and fms_record.symmetry_score < 60:
            tags.append({'name': 'symmetry_weak', 'dimension': 'symmetry'})
        return tags
