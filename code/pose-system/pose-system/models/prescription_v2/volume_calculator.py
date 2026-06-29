"""
FMS 分数 → 训练量计算器。

根据 FMS 各维度分数和动作特性，计算个性化的训练量（组数、次数、时长）。
纯函数设计，无外部依赖。
"""
from typing import Dict, List, Optional, Tuple
from dataclasses import dataclass


# FMS 各维度对训练量调整的影响权重
# core 和 balance 对训练量影响最大（不稳定时所有动作都要降量）
VOLUME_DIMENSION_WEIGHTS = {
    "balance_score": 0.20,
    "flexibility_score": 0.15,
    "core_score": 0.30,
    "upper_limb_score": 0.15,
    "symmetry_score": 0.20,
}

# 分数区间 → 调整系数
# 分数越高系数越大（训练量可递增），分数越低越保守
SCORE_BRACKETS = [
    (80, 1.2),   # >= 80 分 → 120% 训练量
    (60, 1.0),   # >= 60 分 → 100% 训练量
    (40, 0.7),   # >= 40 分 → 70% 训练量
    (20, 0.5),   # >= 20 分 → 50% 训练量
    (0,  0.3),   # >= 0 分  → 30% 训练量（严重不足）
]

# 强度系数：高强度动作天然需要更少的量
INTENSITY_FACTORS = {
    "LOW": 1.2,
    "MEDIUM": 1.0,
    "HIGH": 0.7,
}

# 训练量上下限
LIMITS = {
    "sets": (1, 5),
    "reps": (5, 20),
    "duration_seconds": (10, 60),
}


@dataclass
class VolumeResult:
    """训练量计算结果。"""
    sets: int
    reps: int
    duration_seconds: int
    fms_multiplier: float       # FMS 综合调整系数
    intensity_factor: float      # 强度调整系数
    final_multiplier: float      # 最终综合系数
    notes: str = ""


class VolumeCalculator:
    """根据 FMS 分数计算个性化训练量。

    计算逻辑：
    1. 计算 FMS 各维度的加权调整系数（高分增量、低分降量）
    2. 乘以动作强度系数（高强度动作天然量少）
    3. 得到最终系数，应用到动作默认的 sets/reps/duration
    4. 结果限制在安全范围内

    使用示例：
        calc = VolumeCalculator()
        volume = calc.calculate(action, {"balance_score": 65, "core_score": 40, ...})
        print(f"建议: {volume.sets}组 x {volume.reps}次")
    """

    def __init__(
        self,
        brackets: list = None,
        weights: Dict[str, float] = None,
    ):
        """初始化计算器。

        Args:
            brackets: 自定义分数区间，格式 [(score, multiplier), ...]
            weights: 自定义维度权重
        """
        self.brackets = brackets or SCORE_BRACKETS
        self.weights = weights or VOLUME_DIMENSION_WEIGHTS

    def _score_to_multiplier(self, score: float) -> float:
        """单个维度分数 → 调整系数。"""
        for threshold, multiplier in self.brackets:
            if score >= threshold:
                return multiplier
        return 0.3  # 兜底

    def compute_fms_multiplier(
        self,
        fms_scores: Dict[str, Optional[float]]
    ) -> Tuple[float, Dict[str, float]]:
        """计算 FMS 综合调整系数。

        Args:
            fms_scores: FMS 各维度分数

        Returns:
            (综合系数, 各维度详细系数)
        """
        total_weight = 0.0
        weighted_sum = 0.0
        detail = {}

        for dim_key, weight in self.weights.items():
            score = fms_scores.get(dim_key)
            if score is None:
                # 未测试维度，使用中性系数
                detail[dim_key] = 1.0
                continue

            dim_mult = self._score_to_multiplier(score)
            detail[dim_key] = dim_mult
            weighted_sum += dim_mult * weight
            total_weight += weight

        if total_weight == 0:
            return 1.0, detail

        fms_multiplier = weighted_sum / total_weight
        # 限制在 0.3-1.5 之间
        fms_multiplier = max(0.3, min(1.5, fms_multiplier))
        return round(fms_multiplier, 2), detail

    def calculate(
        self,
        action,
        fms_scores: Dict[str, Optional[float]],
        user_level: int = 1,
    ) -> VolumeResult:
        """计算单个动作的个性化训练量。

        Args:
            action: Action 数据类
            fms_scores: FMS 各维度分数
            user_level: 用户训练水平 (1=入门, 2=初级, 3=中级, 4=高级, 5=精英)

        Returns:
            VolumeResult
        """
        # 1. FMS 综合调整系数
        fms_mult, detail = self.compute_fms_multiplier(fms_scores)

        # 2. 强度系数
        intensity = getattr(action, "intensity", "MEDIUM")
        intensity_factor = INTENSITY_FACTORS.get(intensity, 1.0)

        # 3. 最终系数
        final_mult = round(fms_mult * intensity_factor, 2)
        final_mult = max(0.3, min(1.5, final_mult))

        # 4. 应用到动作默认值
        raw_sets = action.default_sets * final_mult
        raw_reps = action.default_reps * final_mult
        raw_dur = action.default_duration_seconds * final_mult

        # 5. 限制在安全范围
        sets = max(LIMITS["sets"][0], min(LIMITS["sets"][1], round(raw_sets)))
        reps = max(LIMITS["reps"][0], min(LIMITS["reps"][1], round(raw_reps)))
        duration = max(LIMITS["duration_seconds"][0],
                       min(LIMITS["duration_seconds"][1], round(raw_dur)))

        # 6. 如果是拉伸/计时类动作，reps 可能为 0
        if action.default_reps == 0 and action.default_duration_seconds > 0:
            reps = 0
        elif action.default_duration_seconds == 0 and action.default_reps > 0:
            duration = 0

        # 7. 生成说明
        notes_parts = []
        if fms_mult < 0.7:
            notes_parts.append(f"FMS综合偏低({fms_mult:.0%})，已降低训练量")
        elif fms_mult > 1.1:
            notes_parts.append(f"FMS表现良好({fms_mult:.0%})，可适当增加训练量")
        if intensity_factor < 1.0:
            notes_parts.append("高强度动作已自动降量")
        if final_mult < 0.6:
            notes_parts.append("建议优先选择退阶动作建立基础")

        return VolumeResult(
            sets=sets,
            reps=reps,
            duration_seconds=duration,
            fms_multiplier=fms_mult,
            intensity_factor=intensity_factor,
            final_multiplier=final_mult,
            notes="；".join(notes_parts) if notes_parts else "标准训练量",
        )

    def calculate_batch(
        self,
        actions: list,
        fms_scores: Dict[str, Optional[float]],
        user_level: int = 1,
    ) -> Dict[str, VolumeResult]:
        """批量计算多个动作的训练量。

        Returns:
            {action_id: VolumeResult}
        """
        results = {}
        for action in actions:
            results[action.id] = self.calculate(action, fms_scores, user_level)
        return results

    def get_total_volume(
        self,
        volume_results: Dict[str, VolumeResult],
        actions: list,
    ) -> Dict[str, int]:
        """汇总训练总量。

        Returns:
            {'total_sets': int, 'total_reps': int, 'total_duration_minutes': float}
        """
        total_sets = 0
        total_reps = 0
        total_duration = 0

        for action in actions:
            vol = volume_results.get(action.id)
            if vol is None:
                continue
            total_sets += vol.sets
            total_reps += vol.sets * vol.reps
            total_duration += vol.sets * vol.duration_seconds

        return {
            "total_sets": total_sets,
            "total_reps": total_reps,
            "total_duration_minutes": round(total_duration / 60, 1),
        }
