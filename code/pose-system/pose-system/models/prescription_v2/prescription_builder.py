"""
本地规则处方构建器。

当 DeepSeek 不可用时，使用纯规则引擎生成训练处方。
结合体态评估结果（问题类型）和 FMS 分数（能力水平），
从标准动作库中选取合适动作并计算训练量。
"""
from typing import Dict, List, Optional, Any
from dataclasses import dataclass, field
from datetime import datetime

from .action_library import StandardActionLibrary, Action, get_action_library
from .eligibility_checker import EligibilityChecker, EligibilityResult
from .volume_calculator import VolumeCalculator, VolumeResult


# 问题严重程度权重（用于动作匹配排序）
SEVERITY_WEIGHT = {
    "severe": 1.0,
    "moderate": 0.7,
    "mild": 0.4,
}


@dataclass
class PrescriptionPlanItem:
    """处方中的单个训练项。"""
    action_id: str
    action_name: str
    family_name: str
    category: str
    phase: str  # warmup / main / cooldown
    sets: int
    reps: int
    duration_seconds: int
    order_index: int
    difficulty: int
    intensity: str
    notes: str = ""
    steps: List[str] = field(default_factory=list)
    cues: List[str] = field(default_factory=list)
    display_type: str = "image"
    display_url: str = ""


@dataclass
class PrescriptionPlan:
    """完整训练处方计划。"""
    plan_name: str
    overall_strategy: str
    generation_method: str  # "local" | "deepseek"
    assessment_record_id: Optional[int] = None
    fms_record_id: Optional[int] = None
    user_id: Optional[int] = None
    detected_problems: List[Dict] = field(default_factory=list)
    fms_summary: Dict = field(default_factory=dict)
    phases: Dict[str, List[PrescriptionPlanItem]] = field(default_factory=dict)
    total_volume: Dict[str, int] = field(default_factory=dict)
    created_at: str = ""

    def __post_init__(self):
        if not self.created_at:
            self.created_at = datetime.utcnow().isoformat()


class PrescriptionBuilder:
    """本地规则处方构建器。

    流程：
    1. 从体态评估提取问题列表 + 严重程度
    2. 计算每个动作的 problem_match_score
    3. 用 FMS 筛选可执行动作（排除 unsafe）
    4. 按阶段选取动作（warmup → main → cooldown）
    5. 用 VolumeCalculator 计算每组动作的训练量
    6. 组装并返回 PrescriptionPlan

    使用示例：
        builder = PrescriptionBuilder()
        plan = builder.build(
            assessment_record=record,
            fms_record=fms_record,
            user_level=1,
        )
    """

    # 各阶段动作数量上限
    PHASE_LIMITS = {
        "warmup": 5,
        "main": 6,
        "cooldown": 4,
    }

    # 各阶段允许的 phase 标签
    PHASE_ALLOWED = {
        "warmup": ["warmup"],
        "main": ["main"],
        "cooldown": ["cooldown"],
    }

    # 各阶段允许的强度
    PHASE_INTENSITY = {
        "warmup": ["LOW", "MEDIUM"],
        "main": ["MEDIUM", "HIGH"],
        "cooldown": ["LOW"],
    }

    def __init__(
        self,
        library: StandardActionLibrary = None,
        checker: EligibilityChecker = None,
        calculator: VolumeCalculator = None,
    ):
        self.library = library or get_action_library()
        self.checker = checker or EligibilityChecker()
        self.calculator = calculator or VolumeCalculator()

    # ── 问题提取 ────────────────────────

    def _extract_problems(
        self,
        assessment_record
    ) -> List[Dict[str, Any]]:
        """从 AssessmentRecord 提取问题列表及严重程度。"""
        problems = []
        # 从 posture_data JSON 提取
        posture = getattr(assessment_record, "posture_data", None)
        if isinstance(posture, str):
            import json
            try:
                posture = json.loads(posture)
            except (json.JSONDecodeError, TypeError):
                posture = {}

        if isinstance(posture, dict):
            flags = posture.get("flags", [])
            measurements = posture.get("measurements", {})
            for flag in flags:
                severity = self._determine_severity(flag, measurements)
                if flag != "possible_scoliosis":  # 脊柱侧弯不生成训练
                    problems.append({
                        "flag": flag,
                        "severity": severity,
                        "weight": SEVERITY_WEIGHT.get(severity, 0.5),
                    })

        return problems

    def _determine_severity(self, flag: str, measurements: Dict) -> str:
        """根据测量值推断严重程度。"""
        # 从 thresholds.json 的逻辑推断
        thresholds = {
            "head_forward_posture": (15, 20, 30),
            "shoulder_imbalance": (10, 20, 35),
            "pelvic_lateral_tilt": (10, 20, 35),
            "possible_scoliosis": (15, 25, 40),
            "knee_hyperextension": (-5, -10, -15),
            "pelvic_anterior_tilt": (20, 35, 50),
            "pelvic_posterior_tilt": (-20, -35, -50),
        }
        thresh = thresholds.get(flag)
        if not thresh:
            return "mild"

        # 获取测量值
        metric_map = {
            "head_forward_posture": "head_forward_deg",
            "shoulder_imbalance": "shoulder_height_diff_px",
            "pelvic_lateral_tilt": "hip_height_diff_px",
            "possible_scoliosis": "spine_lateral_deviation_px",
            "knee_hyperextension": "knee_hyperextension_deg",
            "pelvic_anterior_tilt": "pelvic_forward_offset_px",
            "pelvic_posterior_tilt": "pelvic_forward_offset_px",
        }
        metric = metric_map.get(flag, "")
        value = abs(measurements.get(metric, 0))

        severe = abs(thresh[2])
        moderate = abs(thresh[1])

        if value >= severe:
            return "severe"
        elif value >= moderate:
            return "moderate"
        return "mild"

    # ── FMS 摘要 ────────────────────────

    def _build_fms_summary(self, fms_record) -> Dict:
        """构建 FMS 摘要。"""
        dims = ["balance", "flexibility", "upper_limb", "core", "symmetry"]
        scores = {}
        weak_dims = []
        for dim in dims:
            score = getattr(fms_record, f"{dim}_score", None)
            scores[dim] = score
            if score is not None and score < 60:
                weak_dims.append(dim)

        return {
            "overall_score": getattr(fms_record, "overall_score", None),
            "risk_level": getattr(fms_record, "risk_level", "unknown"),
            "dimensions": scores,
            "weak_dimensions": weak_dims,
            "is_complete": all(s is not None for s in scores.values()),
        }

    # ── 动作选取 ────────────────────────

    def _score_actions(
        self,
        problems: List[Dict],
    ) -> List[tuple]:
        """根据体态问题对所有动作打分排序。

        Returns:
            [(action, score), ...] 按分数降序
        """
        problem_ids = [p["flag"] for p in problems]
        severity_map = {p["flag"]: p.get("weight", 0.5) for p in problems}

        scored = []
        for action in self.library.get_all():
            score = sum(
                action.problem_mapping.get(pid, 0.0) * severity_map.get(pid, 0.5)
                for pid in problem_ids
            )
            if score > 0:
                scored.append((action, score))
        scored.sort(key=lambda x: x[1], reverse=True)
        return scored

    # ── 组装处方 ────────────────────────

    def build(
        self,
        assessment_record,
        fms_record,
        user_level: int = 1,
        use_equipment: bool = False,
    ) -> PrescriptionPlan:
        """构建训练处方。

        Args:
            assessment_record: AssessmentRecord ORM 对象
            fms_record: FMSRecord ORM 对象
            user_level: 用户训练水平 1-5
            use_equipment: 是否允许器械动作

        Returns:
            PrescriptionPlan
        """
        # 1. 提取问题
        problems = self._extract_problems(assessment_record)
        problem_ids = [p["flag"] for p in problems]

        # 2. FMS 摘要
        fms_summary = self._build_fms_summary(fms_record)
        fms_scores = {
            "balance_score": getattr(fms_record, "balance_score", None),
            "flexibility_score": getattr(fms_record, "flexibility_score", None),
            "core_score": getattr(fms_record, "core_score", None),
            "upper_limb_score": getattr(fms_record, "upper_limb_score", None),
            "symmetry_score": getattr(fms_record, "symmetry_score", None),
        }

        # 3. 动作打分
        scored_actions = self._score_actions(problems)

        # 4. 筛选：排除 unsafe 动作
        eligible_actions = []
        for action, score in scored_actions:
            result = self.checker.check(action, fms_scores)
            if result.eligible:
                eligible_actions.append((action, score, result))
            else:
                # 尝试推荐退阶动作
                if action.is_regression_of:
                    reg_action = self.library.get_by_id(action.is_regression_of)
                    if reg_action:
                        reg_result = self.checker.check(reg_action, fms_scores)
                        if reg_result.eligible:
                            eligible_actions.append(
                                (reg_action, score * 0.8, reg_result)
                            )

        # 去重（同一个 family 的 action 按 ID 去重）
        seen = set()
        deduped = []
        for action, score, result in eligible_actions:
            if action.id not in seen:
                seen.add(action.id)
                deduped.append((action, score, result))

        # 5. 按阶段选取 + 去重（同肌群不超 2 个）
        body_part_count: Dict[str, int] = {}
        phases = {
            "warmup": [],
            "main": [],
            "cooldown": [],
        }

        for action, score, result in deduped:
            for phase_name in ["warmup", "main", "cooldown"]:
                if self._can_place_in_phase(action, phase_name, phases[phase_name],
                                              body_part_count):
                    vol = self.calculator.calculate(action, fms_scores, user_level)
                    item = PrescriptionPlanItem(
                        action_id=action.id,
                        action_name=action.name,
                        family_name=action.family_name,
                        category=action.category,
                        phase=phase_name,
                        sets=vol.sets,
                        reps=vol.reps,
                        duration_seconds=vol.duration_seconds,
                        order_index=len(phases[phase_name]),
                        difficulty=action.difficulty,
                        intensity=action.intensity,
                        notes=vol.notes,
                        steps=action.steps,
                        cues=action.cues,
                        display_type=action.display_type,
                        display_url=action.display_url,
                    )
                    phases[phase_name].append(item)
                    self._update_body_part_count(body_part_count, action)
                    break  # 每个动作只放一个阶段

        # 6. 确保覆盖率：每个问题至少 1 个动作
        covered = set()
        for phase_items in phases.values():
            for item in phase_items:
                action = self.library.get_by_id(item.action_id)
                if action:
                    for pid in problem_ids:
                        if action.problem_mapping.get(pid, 0) > 0.2:
                            covered.add(pid)

        # 对未覆盖的问题，强制添加最高相关分的动作
        uncovered = set(problem_ids) - covered
        for pid in uncovered:
            for action, score, result in deduped:
                if action.problem_mapping.get(pid, 0) > 0.3:
                    vol = self.calculator.calculate(action, fms_scores, user_level)
                    item = PrescriptionPlanItem(
                        action_id=action.id,
                        action_name=action.name,
                        family_name=action.family_name,
                        category=action.category,
                        phase="main",
                        sets=vol.sets,
                        reps=vol.reps,
                        duration_seconds=vol.duration_seconds,
                        order_index=len(phases["main"]),
                        difficulty=action.difficulty,
                        intensity=action.intensity,
                        notes="（自动补充覆盖）" + vol.notes,
                        steps=action.steps,
                        cues=action.cues,
                        display_type=action.display_type,
                        display_url=action.display_url,
                    )
                    phases["main"].append(item)
                    break

        # 7. 计算总训练量
        all_items = []
        for phase_items in phases.values():
            all_items.extend(phase_items)

        total_sets = sum(item.sets for item in all_items)
        total_reps = sum(item.sets * item.reps for item in all_items)
        total_dur = sum(item.sets * item.duration_seconds for item in all_items)

        # 8. 生成策略说明
        strategy = self._build_strategy(problems, fms_summary, len(all_items))

        # 9. 生成计划名
        plan_name = self._build_plan_name(problems)

        return PrescriptionPlan(
            plan_name=plan_name,
            overall_strategy=strategy,
            generation_method="local",
            detected_problems=problems,
            fms_summary=fms_summary,
            phases=phases,
            total_volume={
                "total_actions": len(all_items),
                "total_sets": total_sets,
                "total_reps": total_reps,
                "total_duration_minutes": round(total_dur / 60, 1),
            },
        )

    def _can_place_in_phase(
        self,
        action: Action,
        phase_name: str,
        current_items: List[PrescriptionPlanItem],
        body_part_count: Dict[str, int],
    ) -> bool:
        """判断动作能否放入指定阶段。"""
        # 数量限制
        if len(current_items) >= self.PHASE_LIMITS.get(phase_name, 4):
            return False

        # 阶段匹配
        allowed = self.PHASE_ALLOWED.get(phase_name, [])
        if not any(p in action.phases for p in allowed):
            return False

        # 强度匹配
        allowed_intensity = self.PHASE_INTENSITY.get(phase_name, [])
        if action.intensity not in allowed_intensity:
            return False

        # 同肌群限制（main 阶段每个肌群最多 2 个动作）
        if phase_name == "main":
            for part in action.target_body_parts:
                if body_part_count.get(part, 0) >= 2:
                    return False

        return True

    def _update_body_part_count(
        self,
        body_part_count: Dict[str, int],
        action: Action,
    ):
        """更新肌群计数。"""
        for part in action.target_body_parts:
            body_part_count[part] = body_part_count.get(part, 0) + 1

    def _build_strategy(
        self,
        problems: List[Dict],
        fms_summary: Dict,
        total_actions: int,
    ) -> str:
        """生成整体训练策略说明。"""
        parts = []

        prob_names = []
        for p in problems:
            name_map = {
                "head_forward_posture": "头前倾",
                "shoulder_imbalance": "肩膀不对称",
                "pelvic_lateral_tilt": "骨盆侧倾",
                "knee_hyperextension": "膝关节超伸",
                "pelvic_anterior_tilt": "骨盆前倾",
                "pelvic_posterior_tilt": "骨盆后倾",
            }
            prob_names.append(name_map.get(p["flag"], p["flag"]))

        if prob_names:
            parts.append(f"针对{', '.join(prob_names)}问题，制定本训练计划。")

        overall = fms_summary.get("overall_score")
        if overall is not None:
            if overall < 40:
                parts.append("FMS 综合评分偏低，以低强度退阶动作为主，优先建立基础运动模式。")
            elif overall < 60:
                parts.append("FMS 综合评分中等，适度控制训练强度，强调动作质量。")
            else:
                parts.append("FMS 表现良好，可适当增加训练量，聚焦体态纠正。")

        weak = fms_summary.get("weak_dimensions", [])
        if weak:
            dim_names = {
                "balance": "平衡",
                "flexibility": "柔韧",
                "upper_limb": "上肢",
                "core": "核心",
                "symmetry": "对称",
            }
            weak_cn = [dim_names.get(d, d) for d in weak]
            parts.append(f"弱项维度: {', '.join(weak_cn)}，相应动作已降低训练量。")

        parts.append(f"本计划共 {total_actions} 个动作，热身→主训练→整理，循序渐进。")
        return "".join(parts)

    def _build_plan_name(self, problems: List[Dict]) -> str:
        """生成计划名称。"""
        if not problems:
            return "基础体态维持训练"
        name_map = {
            "head_forward_posture": "头前倾纠正",
            "shoulder_imbalance": "肩对称调整",
            "pelvic_lateral_tilt": "骨盆侧倾纠正",
            "knee_hyperextension": "膝关节稳定",
            "pelvic_anterior_tilt": "骨盆前倾纠正",
            "pelvic_posterior_tilt": "骨盆后倾纠正",
        }
        main = problems[0]["flag"]
        prefix = name_map.get(main, "体态纠正")
        return f"{prefix}训练计划"
