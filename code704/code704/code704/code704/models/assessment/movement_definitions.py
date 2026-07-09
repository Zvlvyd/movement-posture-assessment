# -*- coding: utf-8 -*-
"""
评估动作定义模块 - 定义5组引导动作，替代旧FMS测试
每个动作指定目标关节、追踪关键点、正常ROM范围、评估侧重点
"""
from dataclasses import dataclass, field
from typing import List, Dict, Optional, Tuple
from enum import Enum


class MovementSide(Enum):
    BILATERAL = "bilateral"
    LEFT = "left"
    RIGHT = "right"
    SEQUENTIAL = "sequential"  # 先左后右


@dataclass
class JointTarget:
    """目标关节的追踪定义"""
    joint_name: str              # 关节名称，如 "left_knee", "cervical_rotation"
    display_name: str            # 显示名称，如 "左膝关节", "颈椎旋转"
    angle_key: str               # AngleCalculator 中的角度键名
    min_normal: float            # 正常最小ROM (度)
    max_normal: float            # 正常最大ROM (度)
    direction: str = "larger_better"  # larger_better / smaller_better
    unit: str = "°"


@dataclass
class MovementDefinition:
    """单个评估动作定义"""
    index: int                   # 序号 0-4
    name: str                    # 动作名称
    instruction: str             # 引导语
    side: MovementSide           # 单侧/双侧/先后
    duration_hint: str           # 预计耗时提示
    targets: List[JointTarget] = field(default_factory=list)
    related_problems: List[str] = field(default_factory=list)  # 关联的体态问题标签
    related_muscles_tight: List[str] = field(default_factory=list)  # ROM不足时关联的紧张肌肉
    related_muscles_weak: List[str] = field(default_factory=list)   # ROM不足时关联的薄弱肌肉


# ============================================================
# 5组引导动作定义
# ============================================================

MOVEMENTS: List[MovementDefinition] = [
    # 动作1：颈部评估
    MovementDefinition(
        index=0,
        name="颈部活动度评估",
        instruction="站直身体。先将头缓慢转向左侧至最大限度，保持2秒后回正；再转向右侧至最大限度。然后头部向左肩侧屈，再向右肩侧屈。",
        side=MovementSide.SEQUENTIAL,
        duration_hint="约30秒",
        targets=[
            JointTarget("cervical_rotation_left", "颈椎左旋", "neck_tilt", 60, 90, unit="°"),
            JointTarget("cervical_rotation_right", "颈椎右旋", "neck_tilt", 60, 90, unit="°"),
            JointTarget("cervical_lateral_left", "颈椎左侧屈", "head_tilt", 35, 45, unit="°"),
            JointTarget("cervical_lateral_right", "颈椎右侧屈", "head_tilt", 35, 45, unit="°"),
        ],
        related_problems=["head_forward_posture"],
        related_muscles_tight=["胸锁乳突肌", "斜方肌上束"],
        related_muscles_weak=["深层颈屈肌", "下斜方肌"],
    ),
    # 动作2：肩关节评估
    MovementDefinition(
        index=1,
        name="肩关节活动度评估",
        instruction="双臂从体侧缓慢向前举起至头顶上方，尽量伸直。然后一手从肩上向后、另一手从腰后向上，尝试在背后触碰双手。",
        side=MovementSide.BILATERAL,
        duration_hint="约30秒",
        targets=[
            JointTarget("left_shoulder_flexion", "左肩屈曲", "left_shoulder", 150, 180, unit="°"),
            JointTarget("right_shoulder_flexion", "右肩屈曲", "right_shoulder", 150, 180, unit="°"),
            JointTarget("left_elbow_extension", "左肘伸展", "left_elbow", 0, 10, direction="smaller_better", unit="°"),
            JointTarget("right_elbow_extension", "右肘伸展", "right_elbow", 0, 10, direction="smaller_better", unit="°"),
        ],
        related_problems=["shoulder_imbalance"],
        related_muscles_tight=["胸小肌", "胸锁乳突肌"],
        related_muscles_weak=["下斜方肌", "菱形肌", "前锯肌"],
    ),
    # 动作3：脊柱评估
    MovementDefinition(
        index=2,
        name="脊柱活动度评估",
        instruction="双脚与肩同宽，缓慢向前弯腰，尽量用手触摸脚趾，膝盖保持伸直。然后身体向左侧弯曲，再向右侧弯曲。",
        side=MovementSide.BILATERAL,
        duration_hint="约30秒",
        targets=[
            JointTarget("spine_flexion", "脊柱屈曲", "trunk_tilt", 60, 100, unit="°"),
            JointTarget("left_hip_flexion_bend", "左髋屈曲(体前屈)", "left_hip", 70, 110, unit="°"),
            JointTarget("right_hip_flexion_bend", "右髋屈曲(体前屈)", "right_hip", 70, 110, unit="°"),
        ],
        related_problems=["pelvic_anterior_tilt", "pelvic_lateral_tilt", "possible_scoliosis"],
        related_muscles_tight=["腘绳肌", "髂腰肌"],
        related_muscles_weak=["臀大肌", "腹横肌"],
    ),
    # 动作4：深蹲评估
    MovementDefinition(
        index=3,
        name="深蹲活动度评估",
        instruction="双脚与肩同宽，双手前平举保持平衡。缓慢下蹲至最低点，保持脚跟不离地。然后换单腿做小幅下蹲。",
        side=MovementSide.SEQUENTIAL,
        duration_hint="约40秒",
        targets=[
            JointTarget("left_knee_flexion", "左膝屈曲", "left_knee", 120, 155, unit="°"),
            JointTarget("right_knee_flexion", "右膝屈曲", "right_knee", 120, 155, unit="°"),
            JointTarget("left_hip_flexion_squat", "左髋屈曲(深蹲)", "left_hip", 90, 130, unit="°"),
            JointTarget("right_hip_flexion_squat", "右髋屈曲(深蹲)", "right_hip", 90, 130, unit="°"),
        ],
        related_problems=["knee_hyperextension", "pelvic_lateral_tilt"],
        related_muscles_tight=["股直肌", "腘绳肌"],
        related_muscles_weak=["股四头肌", "臀中肌", "臀大肌"],
    ),
    # 动作5：髋关节评估
    MovementDefinition(
        index=4,
        name="髋关节活动度评估",
        instruction="站姿，单手扶墙保持平衡。将一侧膝盖向胸部抬起至最高，然后缓慢向侧面抬起腿（外展）。换另一侧重复。",
        side=MovementSide.SEQUENTIAL,
        duration_hint="约40秒",
        targets=[
            JointTarget("left_hip_flexion_kneeup", "左髋屈曲(抬膝)", "left_hip", 100, 130, unit="°"),
            JointTarget("right_hip_flexion_kneeup", "右髋屈曲(抬膝)", "right_hip", 100, 130, unit="°"),
        ],
        related_problems=["pelvic_anterior_tilt", "pelvic_lateral_tilt"],
        related_muscles_tight=["髂腰肌", "股直肌"],
        related_muscles_weak=["臀大肌", "腹横肌", "腘绳肌"],
    ),
]


def get_movement(index: int) -> Optional[MovementDefinition]:
    """获取指定序号的评估动作"""
    for m in MOVEMENTS:
        if m.index == index:
            return m
    return None


def get_all_movements() -> List[MovementDefinition]:
    return MOVEMENTS


def get_target_angle_keys() -> List[str]:
    """获取所有动作中需要追踪的角度键名（去重）"""
    keys = set()
    for m in MOVEMENTS:
        for t in m.targets:
            keys.add(t.angle_key)
    return list(keys)
