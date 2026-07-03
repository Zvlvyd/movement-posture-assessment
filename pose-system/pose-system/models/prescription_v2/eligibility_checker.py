"""
FMS 能力 → 动作可行性判断器。

根据 FMS 各维度分数，判断用户是否能安全执行指定动作。
纯函数设计，无外部依赖，易于单元测试。
"""
from typing import Dict, Optional, List, Tuple
from dataclasses import dataclass, field


# FMS 维度 → 中文标签
DIMENSION_LABELS = {
    "balance_score": "平衡能力",
    "flexibility_score": "柔韧性",
    "core_score": "核心稳定性",
    "upper_limb_score": "上肢能力",
    "symmetry_score": "对称性",
}

# 维度重要性权重（用于综合风险判断）
# core 和 balance 不达标比 upper_limb 更危险
DIMENSION_SEVERITY = {
    "balance_score": 1.2,
    "flexibility_score": 0.7,
    "core_score": 1.3,
    "upper_limb_score": 0.8,
    "symmetry_score": 1.0,
}


@dataclass
class EligibilityResult:
    """动作可行性判断结果。"""
    eligible: bool
    risk_level: str  # "safe" | "caution" | "unsafe"
    failing_dimensions: List[str] = field(default_factory=list)
    reasons: List[str] = field(default_factory=list)
    severity_score: float = 0.0  # 不达标的加权严重程度分


class EligibilityChecker:
    """根据 FMS 分数判断用户能否安全执行指定动作。

    判断逻辑：
    1. 逐维度比较用户 FMS 分数与动作禁忌阈值
    2. 所有维度达标 → safe
    3. 1-2 个维度不达标（非核心维度）→ caution
    4. 3+ 个维度不达标，或核心维度(core/balance)严重不达标 → unsafe
    5. 未测试维度（None）→ 跳过，不参与判断

    使用示例：
        checker = EligibilityChecker()
        result = checker.check(action, {"balance_score": 65, "core_score": 40, ...})
        if result.eligible:
            print(f"可执行，风险等级: {result.risk_level}")
    """

    # 核心维度：不达标时危险系数更高
    CRITICAL_DIMENSIONS = {"balance_score", "core_score"}

    # 单维度严重不达标阈值（低于此值即使只此一项也为 unsafe）
    SEVERE_DEFICIT_RATIO = 0.5  # 用户分数 < 阈值*0.5 即为严重不达标

    def check(
        self,
        action,
        fms_scores: Dict[str, Optional[float]]
    ) -> EligibilityResult:
        """检查用户是否能安全执行指定动作。

        Args:
            action: Action 数据类（来自 StandardActionLibrary）
            fms_scores: FMS 各维度分数，如 {'balance_score': 65, 'flexibility_score': 50, ...}
                        分数为 None 表示该维度未测试

        Returns:
            EligibilityResult 包含可行性和风险等级
        """
        contraindications = action.contraindications
        if not contraindications:
            return EligibilityResult(
                eligible=True,
                risk_level="safe",
                reasons=["该动作无 FMS 限制要求"],
            )

        failing = []
        reasons = []
        severity_score = 0.0
        has_severe_deficit = False

        for dim_key, min_score in contraindications.items():
            # dim_key 格式: min_balance_score → 转换为 balance_score
            score_key = dim_key.replace("min_", "")
            user_score = fms_scores.get(score_key)

            # 未测试的维度，跳过
            if user_score is None:
                continue

            # 分数不达标
            if user_score < min_score:
                deficit_ratio = user_score / max(min_score, 1)
                failing.append(score_key)
                label = DIMENSION_LABELS.get(score_key, score_key)
                reasons.append(
                    f"{label}: {user_score:.0f}分 < 要求{min_score:.0f}分"
                )
                severity_score += max(0, 1.0 - deficit_ratio) * DIMENSION_SEVERITY.get(
                    score_key, 1.0
                )

                # 检查是否严重不达标
                if deficit_ratio < self.SEVERE_DEFICIT_RATIO:
                    has_severe_deficit = True

        # ── 判断风险等级 ──────────────────────────
        if len(failing) == 0:
            return EligibilityResult(
                eligible=True,
                risk_level="safe",
            )

        # 核心维度严重不达标 → unsafe
        critical_failing = [d for d in failing if d in self.CRITICAL_DIMENSIONS]
        if has_severe_deficit and critical_failing:
            return EligibilityResult(
                eligible=False,
                risk_level="unsafe",
                failing_dimensions=failing,
                reasons=reasons + ["核心维度严重不达标，不建议执行此动作"],
                severity_score=severity_score,
            )

        # 3+ 维度不达标 → unsafe
        if len(failing) >= 3:
            return EligibilityResult(
                eligible=False,
                risk_level="unsafe",
                failing_dimensions=failing,
                reasons=reasons + [f"{len(failing)}个维度不达标，不建议执行此动作"],
                severity_score=severity_score,
            )

        # 1-2 个维度不达标（非严重）→ caution
        return EligibilityResult(
            eligible=True,
            risk_level="caution",
            failing_dimensions=failing,
            reasons=reasons + ["建议降低强度或选择退阶动作"],
            severity_score=severity_score,
        )

    def filter_actions(
        self,
        actions: List,
        fms_scores: Dict[str, Optional[float]],
        include_caution: bool = True,
    ) -> Tuple[List, List, List]:
        """批量筛选动作，按风险等级分组。

        Args:
            actions: 动作列表
            fms_scores: FMS 分数
            include_caution: 是否包含 caution 级别的动作

        Returns:
            (safe_actions, caution_actions, unsafe_actions)
        """
        safe = []
        caution = []
        unsafe = []
        for action in actions:
            result = self.check(action, fms_scores)
            if result.risk_level == "safe":
                safe.append((action, result))
            elif result.risk_level == "caution":
                caution.append((action, result))
            else:
                unsafe.append((action, result))
        return safe, caution, unsafe

    def get_recommendation(
        self,
        action,
        fms_scores: Dict[str, Optional[float]],
    ) -> str:
        """获取针对一个动作的具体建议。

        Returns:
            中文建议字符串
        """
        result = self.check(action, fms_scores)
        if result.risk_level == "safe":
            return f"可以安全执行「{action.name}」"
        elif result.risk_level == "caution":
            reg = action.is_regression_of
            if reg:
                return f"「{action.name}」需谨慎（{'；'.join(result.reasons)}），建议退阶到更简单的变体"
            return f"「{action.name}」需谨慎（{'；'.join(result.reasons)}），建议降低组数或次数"
        else:
            return f"「{action.name}」不建议执行（{'；'.join(result.reasons)}），请选择退阶动作"
