# -*- coding: utf-8 -*-
"""
体态问题→动作映射器
将体态评估检测到的问题标签，映射到 exercises.json 中的具体拉伸/强化动作，
支持器械过滤和强度分级。
"""
import json
import re
import math
from pathlib import Path
from typing import Dict, List, Optional, Tuple
from enum import Enum
from dataclasses import dataclass, field

KNOWLEDGE_DIR = Path(__file__).parent.parent / "knowledge"

# ── 器械关键词检测 ──────────────────────────────────────────────────────────
# 必需器械（需要专门购买或准备的）
REQUIRED_EQUIPMENT_KEYWORDS = {
    "弹力带": "弹力带",
    "哑铃": "哑铃",
    "泡沫轴": "泡沫轴",
}
# 可选器械（居家常见物品，无器械时可徒手替代）
OPTIONAL_EQUIPMENT_KEYWORDS = {
    "门框": "门框",
    "墙": "墙壁",
    "毛巾": "毛巾",
    "矿泉水瓶": "矿泉水瓶",
    "垫子": "垫子",
    "枕头": "枕头",
}

def detect_equipment(name: str, steps: List[str], cues: List[str]) -> Tuple[List[str], List[str]]:
    """检测一个动作所需器械，返回 (必需器械, 可选器械)"""
    text = name + " " + " ".join(steps) + " " + " ".join(cues)
    required = []
    optional = []
    for kw, label in REQUIRED_EQUIPMENT_KEYWORDS.items():
        if kw in text:
            required.append(label)
    for kw, label in OPTIONAL_EQUIPMENT_KEYWORDS.items():
        if kw in text:
            optional.append(label)
    return (list(set(required)), list(set(optional)))


# ── 强度分级 ────────────────────────────────────────────────────────────────
class IntensityLevel(str, Enum):
    LOW = "low"       # 低强度（新手/恢复期）
    MEDIUM = "medium"  # 中等强度（日常训练）
    HIGH = "high"      # 高强度（进阶/力量训练）

def parse_intensity(sets_str: str) -> IntensityLevel:
    """根据 sets 字段文本解析强度等级"""
    sets_match = re.search(r"(\d+)\s*组", sets_str)
    raw_reps_match = re.search(r"×\s*(\d+)\s*次", sets_str)
    duration_match = re.search(r"×\s*(\d+)\s*秒", sets_str)

    sets = int(sets_match.group(1)) if sets_match else 3
    has_duration = bool(duration_match)
    has_reps = bool(raw_reps_match)

    # 持续时间类动作（拉伸/等长）→ 强度权重低
    if has_duration and not has_reps:
        duration = int(duration_match.group(1))
        score = sets * (duration / 15)
        if "每侧" in sets_str:
            score *= 1.3
        if "进阶" in sets_str:
            score *= 1.5
    else:
        # 次数类动作（力量训练）
        reps = int(raw_reps_match.group(1)) if raw_reps_match else 10
        score = float(sets * reps)
        if "每侧" in sets_str:
            score *= 1.5
        if "进阶" in sets_str:
            score += 5

    if score <= 25:
        return IntensityLevel.LOW
    elif score <= 60:
        return IntensityLevel.MEDIUM
    else:
        return IntensityLevel.HIGH


# ── 动作条目数据结构 ──────────────────────────────────────────────────────
class ExercisePhase(str, Enum):
    WARMUP = "warmup"
    ACTIVATION = "activation"
    MAIN = "main"
    COOLDOWN = "cooldown"

@dataclass
class ExerciseItem:
    name: str
    problem_id: str           # 对应 problems.json 的 key
    category: str             # "stretch" 或 "strength"
    phase: ExercisePhase
    steps: List[str]
    sets: str
    cues: List[str]
    equipment: List[str]      # 所需器械列表
    intensity: IntensityLevel
    is_major: bool = False    # 主训练动作（strength 类为主）

    def to_dict(self) -> dict:
        return {
            "name": self.name,
            "problem_id": self.problem_id,
            "category": self.category,
            "phase": self.phase.value,
            "steps": self.steps,
            "sets": self.sets,
            "cues": self.cues,
            "equipment": self.equipment,
            "intensity": self.intensity.value,
            "is_major": self.is_major,
        }


# ── 动作库 ─────────────────────────────────────────────────────────────────
class ProblemExerciseLibrary:
    """加载并缓存 exercises.json 中的所有动作"""

    _instance = None
    _exercises: Dict[str, List[ExerciseItem]] = None

    def __new__(cls):
        if cls._instance is None:
            cls._instance = super().__new__(cls)
        return cls._instance

    def __init__(self):
        if self._exercises is not None:
            return
        path = KNOWLEDGE_DIR / "exercises.json"
        with open(path, "r", encoding="utf-8") as f:
            raw = json.load(f)

        self._exercises = {}
        for problem_id, problem_data in raw.items():
            items = []
            for ex in problem_data.get("stretch", []):
                req_eq, opt_eq = detect_equipment(ex["name"], ex.get("steps", []), ex.get("cues", []))
                equipment = req_eq + opt_eq
                intensity = parse_intensity(ex.get("sets", "3组 × 30秒"))
                items.append(ExerciseItem(
                    name=ex["name"],
                    problem_id=problem_id,
                    category="stretch",
                    phase=ExercisePhase.COOLDOWN if intensity == IntensityLevel.LOW else ExercisePhase.WARMUP,
                    steps=ex.get("steps", []),
                    sets=ex.get("sets", ""),
                    cues=ex.get("cues", []),
                    equipment=equipment,
                    intensity=intensity,
                    is_major=(intensity != IntensityLevel.LOW),
                ))
            for ex in problem_data.get("strength", []):
                req_eq, opt_eq = detect_equipment(ex["name"], ex.get("steps", []), ex.get("cues", []))
                equipment = req_eq + opt_eq
                intensity = parse_intensity(ex.get("sets", "3组 × 10次"))
                items.append(ExerciseItem(
                    name=ex["name"],
                    problem_id=problem_id,
                    category="strength",
                    phase=ExercisePhase.MAIN,
                    steps=ex.get("steps", []),
                    sets=ex.get("sets", ""),
                    cues=ex.get("cues", []),
                    equipment=equipment,
                    intensity=intensity,
                    is_major=True,
                ))
            self._exercises[problem_id] = items

    def get_all_problem_ids(self) -> List[str]:
        return list(self._exercises.keys())

    def get_for_problem(self, problem_id: str) -> List[ExerciseItem]:
        return self._exercises.get(problem_id, [])

    def filter(self,
               problem_ids: List[str],
               use_equipment: bool = True,
               max_intensity: IntensityLevel = IntensityLevel.HIGH,
               ) -> List[ExerciseItem]:
        """
        Args:
            problem_ids: 体态问题ID列表
            use_equipment: True=包含器械/徒手, False=仅可选器械的徒手替代（排除必需器械）
            max_intensity: 最高强度等级
        """
        result = []
        intensity_order = {IntensityLevel.LOW: 1, IntensityLevel.MEDIUM: 2, IntensityLevel.HIGH: 3}
        max_order = intensity_order.get(max_intensity, 3)

        for pid in problem_ids:
            for ex in self.get_for_problem(pid):
                if intensity_order.get(ex.intensity, 3) > max_order:
                    continue
                if not use_equipment and ex.equipment:
                    # Check if any equipment is REQUIRED (not just optional)
                    text = ex.name + " " + " ".join(ex.steps) + " " + " ".join(ex.cues)
                    has_required = any(kw in text for kw in REQUIRED_EQUIPMENT_KEYWORDS)
                    if has_required:
                        continue
                result.append(ex)
        return result


# ── 处方组装器 ──────────────────────────────────────────────────────────────
class PosturePrescriptionBuilder:
    """
    根据体态问题列表和用户偏好，组装完整处方。
    处方结构：
      - warmup: 低强度拉伸（全身热身）
      - activation: 中强度拉伸（针对体态问题的拉伸激活）
      - main: 针对体态问题的强化训练
      - cooldown: 低强度拉伸（放松）
    """

    @staticmethod
    def build(problem_ids: List[str],
              use_equipment: bool = True,
              intensity: str = "medium",
              ) -> Dict:
        """
        组装处方。

        Args:
            problem_ids: 体态问题ID列表
            use_equipment: 是否使用器械
            intensity: "low" / "medium" / "high"

        Returns:
            处方案例字典，包含 items 列表
        """
        lib = ProblemExerciseLibrary()
        intensity_map = {
            "low": IntensityLevel.LOW,
            "medium": IntensityLevel.MEDIUM,
            "high": IntensityLevel.HIGH,
        }
        max_intensity = intensity_map.get(intensity, IntensityLevel.MEDIUM)

        # 按体态问题获取过滤后的动作
        filtered = lib.filter(problem_ids, use_equipment=use_equipment, max_intensity=max_intensity)

        # 分类到各阶段
        warmup: List[ExerciseItem] = []
        activation: List[ExerciseItem] = []
        main: List[ExerciseItem] = []
        cooldown: List[ExerciseItem] = []

        for ex in filtered:
            if ex.phase == ExercisePhase.WARMUP:
                warmup.append(ex)
            elif ex.phase == ExercisePhase.MAIN and ex.category == "strength":
                main.append(ex)
            elif ex.phase == ExercisePhase.MAIN and ex.category == "stretch":
                activation.append(ex)
            else:
                cooldown.append(ex)

        # 确保每个阶段不空；如果某个体态问题没有动作，跳过
        # 为每个体态问题确保至少有1个拉伸和1个强化动作
        covered_problems = set()
        for pid in problem_ids:
            pid_exercises = [e for e in filtered if e.problem_id == pid]
            stretch_ex = [e for e in pid_exercises if e.category == "stretch"]
            strength_ex = [e for e in pid_exercises if e.category == "strength"]

            if stretch_ex:
                covered_problems.add(pid)
            if strength_ex:
                covered_problems.add(pid)

        # 重新整理 warmup: 每问题取1个拉伸（如果 warmup 段无则可放 activation）
        if not warmup:
            for ex in filtered:
                if ex.category == "stretch" and len(warmup) < len(problem_ids):
                    warmup.append(ex)

        # activation: 取中等强度的拉伸
        if not activation:
            for pid in problem_ids:
                pid_stretch = [e for e in filtered if e.problem_id == pid and e.category == "stretch"]
                for e in pid_stretch:
                    if e not in warmup and e not in activation:
                        activation.append(e)
                        break

        # main: 每个体态问题取1-2个强化动作
        main_by_problem = {}
        for ex in main:
            if ex.problem_id not in main_by_problem:
                main_by_problem[ex.problem_id] = []
            if len(main_by_problem[ex.problem_id]) < 2:
                main_by_problem[ex.problem_id].append(ex)
        main = []
        for pid in problem_ids:
            main.extend(main_by_problem.get(pid, []))

        # cooldown: 取低强度拉伸
        if not cooldown:
            cooldown = activation[:]

        # 组装最终 items
        all_sections = [("warmup", warmup[:3]), ("activation", activation[:2]),
                        ("main", main[:4]), ("cooldown", cooldown[:2])]

        items = []
        order = 0
        for phase_name, section_items in all_sections:
            for ex in section_items:
                order += 1
                items.append({
                    "name": ex.name,
                    "phase": phase_name,
                    "category": ex.category,
                    "problem_id": ex.problem_id,
                    "sets": ex.sets,
                    "steps": ex.steps,
                    "cues": ex.cues,
                    "equipment": ex.equipment,
                    "intensity": ex.intensity.value,
                    "order_index": order,
                })
        return {
            "items": items,
            "total_exercises": len(items),
            "covered_problems": list(covered_problems),
            "config": {
                "use_equipment": use_equipment,
                "intensity": intensity,
            },
        }


