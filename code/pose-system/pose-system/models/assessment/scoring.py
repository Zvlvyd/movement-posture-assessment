# -*- coding: utf-8 -*-
"""
统一评分引擎 - 将ROM测量值映射到5维度评分体系
替代旧的 models/fms/scoring.py
"""
import json
import math
import os
from pathlib import Path
from typing import Dict, List, Optional, Tuple
from dataclasses import dataclass, field

from .rom_tracker import MovementROMResult, JointROM


@dataclass
class DimensionScore:
    """单个维度的评分结果"""
    dimension: str                # balance/flexibility/upper_limb/core/symmetry
    label: str                    # 中文标签
    score: float                  # 0-100
    max_score: float = 100.0
    details: List[str] = field(default_factory=list)
    contributing_joints: List[str] = field(default_factory=list)


class UnifiedScoringEngine:
    """
    统一评分引擎
    将 ROM 测量值映射到 5 维度：balance, flexibility, upper_limb, core, symmetry
    每维度评分基于与 rom_norms.json 中常模数据的偏差百分比
    """
    
    DIMENSION_LABELS = {
        'balance': '平衡',
        'flexibility': '灵活性',
        'upper_limb': '上肢',
        'core': '核心',
        'symmetry': '对称性',
    }
    
    WEIGHTS = {
        'balance': 0.20,
        'flexibility': 0.25,
        'upper_limb': 0.15,
        'core': 0.20,
        'symmetry': 0.20,
    }
    
    def __init__(self, norms_path: Optional[str] = None):
        """
        norms_path: rom_norms.json 路径，默认从 knowledge 目录加载
        """
        if norms_path is None:
            norms_path = Path(__file__).parent.parent / "knowledge" / "rom_norms.json"
        
        self.norms = self._load_norms(norms_path)
    
    def _load_norms(self, path) -> Dict:
        """加载常模数据"""
        if os.path.exists(str(path)):
            with open(str(path), "r", encoding="utf-8") as f:
                return json.load(f)
        return {}
    
    def _score_from_ratio(self, ratio: float) -> float:
        """
        将 ROM与常模的比值 转换为 0-100 分数
        ratio: 实测ROM / 常模最小值
        ratio >= 1.0  → 100分
        ratio >= 0.8  → 80-99分
        ratio >= 0.6  → 50-79分
        ratio <  0.6  → 线性衰减
        """
        if ratio >= 1.0:
            return 100.0
        elif ratio >= 0.8:
            return 80.0 + (ratio - 0.8) / 0.2 * 20.0
        elif ratio >= 0.6:
            return 50.0 + (ratio - 0.6) / 0.2 * 30.0
        else:
            return max(0.0, ratio / 0.6 * 50.0)
    
    def score_balance(self, movement_results: List[MovementROMResult],
                      posture_flags: List[str]) -> DimensionScore:
        """
        平衡维度评分
        - 静态姿态：头部倾斜、脊柱侧偏等指标
        - 动态：单腿稳定时各关节的稳定性
        """
        # 从姿态标记推断平衡
        balance_flags = {'shoulder_imbalance', 'pelvic_lateral_tilt', 'possible_scoliosis'}
        flag_penalty = sum(15 for f in posture_flags if f in balance_flags)
        
        # 从深蹲动作看平衡（动作3）
        knee_sym_score = 100.0
        for result in movement_results:
            if result.movement_index == 3:  # 深蹲
                knees = [r for r in result.joint_roms if 'knee' in r.joint]
                if len(knees) >= 2:
                    left = next((r for r in knees if r.side == 'left'), None)
                    right = next((r for r in knees if r.side == 'right'), None)
                    if left and right and max(left.rom_deg, right.rom_deg) > 0:
                        diff = abs(left.rom_deg - right.rom_deg)
                        knee_sym_score = max(0, 100 - diff * 3)
        
        score = max(0, (knee_sym_score * 0.6 + (100 - flag_penalty) * 0.4))
        
        return DimensionScore(
            dimension='balance',
            label='平衡',
            score=round(score, 1),
            details=[f"姿态对称性: {100 - flag_penalty:.0f}分", f"深蹲膝对称: {knee_sym_score:.0f}分"],
            contributing_joints=['spine_lateral', 'shoulder_height', 'hip_height', 'knee_symmetry'],
        )
    
    def score_flexibility(self, movement_results: List[MovementROMResult]) -> DimensionScore:
        """
        灵活性维度评分
        各关节 ROM 与常模比值的加权平均
        """
        ratios = []
        details = []
        
        for result in movement_results:
            for rom in result.joint_roms:
                norm = self.norms.get(rom.joint, {})
                min_norm = norm.get("min", 60)
                
                if rom.rom_deg > 0 and min_norm > 0:
                    ratio = rom.rom_deg / min_norm
                    ratios.append(min(ratio, 1.5))  # 上限1.5倍常模
                    score = self._score_from_ratio(ratio)
                    details.append(f"{rom.joint}({rom.side}): {rom.rom_deg}°/{min_norm}° → {score:.0f}分")
        
        if not ratios:
            return DimensionScore(dimension='flexibility', label='灵活性', score=50.0, details=['无ROM数据'])
        
        avg_score = sum(self._score_from_ratio(r) for r in ratios) / len(ratios)
        
        return DimensionScore(
            dimension='flexibility',
            label='灵活性',
            score=round(avg_score, 1),
            details=details,
            contributing_joints=[r.joint for result in movement_results for r in result.joint_roms],
        )
    
    def score_upper_limb(self, movement_results: List[MovementROMResult],
                         posture_flags: List[str]) -> DimensionScore:
        """
        上肢维度评分
        肩关节 ROM + 颈椎 ROM + 上肢左右对称性
        """
        scores = []
        details = []
        joints = []
        
        for result in movement_results:
            if result.movement_index in [0, 1]:  # 颈部和肩部
                for rom in result.joint_roms:
                    norm = self.norms.get(rom.joint, {})
                    min_norm = norm.get("min", 60)
                    if rom.rom_deg > 0 and min_norm > 0:
                        ratio = rom.rom_deg / min_norm
                        s = self._score_from_ratio(ratio)
                        scores.append(s)
                        details.append(f"{rom.joint}({rom.side}): {rom.rom_deg}°/{min_norm}° → {s:.0f}分")
                        joints.append(rom.joint)
        
        # 肩对称性
        if 'shoulder_imbalance' in posture_flags:
            scores.append(40)
            details.append("肩部不对称: -60分")
        
        if not scores:
            return DimensionScore(dimension='upper_limb', label='上肢', score=50.0, details=['无上肢数据'])
        
        avg_score = sum(scores) / len(scores)
        return DimensionScore(
            dimension='upper_limb', label='上肢',
            score=round(avg_score, 1), details=details, contributing_joints=joints,
        )
    
    def score_core(self, movement_results: List[MovementROMResult],
                   posture_flags: List[str]) -> DimensionScore:
        """
        核心维度评分
        深蹲时躯干前倾角、体前屈时骨盆控制
        """
        scores = []
        details = []
        
        for result in movement_results:
            if result.movement_index in [2, 3]:  # 脊柱和深蹲
                for rom in result.joint_roms:
                    if 'trunk' in rom.joint or 'hip' in rom.joint:
                        norm = self.norms.get(rom.joint, {})
                        min_norm = norm.get("min", 60)
                        if rom.rom_deg > 0 and min_norm > 0:
                            ratio = rom.rom_deg / min_norm
                            s = self._score_from_ratio(ratio)
                            scores.append(s)
                            details.append(f"{rom.joint}: {rom.rom_deg}°/{min_norm}° → {s:.0f}分")
        
        # 骨盆前倾
        if 'pelvic_anterior_tilt' in posture_flags:
            scores.append(40)
            details.append("骨盆前倾: 核心控制不足 -60分")
        
        if not scores:
            return DimensionScore(dimension='core', label='核心', score=50.0, details=['无核心数据'])
        
        avg_score = sum(scores) / len(scores)
        return DimensionScore(
            dimension='core', label='核心',
            score=round(avg_score, 1), details=details,
            contributing_joints=['trunk_tilt', 'hip_flexion'],
        )
    
    def score_symmetry(self, movement_results: List[MovementROMResult],
                       posture_flags: List[str],
                       asymmetry_findings: List) -> DimensionScore:
        """
        对称性维度评分
        所有双侧动作的左右 ROM 差异综合评分
        """
        details = []
        total_penalty = 0
        
        for finding in asymmetry_findings:
            # Handle both dict and dataclass/object types
            if isinstance(finding, dict):
                diff = finding.get('diff_pct', 0)
                joint = finding.get('joint', 'unknown')
            else:
                diff = getattr(finding, 'diff_pct', 0)
                joint = getattr(finding, 'joint', 'unknown')
            if diff >= 35:
                penalty = 30
                details.append(f"{joint}: 偏差{diff}% (严重) -{penalty}分")
            elif diff >= 20:
                penalty = 15
                details.append(f"{joint}: 偏差{diff}% (中度) -{penalty}分")
            elif diff >= 10:
                penalty = 8
                details.append(f"{joint}: 偏差{diff}% (轻度) -{penalty}分")
            else:
                penalty = 0
            total_penalty += penalty
        
        # 姿态对称标记
        sym_flags = {'shoulder_imbalance', 'pelvic_lateral_tilt', 'possible_scoliosis'}
        flag_penalty = sum(10 for f in posture_flags if f in sym_flags)
        
        score = max(0, 100 - total_penalty - flag_penalty)
        
        if not details:
            details.append("左右对称性良好")
        
        return DimensionScore(
            dimension='symmetry', label='对称性',
            score=round(score, 1), details=details, contributing_joints=[],
        )
    
    def compute_all(self, movement_results: List[MovementROMResult],
                    posture_flags: List[str],
                    asymmetry_findings: List) -> List[DimensionScore]:
        """计算所有5维度的评分"""
        return [
            self.score_balance(movement_results, posture_flags),
            self.score_flexibility(movement_results),
            self.score_upper_limb(movement_results, posture_flags),
            self.score_core(movement_results, posture_flags),
            self.score_symmetry(movement_results, posture_flags, asymmetry_findings),
        ]
    
    def compute_overall(self, scores: List[DimensionScore]) -> float:
        """计算加权总分"""
        total = sum(s.score * self.WEIGHTS.get(s.dimension, 0.2) for s in scores)
        return round(total, 1)
    
    def get_risk_level(self, overall_score: float, scores: List[DimensionScore]) -> str:
        """根据总分和单项分判定风险等级"""
        if overall_score < 40 or any(s.score < 30 for s in scores):
            return 'high'
        elif overall_score < 70 or any(s.score < 50 for s in scores):
            return 'medium'
        return 'low'
