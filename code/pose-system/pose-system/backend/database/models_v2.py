"""
处方生成模块 v2 数据库模型。

新增表：
- prescription_plan: 处方计划主表
- prescription_plan_item: 处方计划动作明细

这两张表独立于现有的 prescription/prescription_item 表，
不与现有管线冲突。
"""
from sqlalchemy import (
    Column, Integer, String, Float, DateTime, ForeignKey, Text, Boolean
)
from sqlalchemy.orm import relationship
from datetime import datetime
from backend.database.connection import Base


class PrescriptionPlan(Base):
    """处方计划 v2 主表。"""
    __tablename__ = "prescription_plan"

    id = Column(Integer, primary_key=True, autoincrement=True)
    user_id = Column(Integer, ForeignKey("user.id"), nullable=False, index=True)
    assessment_record_id = Column(
        Integer, ForeignKey("assessment_record.id"), nullable=True
    )
    fms_record_id = Column(
        Integer, ForeignKey("fms_record.id"), nullable=True
    )

    plan_name = Column(String(200), nullable=False, comment="计划名称（AI或本地生成）")
    overall_strategy = Column(Text, comment="整体训练策略说明")
    status = Column(String(20), default="draft", comment="draft/active/completed")
    generation_method = Column(
        String(20), default="local", comment="deepseek/local"
    )
    template_version = Column(String(20), comment="使用的模板版本号")

    # 存储完整的生成元数据（问题列表、FMS摘要等）
    plan_meta = Column(Text, comment="JSON: detected_problems, fms_summary, total_volume")

    # 存储 DeepSeek 原始响应（仅 deepseek 方法，用于审计和调试）
    raw_ai_response = Column(Text, comment="DeepSeek 原始响应 JSON（审计用）")

    created_at = Column(DateTime, default=datetime.utcnow)
    activated_at = Column(DateTime, nullable=True)
    completed_at = Column(DateTime, nullable=True)

    # 关系
    user = relationship("User", foreign_keys=[user_id])
    assessment_record = relationship(
        "AssessmentRecord", foreign_keys=[assessment_record_id]
    )
    fms_record = relationship("FMSRecord", foreign_keys=[fms_record_id])
    items = relationship(
        "PrescriptionPlanItem",
        back_populates="plan",
        cascade="all, delete-orphan",
        order_by="PrescriptionPlanItem.order_index",
    )

    def to_dict(self):
        return {
            "id": self.id,
            "user_id": self.user_id,
            "assessment_record_id": self.assessment_record_id,
            "fms_record_id": self.fms_record_id,
            "plan_name": self.plan_name,
            "overall_strategy": self.overall_strategy,
            "status": self.status,
            "generation_method": self.generation_method,
            "template_version": self.template_version,
            "created_at": self.created_at.isoformat() if self.created_at else None,
            "activated_at": self.activated_at.isoformat() if self.activated_at else None,
            "items": [item.to_dict() for item in self.items] if self.items else [],
        }


class PrescriptionPlanItem(Base):
    """处方计划动作明细表。"""
    __tablename__ = "prescription_plan_item"

    id = Column(Integer, primary_key=True, autoincrement=True)
    plan_id = Column(
        Integer, ForeignKey("prescription_plan.id"), nullable=False, index=True
    )

    action_id = Column(String(50), nullable=False, comment="对应 action_library.json 中的 id")
    action_name = Column(String(200), nullable=False, comment="动作名称（冗余存储）")
    family_name = Column(String(100), comment="动作家族名称")
    category = Column(String(50), comment="动作大类")

    phase = Column(String(20), nullable=False, comment="warmup/activation/main/cooldown")
    sets = Column(Integer, default=3)
    reps = Column(Integer, default=10)
    duration_seconds = Column(Integer, default=0)
    order_index = Column(Integer, default=0)

    difficulty = Column(Integer, default=1, comment="动作难度 1-5")
    intensity = Column(String(10), default="MEDIUM", comment="LOW/MEDIUM/HIGH")

    notes = Column(Text, comment="AI 或系统给出的训练备注")
    is_substitution = Column(Boolean, default=False, comment="是否为替代动作")

    created_at = Column(DateTime, default=datetime.utcnow)

    # 关系
    plan = relationship("PrescriptionPlan", back_populates="items")

    def to_dict(self):
        return {
            "id": self.id,
            "plan_id": self.plan_id,
            "action_id": self.action_id,
            "action_name": self.action_name,
            "family_name": self.family_name,
            "category": self.category,
            "phase": self.phase,
            "sets": self.sets,
            "reps": self.reps,
            "duration_seconds": self.duration_seconds,
            "order_index": self.order_index,
            "difficulty": self.difficulty,
            "intensity": self.intensity,
            "notes": self.notes,
            "is_substitution": self.is_substitution,
        }
