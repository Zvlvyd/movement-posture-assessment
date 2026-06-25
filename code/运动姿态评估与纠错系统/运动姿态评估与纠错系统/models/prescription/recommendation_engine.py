from typing import List, Dict, Optional
from dataclasses import dataclass, field
from enum import Enum
import random

class Phase(str, Enum):
    WARMUP = 'warmup'
    ACTIVATION = 'activation'
    MAIN = 'main'
    COOLDOWN = 'cooldown'

@dataclass
class ActionItem:
    name: str
    phase: Phase
    sets: int = 3
    reps: int = 10
    duration_seconds: int = 0
    difficulty: int = 1
    tags: List[str] = field(default_factory=list)
    description: str = ''

# Built-in action library
ACTION_LIBRARY = [
    ActionItem('关节绕环', Phase.WARMUP, 1, 10, 0, 1, ['general'], '活动全身关节'),
    ActionItem('高抬腿', Phase.WARMUP, 2, 20, 0, 1, ['general'], '提升心率'),
    ActionItem('开合跳', Phase.WARMUP, 2, 15, 0, 1, ['general'], '全身热身'),
    ActionItem('臀桥', Phase.ACTIVATION, 3, 12, 0, 2, ['core', 'balance'], '激活臀肌和核心'),
    ActionItem('鸟狗式', Phase.ACTIVATION, 3, 10, 0, 2, ['core', 'balance'], '核心稳定训练'),
    ActionItem('弹力带侧走', Phase.ACTIVATION, 3, 12, 0, 2, ['core', 'balance'], '激活髋外展肌'),
    ActionItem('箱式深蹲', Phase.MAIN, 3, 12, 0, 2, ['flexibility', 'balance'], '控制深蹲幅度'),
    ActionItem('徒手深蹲', Phase.MAIN, 3, 15, 0, 3, ['flexibility', 'balance'], '标准深蹲训练'),
    ActionItem('弓步蹲', Phase.MAIN, 3, 10, 0, 3, ['symmetry', 'balance'], '下肢对称性训练'),
    ActionItem('单腿硬拉', Phase.MAIN, 3, 10, 0, 3, ['balance', 'core'], '平衡与后链训练'),
    ActionItem('墙壁天使', Phase.MAIN, 3, 12, 0, 2, ['upper_limb'], '肩关节活动度训练'),
    ActionItem('弹力带拉开', Phase.MAIN, 3, 12, 0, 2, ['upper_limb'], '肩袖肌群训练'),
    ActionItem('俯卧撑', Phase.MAIN, 3, 10, 0, 3, ['upper_limb', 'core'], '上肢力量训练'),
    ActionItem('平板支撑', Phase.MAIN, 3, 1, 30, 3, ['core'], '核心耐力训练'),
    ActionItem('死虫式', Phase.MAIN, 3, 10, 0, 2, ['core'], '核心控制训练'),
    ActionItem('侧平板', Phase.MAIN, 3, 1, 20, 3, ['core'], '侧向核心训练'),
    ActionItem('静态拉伸-股四头肌', Phase.COOLDOWN, 2, 1, 30, 1, ['general'], '拉伸放松'),
    ActionItem('静态拉伸-腘绳肌', Phase.COOLDOWN, 2, 1, 30, 1, ['general'], '拉伸放松'),
    ActionItem('静态拉伸-胸肌', Phase.COOLDOWN, 2, 1, 30, 1, ['general'], '拉伸放松'),
    ActionItem('静态拉伸-肩部', Phase.COOLDOWN, 2, 1, 30, 1, ['upper_limb'], '肩部拉伸'),
    ActionItem('婴儿式放松', Phase.COOLDOWN, 1, 1, 60, 1, ['general'], '全身放松'),
]

class PrescriptionEngine:
    CYCLE_INTENSITY_MAP = {
        'menstrual': 0.6,
        'follicular': 0.9,
        'ovulation': 1.0,
        'luteal': 0.8,
    }
    
    @classmethod
    def generate(cls, problem_tags: List[Dict], difficulty: int = 1, 
                 cycle_phase: Optional[str] = None) -> Dict:
        tag_names = [t['name'] for t in problem_tags]
        dimension_set = set(t.get('dimension', '') for t in problem_tags)
        
        intensity = 1.0
        if cycle_phase and cycle_phase in cls.CYCLE_INTENSITY_MAP:
            intensity = cls.CYCLE_INTENSITY_MAP[cycle_phase]
        
        warmup = cls._select_phase(Phase.WARMUP, difficulty, set(tag_names), count=3)
        activation = cls._select_phase(Phase.ACTIVATION, difficulty, dimension_set, count=2)
        main = cls._select_phase(Phase.MAIN, difficulty, dimension_set, count=4)
        cooldown = cls._select_phase(Phase.COOLDOWN, difficulty, set(tag_names), count=2)
        
        all_items = warmup + activation + main + cooldown
        for i, item in enumerate(all_items):
            item['order_index'] = i + 1
            if intensity < 1.0 and item['phase'] == Phase.MAIN.value:
                item['difficulty'] = max(1, int(item['difficulty'] * intensity))
                item['reps'] = max(5, int(item['reps'] * intensity))
        
        return {
            'difficulty': difficulty,
            'phase_number': difficulty,
            'status': 'active',
            'intensity_coefficient': intensity,
            'cycle_phase': cycle_phase,
            'items': all_items,
        }
    
    @classmethod
    def _select_phase(cls, phase: Phase, difficulty: int, 
                      target_tags: set, count: int = 3) -> List[Dict]:
        candidates = [a for a in ACTION_LIBRARY if a.phase == phase]
        scored = []
        for a in candidates:
            overlap = len(set(a.tags) & target_tags)
            scored.append((overlap, len(set(a.tags) & {'general'}) > 0, a))
        
        scored.sort(key=lambda x: (-x[0], x[1]))
        selected = scored[:count * 2]
        random.shuffle(selected)
        result = []
        for _, _, a in selected[:count]:
            result.append({
                'name': a.name,
                'phase': a.phase.value,
                'sets': a.sets,
                'reps': a.reps,
                'duration': a.duration_seconds,
                'difficulty': a.difficulty,
                'description': a.description,
            })
        return result
    
    @classmethod
    def should_unlock_next(cls, current_phase: int, training_count: int, 
                           overall_score: float) -> bool:
        if current_phase >= 5:
            return False
        thresholds = {1: 3, 2: 5, 3: 7, 4: 10}
        return training_count >= thresholds.get(current_phase, 10) and overall_score >= 60.0
