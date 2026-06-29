"""
处方生成模块 v2 —— 基于标准动作库 + FMS + 体态评估的智能处方系统。

核心组件：
- StandardActionLibrary: 标准动作库（58个徒手动作，10大家族，难度递进）
- EligibilityChecker:   FMS 能力 → 动作可行性判断
- VolumeCalculator:      FMS 分数 → 训练量计算
- PrescriptionBuilder:   本地规则引擎（DeepSeek 不可用时的回退方案）
- TemplateEngine:        提示词模板加载与渲染
- DeepSeekPrescription:  DeepSeek API 调用与处方 JSON 解析
"""

from .action_library import (
    Action,
    StandardActionLibrary,
    get_action_library,
)
from .eligibility_checker import (
    EligibilityChecker,
    EligibilityResult,
    DIMENSION_LABELS,
)
from .volume_calculator import (
    VolumeCalculator,
    VolumeResult,
)
from .prescription_builder import (
    PrescriptionBuilder,
    PrescriptionPlan,
    PrescriptionPlanItem,
)
from .template_engine import TemplateEngine
from .deepseek_prescription import DeepSeekPrescription, DeepSeekResult

__all__ = [
    # Action library
    "Action",
    "StandardActionLibrary",
    "get_action_library",
    # Eligibility
    "EligibilityChecker",
    "EligibilityResult",
    "DIMENSION_LABELS",
    # Volume
    "VolumeCalculator",
    "VolumeResult",
    # Prescription builder
    "PrescriptionBuilder",
    "PrescriptionPlan",
    "PrescriptionPlanItem",
    # Template & DeepSeek
    "TemplateEngine",
    "DeepSeekPrescription",
    "DeepSeekResult",
]
