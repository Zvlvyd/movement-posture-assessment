"""
处方生成模块 v2 业务编排层。

负责：
1. 编排完整处方生成流程（数据加载 → 引擎选择 → 持久化）
2. 处方计划的 CRUD
3. 计划激活（含兼容桥接）
"""
import json
import logging
from typing import Optional, List
from sqlalchemy.orm import Session

from backend.database.models import (
    User, FMSRecord, AssessmentRecord,
    Prescription, PrescriptionItem, PrescriptionStatus, ActionPhase,
    ActionLibrary,
)
from backend.database.models_v2 import PrescriptionPlan, PrescriptionPlanItem

from models.prescription_v2 import (
    StandardActionLibrary, get_action_library,
    EligibilityChecker,
    VolumeCalculator,
    PrescriptionBuilder,
    TemplateEngine,
    DeepSeekPrescription,
    PrescriptionPlan as PlanData,
    PrescriptionPlanItem as PlanItemData,
)

logger = logging.getLogger(__name__)


class PrescriptionV2Service:
    """处方 v2 业务服务。"""

    def __init__(
        self,
        library: StandardActionLibrary = None,
        checker: EligibilityChecker = None,
        calculator: VolumeCalculator = None,
        builder: PrescriptionBuilder = None,
        engine: TemplateEngine = None,
        deepseek: DeepSeekPrescription = None,
    ):
        self.library = library or get_action_library()
        self.checker = checker or EligibilityChecker()
        self.calculator = calculator or VolumeCalculator()
        self.builder = builder or PrescriptionBuilder(
            self.library, self.checker, self.calculator
        )
        self.engine = engine or TemplateEngine()
        self.deepseek = deepseek or DeepSeekPrescription(
            self.library, self.engine, self.checker, self.calculator
        )

    # ── 生成处方 ────────────────────────

    async def generate(
        self,
        db: Session,
        user_id: int,
        assessment_record_id: int,
        fms_record_id: int,
        user_level: int = 1,
        force_local: bool = False,
        training_goal: str = 'comprehensive',
        training_duration: int = 30,
        training_frequency: int = 3,
    ) -> dict:
        """生成训练处方。

        Args:
            db: 数据库会话
            user_id: 用户 ID
            assessment_record_id: 体态评估记录 ID
            fms_record_id: FMS 记录 ID
            user_level: 训练水平
            force_local: 强制本地引擎
            training_goal: 训练目标
            training_duration: 单次时长（分钟）
            training_frequency: 每周频率

        Returns:
            {"success": bool, "plan": PlanResponse|None, "generation_method": str,
             "error_message": str, "fallback_used": bool}
        """
        # 1. 加载记录
        assessment = db.query(AssessmentRecord).filter(
            AssessmentRecord.id == assessment_record_id,
            AssessmentRecord.user_id == user_id,
        ).first()
        if not assessment:
            return {"success": False, "error_message": "体态评估记录不存在"}

        fms = db.query(FMSRecord).filter(
            FMSRecord.id == fms_record_id,
            FMSRecord.user_id == user_id,
        ).first()
        if not fms:
            return {"success": False, "error_message": "FMS 记录不存在"}

        # 查询被隐藏的动作名称
        from backend.database.models_v2 import PrescriptionPlan
        from backend.database.models import ActionLibrary
        hidden_rows = db.query(ActionLibrary).filter(
            ActionLibrary.is_visible == False
        ).all()
        hidden_names = {r.name for r in hidden_rows}

        # 2. 尝试 DeepSeek（如不强制本地）
        plan_data = None
        generation_method = "local"
        fallback_used = False
        error_msg = ""
        raw_response = None

        if not force_local and self._deepseek_available():
            try:
                result = await self.deepseek.generate(
                    assessment, fms, user_level, hidden_names,
                    training_goal=training_goal,
                    training_duration=training_duration,
                    training_frequency=training_frequency,
                )
                if result.success and result.plan:
                    plan_data = result.plan
                    generation_method = "deepseek"
                    raw_response = result.raw_response
                else:
                    logger.warning(f"DeepSeek 处方生成失败: {result.error_message}，回退本地引擎")
                    error_msg = result.error_message
                    fallback_used = True
            except Exception as e:
                logger.warning(f"DeepSeek 调用异常: {e}，回退本地引擎")
                error_msg = str(e)
                fallback_used = True

        # 3. 回退：本地引擎
        if plan_data is None:
            plan_data = self.builder.build(assessment, fms, user_level, hidden_names=hidden_names,
                training_goal=training_goal, training_duration=training_duration)
            generation_method = "local"
            if not error_msg:
                error_msg = ""

        # 3.5 注入训练配置（供前端展示）
        goal_labels = {'comprehensive': '综合提升', 'posture': '体态矫正', 'strength': '力量增强', 'flexibility': '柔韧恢复', 'fatloss': '减脂塑形'}
        level_labels = {1: '心血来潮', 2: '偶尔进行', 3: '渐入佳境', 4: '健身发烧友', 5: '肌肉掌控者'}
        if plan_data:
            plan_data.training_config = {
                "training_goal": goal_labels.get(training_goal, '综合提升'),
                "training_duration": training_duration,
                "training_frequency": training_frequency,
                "user_level": user_level,
                "user_level_label": level_labels.get(user_level, f'Lv.{user_level}'),
            }

        # 3.6 兜底调整：如果总时长低于目标的70%，按比例增加组数
        if plan_data and training_duration > 0:
            total_secs = sum(
                item.sets * item.duration_seconds
                for phase_items in (plan_data.phases or {}).values()
                for item in phase_items
            )
            total_min = total_secs / 60
            target_secs = training_duration * 60
            if total_secs < target_secs * 0.7:
                scale = min(2.0, target_secs / max(total_secs, 1))
                logger.info(f"[PrescriptionV2] Duration {total_min:.1f}min below {training_duration}min target, scaling sets by {scale:.1f}x")
                for phase_items in (plan_data.phases or {}).values():
                    for item in phase_items:
                        item.sets = max(1, round(item.sets * scale))
                        if item.reps > 0:
                            item.reps = max(5, round(item.reps * scale))

        # 4. 持久化
        db_plan = self._save_plan(
            db, user_id, assessment_record_id, fms_record_id,
            plan_data, generation_method,
            raw_response=raw_response,
        )

        # 5. 构建响应
        return {
            "success": True,
            "plan": self._plan_to_response(db_plan, plan_data),
            "generation_method": generation_method,
            "error_message": error_msg,
            "fallback_used": fallback_used,
        }

    # ── 计划 CRUD ────────────────────────

    def list_plans(self, db: Session, user_id: int) -> List[dict]:
        """列出用户的所有计划。"""
        plans = db.query(PrescriptionPlan).filter(
            PrescriptionPlan.user_id == user_id
        ).order_by(PrescriptionPlan.created_at.desc()).all()
        return [self._plan_to_response(p) for p in plans]

    def get_plan(self, db: Session, plan_id: int, user_id: int) -> Optional[dict]:
        """获取单个计划详情。"""
        plan = db.query(PrescriptionPlan).filter(
            PrescriptionPlan.id == plan_id,
            PrescriptionPlan.user_id == user_id,
        ).first()
        if not plan:
            return None
        return self._plan_to_response(plan)

    def activate_plan(
        self, db: Session, plan_id: int, user_id: int
    ) -> dict:
        """激活处方计划。

        同时创建一条兼容的旧 Prescription 记录，
        使现有 PrescriptionTrainingPage 可以直接使用。
        """
        plan = db.query(PrescriptionPlan).filter(
            PrescriptionPlan.id == plan_id,
            PrescriptionPlan.user_id == user_id,
        ).first()
        if not plan:
            return {"success": False, "message": "计划不存在"}

        if plan.status == "active":
            return {"success": False, "message": "计划已激活"}

        # 更新状态
        plan.status = "active"
        from datetime import datetime
        plan.activated_at = datetime.utcnow()

        # 创建桥接 Prescription（兼容旧训练页面）
        bridge_id = self._create_bridge_prescription(db, plan, user_id)

        db.commit()

        return {
            "success": True,
            "message": "计划已激活",
            "bridge_prescription_id": bridge_id,
        }

    # ── 动作库查询 ────────────────────────

    def delete_plan(self, db: Session, plan_id: int, user_id: int) -> bool:
        """删除训练计划，同时清理激活时产生的桥接处方记录和训练完成记录"""
        plan = db.query(PrescriptionPlan).filter(
            PrescriptionPlan.id == plan_id,
            PrescriptionPlan.user_id == user_id,
        ).first()
        if not plan:
            return False

        # 1. 删除训练完成记录（外键引用 plan_item）
        from backend.database.models_v2 import TrainingCompletion
        db.query(TrainingCompletion).filter(
            TrainingCompletion.plan_id == plan_id
        ).delete()

        # 2. 删除计划动作项
        db.query(PrescriptionPlanItem).filter(
            PrescriptionPlanItem.plan_id == plan_id
        ).delete()

        # 2.5 删除计划变更请求（外键引用 plan_id）
        from backend.database.models import PlanChangeRequest
        db.query(PlanChangeRequest).filter(
            PlanChangeRequest.plan_id == plan_id
        ).delete()

        # 3. 如果计划已激活，清理桥接的旧 Prescription 记录
        if plan.status == "active":
            bridge = db.query(Prescription).filter(
                Prescription.user_id == user_id,
                Prescription.fms_record_id == (plan.fms_record_id or 0),
                Prescription.assessment_record_id == plan.assessment_record_id,
                Prescription.phase == 1,
                Prescription.status == PrescriptionStatus.ACTIVE,
            ).order_by(Prescription.created_at.desc()).first()
            if bridge:
                db.query(PrescriptionItem).filter(
                    PrescriptionItem.prescription_id == bridge.id
                ).delete()
                db.delete(bridge)

        db.delete(plan)
        db.commit()
        return True

    def get_action_library(self, db: Session = None) -> dict:
        """获取完整动作库（供前端参考），排除隐藏动作。"""
        hidden_names = set()
        if db:
            from backend.database.models import ActionLibrary
            hidden_rows = db.query(ActionLibrary).filter(
                ActionLibrary.is_visible == False
            ).all()
            hidden_names = {r.name for r in hidden_rows}
        actions = []
        for a in self.library.get_all():
            if a.name in hidden_names:
                continue
            actions.append({
                "id": a.id,
                "family": a.family,
                "family_name": a.family_name,
                "name": a.name,
                "category": a.category,
                "subcategory": a.subcategory,
                "difficulty": a.difficulty,
                "intensity": a.intensity,
                "target_body_parts": a.target_body_parts,
                "phases": a.phases,
                "default_sets": a.default_sets,
                "default_reps": a.default_reps,
                "default_duration_seconds": a.default_duration_seconds,
                "description": a.description,
                "steps": a.steps,
                "cues": a.cues,
                "display_type": a.display_type,
                "display_url": a.display_url,
            })
        families = self.library.get_families()
        return {
            "actions": actions,
            "total": len(actions),
            "families": families,
        }

    # ── 内部方法 ────────────────────────

    def _deepseek_available(self) -> bool:
        """检查 DeepSeek 是否可用。"""
        from config.settings import settings
        force_local = getattr(settings, "PRESCRIPTION_V2_FORCE_LOCAL", False)
        if force_local:
            return False
        return bool(settings.DEEPSEEK_API_KEY)

    def _save_plan(
        self,
        db: Session,
        user_id: int,
        assessment_record_id: int,
        fms_record_id: int,
        plan_data: PlanData,
        generation_method: str,
        raw_response: Optional[str] = None,
    ) -> PrescriptionPlan:
        """保存处方计划到数据库。"""
        import json
        from dataclasses import asdict

        plan_meta = json.dumps({
            "detected_problems": plan_data.detected_problems,
            "fms_summary": plan_data.fms_summary,
            "total_volume": plan_data.total_volume,
            "skipped_items": [asdict(s) for s in (plan_data.skipped_items or [])],
            "training_config": plan_data.training_config,
        }, ensure_ascii=False)

        db_plan = PrescriptionPlan(
            user_id=user_id,
            assessment_record_id=assessment_record_id,
            fms_record_id=fms_record_id,
            plan_name=plan_data.plan_name,
            overall_strategy=plan_data.overall_strategy,
            status="draft",
            generation_method=generation_method,
            template_version="1.0",
            plan_meta=plan_meta,
            raw_ai_response=raw_response,
        )
        db.add(db_plan)
        db.flush()  # 获取 plan.id

        # 保存计划项
        for phase_name, items in plan_data.phases.items():
            for item in items:
                db_item = PrescriptionPlanItem(
                    plan_id=db_plan.id,
                    action_id=item.action_id,
                    action_name=item.action_name,
                    family_name=item.family_name,
                    category=item.category,
                    phase=phase_name,
                    sets=item.sets,
                    reps=item.reps,
                    duration_seconds=item.duration_seconds,
                    order_index=item.order_index,
                    difficulty=item.difficulty,
                    intensity=item.intensity,
                    notes=item.notes,
                    is_substitution=False,
                )
                db.add(db_item)

        db.commit()
        db.refresh(db_plan)
        return db_plan

    def _plan_to_response(
        self,
        db_plan: PrescriptionPlan,
        plan_data: PlanData = None,
    ) -> dict:
        """将 ORM 对象转换为响应 dict。"""
        items = []
        for item in db_plan.items:
            item_dict = item.to_dict()
            # 从动作库补充教学信息
            action = self.library.get_by_id(item.action_id)
            if action:
                item_dict["steps"] = action.steps
                item_dict["cues"] = action.cues
                item_dict["display_type"] = action.display_type
                item_dict["display_url"] = action.display_url
            else:
                item_dict["steps"] = []
                item_dict["cues"] = []
                item_dict["display_type"] = "image"
                item_dict["display_url"] = ""
            items.append(item_dict)

        meta = {}
        if db_plan.plan_meta:
            try:
                meta = json.loads(db_plan.plan_meta)
            except json.JSONDecodeError:
                pass

        return {
            "id": db_plan.id,
            "user_id": db_plan.user_id,
            "assessment_record_id": db_plan.assessment_record_id,
            "fms_record_id": db_plan.fms_record_id,
            "plan_name": db_plan.plan_name,
            "overall_strategy": db_plan.overall_strategy,
            "status": db_plan.status,
            "generation_method": db_plan.generation_method,
            "template_version": db_plan.template_version,
            "plan_meta": meta,
            "created_at": db_plan.created_at.isoformat() if db_plan.created_at else None,
            "activated_at": db_plan.activated_at.isoformat() if db_plan.activated_at else None,
            "completed_at": db_plan.completed_at.isoformat() if db_plan.completed_at else None,
            "items": items,
        }

    def _create_bridge_prescription(
        self,
        db: Session,
        plan: PrescriptionPlan,
        user_id: int,
    ) -> Optional[int]:
        """创建桥接到旧 Prescription 表的记录。

        使现有 PrescriptionTrainingPage 能直接使用 v2 处方。
        """
        try:
            bridge = Prescription(
                user_id=user_id,
                fms_record_id=plan.fms_record_id or 0,
                assessment_record_id=plan.assessment_record_id,
                phase=1,
                status=PrescriptionStatus.ACTIVE,
                difficulty=1,
            )
            db.add(bridge)
            db.flush()

            for item in plan.items:
                # 确保 action_library 中有对应记录
                action_lib = db.query(ActionLibrary).filter(
                    ActionLibrary.name == item.action_name
                ).first()
                if not action_lib:
                    action_lib = ActionLibrary(
                        name=item.action_name,
                        category=item.category or "general",
                        difficulty=item.difficulty,
                        target_body_parts="",
                        description=item.notes or "",
                    )
                    db.add(action_lib)
                    db.flush()

                bridge_item = PrescriptionItem(
                    prescription_id=bridge.id,
                    action_id=action_lib.id,
                    phase=ActionPhase(item.phase),
                    sets=item.sets,
                    reps=item.reps,
                    duration=item.duration_seconds,
                    order_index=item.order_index,
                )
                db.add(bridge_item)

            db.flush()
            return bridge.id
        except Exception as e:
            logger.warning(f"创建桥接 Prescription 失败: {e}")
            return None
