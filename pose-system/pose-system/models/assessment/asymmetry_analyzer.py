# -*- coding: utf-8 -*-
"""
不对称分析器 - 比较左右ROM差异，标记不对称问题
"""
from typing import Dict, List, Optional, Tuple
from dataclasses import dataclass, field
from .rom_tracker import JointROM, MovementROMResult


@dataclass
class AsymmetryFinding:
    """不对称发现"""
    joint: str                    # 关节名称
    side_limited: str             # 受限侧 (left/right)
    rom_left: float               # 左侧ROM
    rom_right: float              # 右侧ROM
    diff_pct: float               # 差异百分比
    severity: str                 # mild/moderate/severe
    related_muscles_tight: List[str] = field(default_factory=list)
    related_muscles_weak: List[str] = field(default_factory=list)
    problem_flag: str = ""        # 关联的体态问题标签


class AsymmetryAnalyzer:
    """
    不对称分析器
    - 对每个双侧动作比较左右 ROM 差异
    - 差异超过阈值 → 标记为不对称问题
    - 关联到对应肌肉
    """
    
    # 不对称阈值（差异百分比）
    MILD_THRESHOLD = 10      # >10% 轻度不对称
    MODERATE_THRESHOLD = 20  # >20% 中度不对称
    SEVERE_THRESHOLD = 35    # >35% 严重不对称
    
    # ROM 不足阈值（与常模比较）
    ROM_DEFICIT_MILD = 0.85   # <85% 常模 → 轻度受限
    ROM_DEFICIT_MODERATE = 0.70  # <70% 常模 → 中度受限
    ROM_DEFICIT_SEVERE = 0.50    # <50% 常模 → 严重受限
    
    @classmethod
    def analyze_bilateral(cls, left_rom: JointROM, right_rom: JointROM,
                          normal_min: float, normal_max: float) -> Optional[AsymmetryFinding]:
        """
        分析双侧ROM的不对称性
        left_rom: 左侧ROM追踪结果
        right_rom: 右侧ROM追踪结果
        normal_min/max: 正常ROM范围
        """
        if left_rom.rom_deg <= 0 or right_rom.rom_deg <= 0:
            return None
        
        # 计算差异
        larger = max(left_rom.rom_deg, right_rom.rom_deg)
        smaller = min(left_rom.rom_deg, right_rom.rom_deg)
        
        if larger < 1:
            return None
        
        diff_pct = round((larger - smaller) / larger * 100, 1)
        
        if diff_pct < cls.MILD_THRESHOLD:
            return None
        
        # 确定受限侧
        if left_rom.rom_deg < right_rom.rom_deg:
            side_limited = "left"
            limited_rom = left_rom.rom_deg
        else:
            side_limited = "right"
            limited_rom = right_rom.rom_deg
        
        # 严重程度
        if diff_pct >= cls.SEVERE_THRESHOLD:
            severity = "severe"
        elif diff_pct >= cls.MODERATE_THRESHOLD:
            severity = "moderate"
        else:
            severity = "mild"
        
        return AsymmetryFinding(
            joint=left_rom.joint,
            side_limited=side_limited,
            rom_left=left_rom.rom_deg,
            rom_right=right_rom.rom_deg,
            diff_pct=diff_pct,
            severity=severity,
        )
    
    @classmethod
    def analyze_rom_deficit(cls, rom: JointROM, normal_min: float, 
                            normal_max: float) -> Optional[Dict]:
        """
        分析单个关节ROM是否低于常模
        返回None表示正常，否则返回受限信息
        """
        if rom.rom_deg <= 0:
            return None
        
        ratio = rom.rom_deg / normal_min
        
        if ratio >= cls.ROM_DEFICIT_MILD:
            return None
        
        if ratio < cls.ROM_DEFICIT_SEVERE:
            severity = "severe"
        elif ratio < cls.ROM_DEFICIT_MODERATE:
            severity = "moderate"
        else:
            severity = "mild"
        
        return {
            "joint": rom.joint,
            "side": rom.side,
            "rom_deg": rom.rom_deg,
            "normal_min": normal_min,
            "normal_max": normal_max,
            "ratio": round(ratio, 2),
            "severity": severity,
            "deficit_pct": round((1 - ratio) * 100, 1),
        }
    
    @classmethod
    def analyze_movement_result(cls, result: MovementROMResult,
                                 normal_ranges: Dict[str, Tuple[float, float]],
                                 muscle_mappings: Dict[str, Dict]) -> List[AsymmetryFinding]:
        """
        对整个动作的ROM结果进行完整分析
        normal_ranges: {joint_name: (min, max)}
        muscle_mappings: {joint_name: {tight: [...], weak: [...]}}
        返回不对称发现列表
        """
        findings = []
        
        # 按关节名分组，找左右配对
        roms_by_joint: Dict[str, Dict[str, JointROM]] = {}
        for rom in result.joint_roms:
            base = rom.joint.replace("left_", "").replace("right_", "")
            if base not in roms_by_joint:
                roms_by_joint[base] = {}
            roms_by_joint[base][rom.side] = rom
        
        for base, sides in roms_by_joint.items():
            if "left" in sides and "right" in sides:
                norm = normal_ranges.get(base, (60, 120))
                finding = cls.analyze_bilateral(sides["left"], sides["right"], norm[0], norm[1])
                if finding:
                    # 关联肌肉
                    mapping = muscle_mappings.get(base, {})
                    finding.related_muscles_tight = mapping.get("tight", [])
                    finding.related_muscles_weak = mapping.get("weak", [])
                    findings.append(finding)
        
        return findings
