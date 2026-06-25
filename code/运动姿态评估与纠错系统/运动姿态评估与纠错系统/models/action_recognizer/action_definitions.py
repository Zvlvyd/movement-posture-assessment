from typing import Dict, Any, List

class ActionDefinition:
    def __init__(self, name: str, category: str, target_joint: str, 
                 min_angle: float, max_angle: float, danger_thresholds: Dict[str, Any],
                 advanced_thresholds: Dict[str, Any] = None):
        self.name = name
        self.category = category
        self.target_joint = target_joint
        self.min_angle = min_angle
        self.max_angle = max_angle
        self.danger_thresholds = danger_thresholds
        self.advanced_thresholds = advanced_thresholds or danger_thresholds

# Standard action definitions
ACTION_DEFINITIONS: Dict[str, ActionDefinition] = {
    'squat': ActionDefinition(
        name='深蹲',
        category='下肢',
        target_joint='knee',
        min_angle=70.0,
        max_angle=160.0,
        danger_thresholds={
            'knee_valgus': 15.0,
            'trunk_forward': 45.0,
            'heel_lift': 0.1,
        },
        advanced_thresholds={
            'knee_valgus': 10.0,
            'trunk_forward': 30.0,
            'heel_lift': 0.05,
            'knee_toe_align': 10.0,
            'depth_symmetry': 10.0,
        }
    ),
    'lunge': ActionDefinition(
        name='弓步蹲',
        category='下肢',
        target_joint='knee',
        min_angle=70.0,
        max_angle=170.0,
        danger_thresholds={
            'knee_valgus': 15.0,
            'trunk_forward': 45.0,
        },
        advanced_thresholds={
            'knee_valgus': 10.0,
            'trunk_forward': 30.0,
            'front_knee_over_toe': 5.0,
        }
    ),
    'pushup': ActionDefinition(
        name='俯卧撑',
        category='上肢',
        target_joint='elbow',
        min_angle=70.0,
        max_angle=170.0,
        danger_thresholds={
            'hip_sag': 20.0,
            'elbow_flare': 45.0,
        },
        advanced_thresholds={
            'hip_sag': 10.0,
            'elbow_flare': 30.0,
            'depth_symmetry': 10.0,
        }
    ),
    'plank': ActionDefinition(
        name='平板支撑',
        category='核心',
        target_joint='hip',
        min_angle=160.0,
        max_angle=180.0,
        danger_thresholds={
            'hip_sag': 15.0,
            'hip_pike': 15.0,
        },
        advanced_thresholds={
            'hip_sag': 8.0,
            'hip_pike': 8.0,
            'shoulder_protraction': 5.0,
        }
    ),
    'shoulder_press': ActionDefinition(
        name='肩推',
        category='上肢',
        target_joint='elbow',
        min_angle=80.0,
        max_angle=180.0,
        danger_thresholds={
            'shoulder_shrug': 10.0,
            'back_arch': 15.0,
        },
        advanced_thresholds={
            'shoulder_shrug': 5.0,
            'back_arch': 8.0,
            'arm_symmetry': 10.0,
        }
    ),
}

def get_action_definition(action_name: str) -> ActionDefinition:
    key = action_name.lower()
    if key in ACTION_DEFINITIONS:
        return ACTION_DEFINITIONS[key]
    # Default fallback
    return ActionDefinition(
        name=action_name,
        category='general',
        target_joint='knee',
        min_angle=70.0,
        max_angle=170.0,
        danger_thresholds={},
    )
