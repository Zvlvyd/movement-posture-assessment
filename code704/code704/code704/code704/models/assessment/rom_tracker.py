# -*- coding: utf-8 -*-
"""
ROM 追踪引擎 - 接收逐帧关键点，追踪关节角度变化轨迹，识别ROM极限
"""
import time
from typing import Dict, List, Optional, Tuple
from dataclasses import dataclass, field
import numpy as np

from models.angle_calculator import AngleCalculator


@dataclass
class JointROM:
    """单个关节的ROM追踪结果"""
    joint: str                    # 关节名称
    side: str                     # left / right / bilateral
    angle_key: str                # AngleCalculator 键名
    rom_deg: float                # 运动范围（最大-最小）
    min_angle: float              # 运动中的最小角度
    max_angle: float              # 运动中的最大角度
    peak_angle: float             # 到达的最大角度（正方向）
    trajectory: List[float] = field(default_factory=list)  # 角度时间序列
    plateau_detected: bool = False  # 是否检测到平台期（ROM极限）
    frames_to_peak: int = 0       # 到达峰值所用帧数
    confidence: float = 1.0       # 关键点置信度加权平均


@dataclass
class MovementROMResult:
    """单个动作的完整ROM追踪结果"""
    movement_index: int
    movement_name: str
    joint_roms: List[JointROM] = field(default_factory=list)
    duration_seconds: float = 0.0
    total_frames: int = 0


class ROMTracker:
    """
    ROM 追踪引擎
    - 接收逐帧关键点，调用 AngleCalculator 获取实时角度
    - 对每个目标关节维护角度时间序列
    - 检测运动终点：角度变化率 < 阈值持续 N 帧 → 判定到达 ROM 极限
    """
    
    # 平台期检测参数
    PLATEAU_RATE_THRESHOLD = 0.3     # 角度变化率阈值 (度/帧)
    PLATEAU_FRAME_COUNT = 8          # 持续帧数
    
    def __init__(self):
        self.angle_calc = AngleCalculator()
        self.reset()
    
    def reset(self):
        """重置所有追踪状态"""
        self._angle_histories: Dict[str, List[float]] = {}  # angle_key -> [values]
        self._plateau_counters: Dict[str, int] = {}          # angle_key -> consecutive plateau frames
        self._peak_values: Dict[str, float] = {}             # angle_key -> peak value
        self._min_values: Dict[str, float] = {}              # angle_key -> min value
        self._frame_count: int = 0
        self._start_time: float = time.time()
        self._all_plateau_detected: bool = False
    
    def feed_keypoints(self, keypoints: np.ndarray) -> Dict[str, Optional[float]]:
        """
        输入一帧关键点，返回当前所有角度
        keypoints: (17, 2) 或 (17, 3) numpy 数组
        """
        self._frame_count += 1
        angles = self.angle_calc.compute_all_angles(keypoints)
        
        for key, value in angles.items():
            if value is None:
                continue
            
            if key not in self._angle_histories:
                self._angle_histories[key] = []
                self._plateau_counters[key] = 0
                self._peak_values[key] = value
                self._min_values[key] = value
            
            self._angle_histories[key].append(value)
            
            # 更新峰值和谷值
            if value > self._peak_values[key]:
                self._peak_values[key] = value
            if value < self._min_values[key]:
                self._min_values[key] = value
            
            # 平台期检测
            if len(self._angle_histories[key]) >= 2:
                prev = self._angle_histories[key][-2]
                delta = abs(value - prev)
                if delta < self.PLATEAU_RATE_THRESHOLD:
                    self._plateau_counters[key] += 1
                else:
                    self._plateau_counters[key] = 0
        
        return angles
    
    def is_all_plateau(self, target_keys: List[str]) -> bool:
        """检查所有目标角度是否都进入平台期"""
        if not target_keys:
            return self._frame_count > 60  # 无目标时至少跑60帧
        
        all_plateau = True
        for key in target_keys:
            if key not in self._plateau_counters:
                return False
            if self._plateau_counters[key] < self.PLATEAU_FRAME_COUNT:
                all_plateau = False
        
        # 至少需要一定帧数
        if self._frame_count < 20:
            return False
        
        return all_plateau
    
    def get_joint_rom(self, joint: str, side: str, angle_key: str) -> Optional[JointROM]:
        """获取指定关节的ROM追踪结果"""
        if angle_key not in self._angle_histories:
            return None
        
        history = self._angle_histories[angle_key]
        if len(history) < 2:
            return None
        
        min_val = self._min_values.get(angle_key, history[0])
        max_val = self._peak_values.get(angle_key, history[0])
        rom = max_val - min_val
        
        # 找到到达峰值的帧
        peak_frame = history.index(max_val) if max_val in history else len(history) - 1
        
        # 检测平台期
        plateau = (angle_key in self._plateau_counters and 
                   self._plateau_counters[angle_key] >= self.PLATEAU_FRAME_COUNT)
        
        return JointROM(
            joint=joint,
            side=side,
            angle_key=angle_key,
            rom_deg=round(rom, 1),
            min_angle=round(min_val, 1),
            max_angle=round(max_val, 1),
            peak_angle=round(max_val, 1),
            trajectory=[round(v, 1) for v in history],
            plateau_detected=plateau,
            frames_to_peak=peak_frame,
            confidence=0.85,  # 可从关键点置信度计算
        )
    
    def get_movement_result(self, movement_index: int, movement_name: str,
                            target_angle_keys: List[str],
                            joint_specs: List[Tuple[str, str, str]]) -> MovementROMResult:
        """
        生成动作的完整ROM追踪结果
        joint_specs: [(joint_name, side, angle_key), ...]
        """
        joint_roms = []
        for joint, side, angle_key in joint_specs:
            rom = self.get_joint_rom(joint, side, angle_key)
            if rom:
                joint_roms.append(rom)
        
        return MovementROMResult(
            movement_index=movement_index,
            movement_name=movement_name,
            joint_roms=joint_roms,
            duration_seconds=round(time.time() - self._start_time, 1),
            total_frames=self._frame_count,
        )
    
    def get_angle_history(self, angle_key: str) -> List[float]:
        """Expose raw angle trajectory for a specific key (needed by VelocityAnalyzer)."""
        return self._angle_histories.get(angle_key, [])

    def get_velocity_history(self, angle_key: str) -> List[float]:
        """
        Compute angular velocity from angle history using central difference.
        Convenience method for external velocity analysis.
        """
        history = self._angle_histories.get(angle_key, [])
        if len(history) < 3:
            return [0.0] * len(history)

        n = len(history)
        v = [0.0] * n
        v[0] = history[1] - history[0]
        for i in range(1, n - 1):
            v[i] = (history[i + 1] - history[i - 1]) / 2.0
        v[-1] = history[-1] - history[-2]
        return v

    def get_pair_histories(self, left_key: str, right_key: str) -> Tuple[List[float], List[float]]:
        """Get angle histories for a left-right joint pair (for VelocityAnalyzer)."""
        left = self._angle_histories.get(left_key, [])
        right = self._angle_histories.get(right_key, [])
        # Trim to same length
        min_len = min(len(left), len(right))
        return left[:min_len], right[:min_len]

    def get_current_angles_summary(self, target_keys: List[str]) -> Dict:
        """获取当前各目标角度的实时摘要（用于前端显示）"""
        summary = {}
        for key in target_keys:
            if key in self._angle_histories and self._angle_histories[key]:
                current = self._angle_histories[key][-1]
                peak = self._peak_values.get(key, current)
                plateau = (key in self._plateau_counters and 
                          self._plateau_counters[key] >= self.PLATEAU_FRAME_COUNT)
                summary[key] = {
                    'current': round(current, 1),
                    'peak': round(peak, 1),
                    'plateau': plateau,
                }
        return summary
