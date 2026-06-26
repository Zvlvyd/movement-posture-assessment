# -*- coding: utf-8 -*-
"""
Verification Mapper
Maps static posture findings to targeted ROM verification movements.
Auto-generates a verification plan from MultiViewAnalyzer results.
"""
from dataclasses import dataclass, field
from typing import Dict, List, Optional, Tuple

from .movement_definitions import MovementDefinition, get_movement, MOVEMENTS


@dataclass
class VerificationMovement:
    """A single verification movement to perform."""
    movement_def: MovementDefinition   # the movement definition
    trigger_problems: List[str]        # which static flags triggered this
    priority: int                      # 0 = highest priority
    key_rom_track: List[str]           # angle keys to track ROM for
    velocity_pairs: List[Tuple[str, str]]  # (left_key, right_key) for velocity check
    rom_checks: List[str] = field(default_factory=list)  # extra ROM deficit checks
    instruction_override: str = ""     # custom instruction for verification context


# ----------------------------------------------------------------
# Problem → Verification Movement Mapping
# ----------------------------------------------------------------
VERIFICATION_MAP: Dict[str, dict] = {
    "head_forward_posture": {
        "use_movement_index": 0,  # 颈部活动度评估
        "key_rom": ["neck_tilt"],
        "velocity_pairs": [],
        "rom_checks": ["head_forward_deg"],
        "instruction_override": "针对头前倾问题，请缓慢进行颈部旋转与侧屈，我们会追踪您的颈部活动范围。",
    },
    "shoulder_imbalance": {
        "use_movement_index": 1,  # 肩关节活动度评估
        "key_rom": ["left_shoulder", "right_shoulder"],
        "velocity_pairs": [("left_shoulder", "right_shoulder")],
        "rom_checks": ["left_shoulder", "right_shoulder", "left_elbow", "right_elbow"],
        "instruction_override": "针对肩部不对称，请缓慢抬举双臂并尝试背后触手，注意左右两侧是否感觉不同。",
    },
    "pelvic_anterior_tilt": {
        "use_movement_index": 2,  # 脊柱活动度评估
        "key_rom": ["trunk_tilt", "left_hip", "right_hip"],
        "velocity_pairs": [],
        "rom_checks": ["left_hip", "right_hip"],
        "instruction_override": "针对骨盆前倾，请缓慢向前弯腰触摸脚趾，感受大腿后侧的拉伸。",
    },
    "pelvic_lateral_tilt": {
        "use_movement_index": 3,  # 深蹲活动度评估
        "key_rom": ["left_knee", "right_knee", "left_hip", "right_hip"],
        "velocity_pairs": [("left_knee", "right_knee"), ("left_hip", "right_hip")],
        "rom_checks": ["left_knee", "right_knee"],
        "instruction_override": "针对骨盆侧倾，请缓慢下蹲，注意两侧膝盖和髋部是否均匀受力。",
    },
    "knee_hyperextension": {
        "use_movement_index": 3,  # 深蹲活动度评估
        "key_rom": ["left_knee", "right_knee"],
        "velocity_pairs": [],
        "rom_checks": ["knee_hyperextension_deg"],
        "instruction_override": "针对膝超伸，下蹲时请控制膝盖不要锁死，保持微屈。",
    },
    "pelvic_posterior_tilt": {
        "use_movement_index": 2,  # 脊柱活动度评估
        "key_rom": ["trunk_tilt", "left_hip", "right_hip"],
        "velocity_pairs": [],
        "rom_checks": ["left_hip", "right_hip"],
        "instruction_override": "针对骨盆后倾，请缓慢向前弯腰并注意髋部屈曲范围。",
    },
    "possible_scoliosis": {
        "use_movement_index": None,  # No verification — suggest medical evaluation
        "key_rom": [],
        "velocity_pairs": [],
        "rom_checks": [],
        "note": "建议就医进行专业脊柱侧弯评估（X光/CT），本系统不做运动验证。",
    },
}


class VerificationMapper:
    """
    Generates a prioritized verification plan from static findings.
    Deduplicates movements (multiple problems may map to the same movement).
    """

    @staticmethod
    def build_plan(flags: List[str],
                   severity_map: Dict[str, str] = None) -> List[VerificationMovement]:
        """
        Build ordered verification plan from a list of problem flags.

        Args:
            flags: list of problem flag strings, e.g. ["shoulder_imbalance", "head_forward_posture"]
            severity_map: optional {flag: severity} for priority sorting

        Returns:
            List of VerificationMovement, deduplicated and sorted by priority.
        """
        if severity_map is None:
            severity_map = {}

        severity_order = {"severe": 0, "moderate": 1, "mild": 2, "normal": 3}

        # Group flags by movement index to deduplicate
        movement_groups: Dict[int, List[str]] = {}  # movement_index -> [flags]
        skipped_flags: List[str] = []

        for flag in flags:
            config = VERIFICATION_MAP.get(flag)
            if config is None:
                continue

            mov_idx = config.get("use_movement_index")
            if mov_idx is None:
                skipped_flags.append(flag)
                continue

            if mov_idx not in movement_groups:
                movement_groups[mov_idx] = []
            movement_groups[mov_idx].append(flag)

        # Build verification movements
        plan = []
        for mov_idx, trigger_flags in movement_groups.items():
            movement_def = get_movement(mov_idx)
            if movement_def is None:
                continue

            # Merge configs from all triggering problems
            merged_key_rom = set()
            merged_velocity_pairs = set()
            merged_rom_checks = set()
            merged_instructions = []

            for flag in trigger_flags:
                config = VERIFICATION_MAP.get(flag, {})
                for k in config.get("key_rom", []):
                    merged_key_rom.add(k)
                for pair in config.get("velocity_pairs", []):
                    merged_velocity_pairs.add(pair)
                for k in config.get("rom_checks", []):
                    merged_rom_checks.add(k)
                inst = config.get("instruction_override", "")
                if inst:
                    merged_instructions.append(inst)

            # Priority = worst severity among trigger problems
            priority = min(
                severity_order.get(severity_map.get(f, "normal"), 99)
                for f in trigger_flags
            )

            plan.append(VerificationMovement(
                movement_def=movement_def,
                trigger_problems=trigger_flags,
                priority=priority,
                key_rom_track=list(merged_key_rom),
                velocity_pairs=list(merged_velocity_pairs),
                rom_checks=list(merged_rom_checks),
                instruction_override="；".join(merged_instructions) if merged_instructions else "",
            ))

        # Sort by priority (most severe first), then by movement index
        plan.sort(key=lambda vm: (vm.priority, vm.movement_def.index))

        return plan

    @staticmethod
    def get_skipped_notes(flags: List[str]) -> List[Dict]:
        """Get notes for flags that require medical evaluation (no movement verification)."""
        notes = []
        for flag in flags:
            config = VERIFICATION_MAP.get(flag, {})
            if config.get("use_movement_index") is None:
                notes.append({
                    "flag": flag,
                    "note": config.get("note", "此问题需专业评估，无自动化验证。"),
                })
        return notes

    @staticmethod
    def get_all_velocity_pairs(plan: List[VerificationMovement]) -> List[Tuple[str, str]]:
        """Extract all unique velocity pairs from a verification plan."""
        all_pairs = set()
        for vm in plan:
            for pair in vm.velocity_pairs:
                all_pairs.add(pair)
        return list(all_pairs)
