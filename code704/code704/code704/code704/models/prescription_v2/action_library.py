"""
标准动作库加载器。

加载 action_library.json，提供按条件查询动作的接口。
采用单例模式，与现有 ProblemExerciseLibrary 保持一致。
"""
import json
import os
from typing import List, Dict, Optional, Any
from dataclasses import dataclass, field


@dataclass
class Action:
    """标准动作数据类。"""
    id: str
    family: str
    family_name: str
    family_name_en: str
    name: str
    name_en: str
    category: str
    subcategory: str
    difficulty: int  # 1-5
    intensity: str  # LOW / MEDIUM / HIGH
    is_regression_of: Optional[str] = None
    is_progression_of: Optional[str] = None
    target_body_parts: List[str] = field(default_factory=list)
    contraindications: Dict[str, int] = field(default_factory=dict)
    problem_mapping: Dict[str, float] = field(default_factory=dict)
    phases: List[str] = field(default_factory=list)
    default_sets: int = 3
    default_reps: int = 10
    default_duration_seconds: int = 0
    description: str = ""
    steps: List[str] = field(default_factory=list)
    cues: List[str] = field(default_factory=list)
    display_type: str = "image"  # image / video
    display_url: str = ""


class StandardActionLibrary:
    """标准动作库（单例）。

    加载 action_library.json 并提供多种查询接口：
    - get_by_id: 按 ID 精确查找
    - get_by_family: 按动作家族筛选
    - get_by_category: 按大类筛选
    - get_by_problem: 按体态问题筛选（按相关性排序）
    - get_by_phase: 按训练阶段筛选
    - get_eligible: 按 FMS 分数筛选可执行的动作
    - get_all: 获取全部动作
    """

    _instance = None
    _actions: Dict[str, Action] = {}
    _actions_list: List[Action] = []
    _meta: Dict[str, Any] = {}

    def __new__(cls, json_path: str = None):
        if cls._instance is None:
            cls._instance = super().__new__(cls)
            cls._instance._loaded = False
        return cls._instance

    def __init__(self, json_path: str = None):
        if self._loaded:
            return
        if json_path is None:
            json_path = os.path.join(os.path.dirname(__file__), "action_library.json")
        self._load(json_path)
        self._loaded = True

    def _load(self, json_path: str):
        """从 JSON 文件加载动作库。"""
        if not os.path.exists(json_path):
            raise FileNotFoundError(f"动作库文件不存在: {json_path}")

        with open(json_path, "r", encoding="utf-8") as f:
            data = json.load(f)

        self._meta = data.get("meta", {})
        self._actions = {}
        self._actions_list = []

        for item in data.get("actions", []):
            action = Action(
                id=item["id"],
                family=item.get("family", ""),
                family_name=item.get("family_name", ""),
                family_name_en=item.get("family_name_en", ""),
                name=item["name"],
                name_en=item.get("name_en", ""),
                category=item.get("category", ""),
                subcategory=item.get("subcategory", ""),
                difficulty=item.get("difficulty", 1),
                intensity=item.get("intensity", "MEDIUM"),
                is_regression_of=item.get("is_regression_of"),
                is_progression_of=item.get("is_progression_of"),
                target_body_parts=item.get("target_body_parts", []),
                contraindications=item.get("contraindications", {}),
                problem_mapping=item.get("problem_mapping", {}),
                phases=item.get("phases", []),
                default_sets=item.get("default_sets", 3),
                default_reps=item.get("default_reps", 10),
                default_duration_seconds=item.get("default_duration_seconds", 0),
                description=item.get("description", ""),
                steps=item.get("steps", []),
                cues=item.get("cues", []),
                display_type=item.get("display_type", "image"),
                display_url=item.get("display_url", ""),
            )
            self._actions[action.id] = action
            self._actions_list.append(action)

    # ─── 查询接口 ────────────────────────────────────────────

    @property
    def meta(self) -> Dict[str, Any]:
        return self._meta

    @property
    def total_count(self) -> int:
        return len(self._actions_list)

    def get_by_id(self, action_id: str) -> Optional[Action]:
        """按 ID 获取动作。"""
        return self._actions.get(action_id)

    def get_by_family(self, family: str) -> List[Action]:
        """获取指定家族的所有动作（按难度升序）。"""
        result = [a for a in self._actions_list if a.family == family]
        result.sort(key=lambda a: a.difficulty)
        return result

    def get_by_category(self, category: str) -> List[Action]:
        """按大类获取动作。"""
        return [a for a in self._actions_list if a.category == category]

    def get_by_problem(
        self,
        problem_ids: List[str],
        min_relevance: float = 0.0,
        max_results: int = 30
    ) -> List[Action]:
        """按体态问题获取相关动作，按相关性总分降序排列。

        Args:
            problem_ids: 检测到的体态问题 ID 列表
            min_relevance: 最低相关性阈值（0-1）
            max_results: 最大返回数量

        Returns:
            按 problem_mapping 总分降序的动作列表
        """
        scored = []
        for action in self._actions_list:
            score = sum(
                action.problem_mapping.get(pid, 0.0)
                for pid in problem_ids
            )
            if score > min_relevance:
                scored.append((action, score))
        scored.sort(key=lambda x: x[1], reverse=True)
        return [action for action, _ in scored[:max_results]]

    def get_by_phase(self, phase: str) -> List[Action]:
        """按训练阶段获取动作。"""
        return [a for a in self._actions_list if phase in a.phases]

    def get_eligible(
        self,
        fms_scores: Dict[str, Optional[float]]
    ) -> List[Dict[str, Any]]:
        """按 FMS 分数筛选可执行的动作。

        Args:
            fms_scores: FMS 各维度分数，如 {'balance': 65, 'flexibility': 50, ...}

        Returns:
            每个元素为 {action, eligible, risk_level, failing_dimensions}
        """
        results = []
        for action in self._actions_list:
            failing = []
            for dim, min_score in action.contraindications.items():
                dim_key = dim.replace("min_", "")  # min_balance_score → balance_score
                user_score = fms_scores.get(dim_key)
                if user_score is not None and user_score < min_score:
                    failing.append(dim_key)

            if len(failing) == 0:
                risk = "safe"
                eligible = True
            elif len(failing) <= 2:
                risk = "caution"
                eligible = True
            else:
                risk = "unsafe"
                eligible = False

            results.append({
                "action": action,
                "eligible": eligible,
                "risk_level": risk,
                "failing_dimensions": failing,
            })

        return results

    def get_all(self) -> List[Action]:
        """获取全部动作（按类别+难度排序）。"""
        category_order = {
            "活动度": 0, "拉伸": 1, "平衡": 2,
            "颈部矫正": 3, "核心": 4, "上肢推": 5,
            "上肢拉": 6, "下肢蹲": 7, "下肢拉": 8,
        }
        result = sorted(
            self._actions_list,
            key=lambda a: (category_order.get(a.category, 99), a.difficulty)
        )
        return result

    def get_families(self) -> List[Dict[str, str]]:
        """获取所有动作家族概览。"""
        families = {}
        for a in self._actions_list:
            if a.family not in families:
                families[a.family] = {
                    "family": a.family,
                    "family_name": a.family_name,
                    "family_name_en": a.family_name_en,
                    "category": a.category,
                    "variant_count": 0,
                    "difficulty_range": f"{a.difficulty}-{a.difficulty}",
                }
            fam = families[a.family]
            fam["variant_count"] += 1
            fam["difficulty_range"] = (
                f"{min(fam['variant_count'], a.difficulty)}-{a.difficulty}"
                if fam["variant_count"] > 1
                else str(a.difficulty)
            )
        return sorted(families.values(), key=lambda f: f["category"])

    def get_phase_guidelines(self) -> Dict[str, Any]:
        """获取训练阶段编排指南。"""
        return self._meta.get("phase_guidelines", {})

    def get_fms_defaults(self) -> Dict[str, Any]:
        """获取 FMS 维度默认值参考。"""
        return self._meta.get("fms_dimension_defaults", {})


# 便捷函数：获取默认单例
_default_library = None


def get_action_library(json_path: str = None) -> StandardActionLibrary:
    """获取标准动作库单例。"""
    global _default_library
    if _default_library is None:
        _default_library = StandardActionLibrary(json_path)
    return _default_library
