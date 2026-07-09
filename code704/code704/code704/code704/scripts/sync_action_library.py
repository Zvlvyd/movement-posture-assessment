# -*- coding: utf-8 -*-
"""Sync action library: apply 案例A (+10 actions) and 案例B (-20 actions) from work log."""
import json
import os

BASE = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))

# ── 20 actions to DELETE ─────────────────────────────────
DELETE_NAMES = [
    "收下巴（仰卧）", "收下巴（坐姿）", "婴儿式", "眼镜蛇式",
    "髋屈肌半跪拉伸", "仰卧腘绳肌拉伸", "侧卧股四头肌拉伸", "坐姿梨状肌拉伸",
    "颈部侧屈拉伸", "躯干旋转", "靠墙肩外旋", "膝盖侧平板", "标准侧平板",
    "单腿平板支撑", "俯卧撑位胸椎旋转", "深蹲位胸椎旋转", "单腿罗马尼亚硬拉",
    "侧平板抬腿", "单腿星形触地", "北欧腘绳肌弯举（辅助版）",
]

# ── 10 actions to ADD to action_library.json ─────────────
NEW_ACTION_LIBRARY = [
    {
        "id": "hh_006", "family": "hip_hinge", "family_name": "髋铰链", "family_name_en": "Hip Hinge",
        "name": "硬拉", "name_en": "Deadlift",
        "category": "下肢拉", "subcategory": "髋主导",
        "difficulty": 3, "intensity": "HIGH",
        "is_regression_of": None,
        "target_body_parts": ["臀大肌", "腘绳肌", "竖脊肌"],
        "contraindications": {"min_balance_score": 30, "min_flexibility_score": 30, "min_core_score": 40, "min_upper_limb_score": 0, "min_symmetry_score": 30},
        "problem_mapping": {"head_forward_posture": 0.1, "shoulder_imbalance": 0.0, "pelvic_lateral_tilt": 0.2, "possible_scoliosis": 0.0, "knee_hyperextension": 0.0, "pelvic_anterior_tilt": 0.7, "pelvic_posterior_tilt": 0.6},
        "phases": ["main"], "default_sets": 3, "default_reps": 10, "default_duration_seconds": 0,
        "description": "双脚与髋同宽，保持背部挺直，髋部后推发力拉起",
        "steps": ["1.双脚与髋同宽站立", "2.屈髋俯身", "3.背部挺直站起", "4.控制下放"],
        "cues": ["保持背部挺直", "髋部主导发力"],
        "display_type": "video", "display_url": "",
    },
    {
        "id": "hh_007", "family": "hip_hinge", "family_name": "髋铰链", "family_name_en": "Hip Hinge",
        "name": "罗马尼亚硬拉", "name_en": "Romanian Deadlift",
        "category": "下肢拉", "subcategory": "髋主导",
        "difficulty": 3, "intensity": "HIGH",
        "is_regression_of": None,
        "target_body_parts": ["腘绳肌", "臀大肌", "竖脊肌"],
        "contraindications": {"min_balance_score": 30, "min_flexibility_score": 35, "min_core_score": 40, "min_upper_limb_score": 0, "min_symmetry_score": 30},
        "problem_mapping": {"head_forward_posture": 0.1, "shoulder_imbalance": 0.0, "pelvic_lateral_tilt": 0.2, "possible_scoliosis": 0.0, "knee_hyperextension": 0.0, "pelvic_anterior_tilt": 0.7, "pelvic_posterior_tilt": 0.8},
        "phases": ["main"], "default_sets": 3, "default_reps": 10, "default_duration_seconds": 0,
        "description": "双腿直立微屈膝，髋部后推，杠铃沿腿前侧下放",
        "steps": ["1.双脚与髋同宽微屈膝", "2.髋部后推", "3.杠铃沿大腿下放", "4.髋部前推回位"],
        "cues": ["膝盖微屈保持", "髋部主导后移"],
        "display_type": "video", "display_url": "",
    },
    {
        "id": "bl_005", "family": "balance", "family_name": "平衡", "family_name_en": "Balance",
        "name": "前后脚掌重心转换", "name_en": "Heel Toe Rock",
        "category": "平衡", "subcategory": "重心控制",
        "difficulty": 1, "intensity": "LOW",
        "is_regression_of": None,
        "target_body_parts": ["踝关节", "足底固有肌"],
        "contraindications": {"min_balance_score": 0, "min_flexibility_score": 0, "min_core_score": 0, "min_upper_limb_score": 0, "min_symmetry_score": 0},
        "problem_mapping": {"head_forward_posture": 0.0, "shoulder_imbalance": 0.0, "pelvic_lateral_tilt": 0.0, "possible_scoliosis": 0.0, "knee_hyperextension": 0.0, "pelvic_anterior_tilt": 0.0, "pelvic_posterior_tilt": 0.0},
        "phases": ["warmup"], "default_sets": 3, "default_reps": 10, "default_duration_seconds": 0,
        "description": "站立位，缓慢将重心从脚跟转移到脚尖再返回",
        "steps": ["1.自然站立", "2.重心前移至脚尖", "3.重心后移至脚跟", "4.重复转移"],
        "cues": ["动作缓慢有控制", "保持身体平衡"],
        "display_type": "video", "display_url": "",
    },
    {
        "id": "st_011", "family": "stretch", "family_name": "拉伸", "family_name_en": "Stretch",
        "name": "髋部打开", "name_en": "Hip Opener",
        "category": "拉伸", "subcategory": "髋部",
        "difficulty": 1, "intensity": "LOW",
        "is_regression_of": None,
        "target_body_parts": ["髋内收肌", "髋关节"],
        "contraindications": {"min_balance_score": 0, "min_flexibility_score": 0, "min_core_score": 0, "min_upper_limb_score": 0, "min_symmetry_score": 0},
        "problem_mapping": {"head_forward_posture": 0.0, "shoulder_imbalance": 0.0, "pelvic_lateral_tilt": 0.3, "possible_scoliosis": 0.0, "knee_hyperextension": 0.0, "pelvic_anterior_tilt": 0.2, "pelvic_posterior_tilt": 0.2},
        "phases": ["warmup", "cooldown"], "default_sets": 2, "default_reps": 10, "default_duration_seconds": 30,
        "description": "坐姿，双腿屈膝向外打开（蝴蝶式），双手放膝上轻压",
        "steps": ["1.坐姿脚底相对", "2.双膝向外打开", "3.感受内侧拉伸", "4.保持30秒放松"],
        "cues": ["膝盖向外打开", "配合呼吸放松"],
        "display_type": "video", "display_url": "",
    },
    {
        "id": "jj_001", "family": "jumping_jack", "family_name": "开合跳", "family_name_en": "Jumping Jack",
        "name": "开合跳", "name_en": "Jumping Jack",
        "category": "热身", "subcategory": "全身",
        "difficulty": 1, "intensity": "MEDIUM",
        "is_regression_of": None,
        "target_body_parts": ["全身", "心肺"],
        "contraindications": {"min_balance_score": 30, "min_flexibility_score": 0, "min_core_score": 25, "min_upper_limb_score": 0, "min_symmetry_score": 0},
        "problem_mapping": {"head_forward_posture": 0.0, "shoulder_imbalance": 0.0, "pelvic_lateral_tilt": 0.0, "possible_scoliosis": 0.0, "knee_hyperextension": 0.0, "pelvic_anterior_tilt": 0.0, "pelvic_posterior_tilt": 0.0},
        "phases": ["warmup"], "default_sets": 3, "default_reps": 20, "default_duration_seconds": 0,
        "description": "双脚并拢站立，跳起分腿举手，落地并腿放手，保持节奏重复",
        "steps": ["1.双脚并拢站立", "2.跳起分腿举手", "3.落地并腿放手", "4.保持节奏重复"],
        "cues": ["核心收紧", "落地轻柔"],
        "display_type": "video", "display_url": "",
    },
    {
        "id": "sq_007", "family": "squat", "family_name": "深蹲", "family_name_en": "Squat",
        "name": "深弓步", "name_en": "Deep Lunge",
        "category": "下肢蹲", "subcategory": "单腿蹲",
        "difficulty": 3, "intensity": "HIGH",
        "is_regression_of": None,
        "target_body_parts": ["股四头肌", "臀大肌", "髋屈肌"],
        "contraindications": {"min_balance_score": 40, "min_flexibility_score": 35, "min_core_score": 35, "min_upper_limb_score": 0, "min_symmetry_score": 35},
        "problem_mapping": {"head_forward_posture": 0.0, "shoulder_imbalance": 0.0, "pelvic_lateral_tilt": 0.4, "possible_scoliosis": 0.2, "knee_hyperextension": 0.5, "pelvic_anterior_tilt": 0.5, "pelvic_posterior_tilt": 0.3},
        "phases": ["main"], "default_sets": 3, "default_reps": 8, "default_duration_seconds": 0,
        "description": "向前迈一大步，前腿膝盖弯曲大于90度，后腿膝盖接近地面",
        "steps": ["1.双脚并拢站立", "2.向前迈一大步", "3.下降至前膝大于90度", "4.前腿发力推回"],
        "cues": ["前膝不超脚尖", "躯干直立"],
        "display_type": "video", "display_url": "",
    },
    {
        "id": "st_012", "family": "stretch", "family_name": "拉伸", "family_name_en": "Stretch",
        "name": "小狗伸展式", "name_en": "Extended Puppy Pose",
        "category": "拉伸", "subcategory": "肩背",
        "difficulty": 1, "intensity": "LOW",
        "is_regression_of": None,
        "target_body_parts": ["背阔肌", "胸椎", "肩关节"],
        "contraindications": {"min_balance_score": 0, "min_flexibility_score": 0, "min_core_score": 0, "min_upper_limb_score": 0, "min_symmetry_score": 0},
        "problem_mapping": {"head_forward_posture": 0.0, "shoulder_imbalance": 0.5, "pelvic_lateral_tilt": 0.0, "possible_scoliosis": 0.0, "knee_hyperextension": 0.0, "pelvic_anterior_tilt": 0.0, "pelvic_posterior_tilt": 0.0},
        "phases": ["cooldown"], "default_sets": 2, "default_reps": 5, "default_duration_seconds": 30,
        "description": "四足跪姿，双手向前延伸，胸部下沉向地面",
        "steps": ["1.四足跪姿", "2.双手向前延伸", "3.胸部下沉", "4.保持30-60秒"],
        "cues": ["臀部保持在膝盖上方", "配合深呼吸"],
        "display_type": "video", "display_url": "",
    },
    {
        "id": "st_013", "family": "stretch", "family_name": "拉伸", "family_name_en": "Stretch",
        "name": "胸部打开", "name_en": "Chest Opener",
        "category": "拉伸", "subcategory": "胸部",
        "difficulty": 1, "intensity": "LOW",
        "is_regression_of": None,
        "target_body_parts": ["胸大肌", "胸小肌", "三角肌前束"],
        "contraindications": {"min_balance_score": 0, "min_flexibility_score": 0, "min_core_score": 0, "min_upper_limb_score": 0, "min_symmetry_score": 0},
        "problem_mapping": {"head_forward_posture": 0.5, "shoulder_imbalance": 0.6, "pelvic_lateral_tilt": 0.0, "possible_scoliosis": 0.1, "knee_hyperextension": 0.0, "pelvic_anterior_tilt": 0.0, "pelvic_posterior_tilt": 0.0},
        "phases": ["warmup", "cooldown"], "default_sets": 2, "default_reps": 10, "default_duration_seconds": 20,
        "description": "站立位，双手在背后交握，手臂向后上方抬起",
        "steps": ["1.站立双手背后交握", "2.手臂向后上抬", "3.挺胸感受拉伸", "4.保持20-30秒"],
        "cues": ["肩胛骨收紧", "不要耸肩"],
        "display_type": "video", "display_url": "",
    },
    {
        "id": "mo_009", "family": "warmup", "family_name": "热身", "family_name_en": "Warmup",
        "name": "侧卧胸椎旋转", "name_en": "Side-Lying Thoracic Rotation",
        "category": "拉伸", "subcategory": "胸椎",
        "difficulty": 1, "intensity": "LOW",
        "is_regression_of": None,
        "target_body_parts": ["胸椎", "背阔肌", "腹斜肌"],
        "contraindications": {"min_balance_score": 0, "min_flexibility_score": 0, "min_core_score": 0, "min_upper_limb_score": 0, "min_symmetry_score": 0},
        "problem_mapping": {"head_forward_posture": 0.3, "shoulder_imbalance": 0.4, "pelvic_lateral_tilt": 0.0, "possible_scoliosis": 0.3, "knee_hyperextension": 0.0, "pelvic_anterior_tilt": 0.0, "pelvic_posterior_tilt": 0.0},
        "phases": ["warmup"], "default_sets": 2, "default_reps": 8, "default_duration_seconds": 0,
        "description": "侧卧屈膝，双手前伸，上方手臂向对侧打开旋转",
        "steps": ["1.侧卧屈膝", "2.上方手臂打开旋转", "3.头部跟随手臂", "4.缓慢回位"],
        "cues": ["骨盆稳定", "眼随手走"],
        "display_type": "video", "display_url": "",
    },
    {
        "id": "st_014", "family": "stretch", "family_name": "拉伸", "family_name_en": "Stretch",
        "name": "肩部拉伸", "name_en": "Shoulder Stretch",
        "category": "拉伸", "subcategory": "肩部",
        "difficulty": 1, "intensity": "LOW",
        "is_regression_of": None,
        "target_body_parts": ["三角肌后束", "冈下肌", "菱形肌"],
        "contraindications": {"min_balance_score": 0, "min_flexibility_score": 0, "min_core_score": 0, "min_upper_limb_score": 0, "min_symmetry_score": 0},
        "problem_mapping": {"head_forward_posture": 0.3, "shoulder_imbalance": 0.6, "pelvic_lateral_tilt": 0.0, "possible_scoliosis": 0.0, "knee_hyperextension": 0.0, "pelvic_anterior_tilt": 0.0, "pelvic_posterior_tilt": 0.0},
        "phases": ["warmup", "cooldown"], "default_sets": 2, "default_reps": 8, "default_duration_seconds": 20,
        "description": "一侧手臂横过胸前，另一手辅助拉向身体",
        "steps": ["1.坐姿或站姿", "2.手臂横过胸前", "3.辅助拉近身体", "4.保持20-30秒换边"],
        "cues": ["肩膀放松下沉", "配合深呼吸"],
        "display_type": "video", "display_url": "",
    },
]

# ── 10 actions to ADD to standard_actions.json ───────────
NEW_STANDARD_ACTIONS = {
    "硬拉": {
        "name": "硬拉", "family": "hip_hinge", "family_name": "髋铰链",
        "category": "下肢拉",
        "description": "双脚与髋同宽，保持背部挺直，髋部后推发力拉起",
        "views": ["正面", "侧面"],
        "standard_keypoints": {
            "正面": {
                "description": "正面检查双膝对齐、脊柱中立",
                "target_angles": {
                    "left_knee": {"min": 140, "max": 180, "optimal": 160},
                    "right_knee": {"min": 140, "max": 180, "optimal": 160},
                    "left_hip": {"min": 50, "max": 110, "optimal": 80},
                    "right_hip": {"min": 50, "max": 110, "optimal": 80},
                },
                "key_checks": [
                    {"joint": "left_knee", "rule": "膝盖不内扣", "threshold": 10, "unit": "°", "direction": "deviation"},
                    {"joint": "right_knee", "rule": "膝盖不内扣", "threshold": 10, "unit": "°", "direction": "deviation"},
                ],
            },
            "侧面": {
                "description": "侧面检查背部挺直和髋铰链动作",
                "target_angles": {
                    "trunk_tilt": {"min": 30, "max": 90, "optimal": 60},
                    "left_hip": {"min": 40, "max": 100, "optimal": 70},
                    "right_hip": {"min": 40, "max": 100, "optimal": 70},
                },
                "key_checks": [
                    {"joint": "trunk_tilt", "rule": "背部不弓起", "threshold": 90, "unit": "°", "direction": "max"},
                ],
            },
        },
        "common_errors": [
            {"name": "背部弓起", "feedback": "背部弓起{value}°，请保持背部挺直", "joint": "trunk_tilt", "threshold": 90},
        ],
    },
    "罗马尼亚硬拉": {
        "name": "罗马尼亚硬拉", "family": "hip_hinge", "family_name": "髋铰链",
        "category": "下肢拉",
        "description": "双腿直立微屈膝，髋部后推，杠铃沿腿前侧下放",
        "views": ["正面", "侧面"],
        "standard_keypoints": {
            "正面": {
                "description": "正面检查双膝对齐",
                "target_angles": {
                    "left_knee": {"min": 150, "max": 180, "optimal": 170},
                    "right_knee": {"min": 150, "max": 180, "optimal": 170},
                    "left_hip": {"min": 60, "max": 110, "optimal": 85},
                    "right_hip": {"min": 60, "max": 110, "optimal": 85},
                },
                "key_checks": [
                    {"joint": "left_knee", "rule": "膝盖不内扣", "threshold": 10, "unit": "°", "direction": "deviation"},
                ],
            },
            "侧面": {
                "description": "侧面检查髋部后推幅度",
                "target_angles": {
                    "trunk_tilt": {"min": 40, "max": 90, "optimal": 70},
                    "left_hip": {"min": 50, "max": 100, "optimal": 75},
                },
                "key_checks": [
                    {"joint": "trunk_tilt", "rule": "背部挺直不屈曲", "threshold": 90, "unit": "°", "direction": "max"},
                ],
            },
        },
        "common_errors": [
            {"name": "膝盖过度弯曲", "feedback": "膝盖弯曲过多{value}°，请保持微屈", "joint": "knee", "threshold": 150},
        ],
    },
    "前后脚掌重心转换": {
        "name": "前后脚掌重心转换", "family": "balance", "family_name": "平衡",
        "category": "平衡",
        "description": "站立位，缓慢将重心从脚跟转移到脚尖再返回",
        "views": ["侧面"],
        "standard_keypoints": {
            "侧面": {
                "description": "侧面检查躯干稳定性和重心偏移",
                "target_angles": {
                    "trunk_tilt": {"min": 0, "max": 10, "optimal": 3},
                    "left_knee": {"min": 170, "max": 180, "optimal": 180},
                    "right_knee": {"min": 170, "max": 180, "optimal": 180},
                },
                "key_checks": [
                    {"joint": "trunk_tilt", "rule": "躯干保持直立", "threshold": 10, "unit": "°", "direction": "max"},
                ],
            },
        },
        "common_errors": [
            {"name": "躯干过度前倾", "feedback": "躯干前倾{value}°，请保持直立", "joint": "trunk_tilt", "threshold": 10},
        ],
    },
    "髋部打开": {
        "name": "髋部打开", "family": "stretch", "family_name": "拉伸",
        "category": "拉伸",
        "description": "坐姿，双腿屈膝向外打开（蝴蝶式），双手放膝上轻压",
        "views": ["正面"],
        "standard_keypoints": {
            "正面": {
                "description": "正面检查髋部外展幅度",
                "target_angles": {
                    "left_hip": {"min": 30, "max": 90, "optimal": 60},
                    "right_hip": {"min": 30, "max": 90, "optimal": 60},
                    "left_knee": {"min": 30, "max": 100, "optimal": 60},
                    "right_knee": {"min": 30, "max": 100, "optimal": 60},
                },
                "key_checks": [
                    {"joint": "left_hip", "rule": "髋部打开幅度充足", "threshold": 30, "unit": "°", "direction": "min"},
                ],
            },
        },
        "common_errors": [],
    },
    "开合跳": {
        "name": "开合跳", "family": "jumping_jack", "family_name": "开合跳",
        "category": "热身",
        "description": "双脚并拢站立，跳起分腿举手，落地并腿放手，保持节奏重复",
        "views": ["正面"],
        "standard_keypoints": {
            "正面": {
                "description": "正面检查四肢协调",
                "target_angles": {
                    "left_hip": {"min": 10, "max": 60, "optimal": 30},
                    "right_hip": {"min": 10, "max": 60, "optimal": 30},
                    "left_shoulder": {"min": 10, "max": 90, "optimal": 45},
                    "right_shoulder": {"min": 10, "max": 90, "optimal": 45},
                },
                "key_checks": [
                    {"joint": "left_shoulder", "rule": "手臂充分展开", "threshold": 10, "unit": "°", "direction": "min"},
                ],
            },
        },
        "common_errors": [
            {"name": "手臂未充分展开", "feedback": "手臂展开不足，请举至头顶", "joint": "shoulder", "threshold": 30},
        ],
    },
    "深弓步": {
        "name": "深弓步", "family": "squat", "family_name": "深蹲",
        "category": "下肢蹲",
        "description": "向前迈一大步，前腿膝盖弯曲大于90度，后腿膝盖接近地面",
        "views": ["侧面"],
        "standard_keypoints": {
            "侧面": {
                "description": "侧面检查前膝角度和躯干直立",
                "target_angles": {
                    "left_knee": {"min": 80, "max": 120, "optimal": 100},
                    "right_knee": {"min": 80, "max": 120, "optimal": 100},
                    "left_hip": {"min": 70, "max": 120, "optimal": 95},
                    "trunk_tilt": {"min": 0, "max": 30, "optimal": 10},
                },
                "key_checks": [
                    {"joint": "left_knee", "rule": "前膝不超脚尖", "threshold": 120, "unit": "°", "direction": "max"},
                    {"joint": "trunk_tilt", "rule": "躯干保持直立", "threshold": 30, "unit": "°", "direction": "max"},
                ],
            },
        },
        "common_errors": [
            {"name": "躯干过度前倾", "feedback": "躯干前倾{value}°，请保持直立", "joint": "trunk_tilt", "threshold": 30},
        ],
    },
    "小狗伸展式": {
        "name": "小狗伸展式", "family": "stretch", "family_name": "拉伸",
        "category": "拉伸",
        "description": "四足跪姿，双手向前延伸，胸部下沉向地面",
        "views": ["侧面"],
        "standard_keypoints": {
            "侧面": {
                "description": "侧面检查肩部伸展幅度",
                "target_angles": {
                    "left_shoulder": {"min": 120, "max": 180, "optimal": 160},
                    "right_shoulder": {"min": 120, "max": 180, "optimal": 160},
                    "trunk_tilt": {"min": 10, "max": 60, "optimal": 30},
                },
                "key_checks": [
                    {"joint": "left_shoulder", "rule": "肩部充分伸展", "threshold": 120, "unit": "°", "direction": "min"},
                ],
            },
        },
        "common_errors": [
            {"name": "臀部未保持位置", "feedback": "臀部前移过多，请保持在膝盖上方", "joint": "hip", "threshold": 10},
        ],
    },
    "胸部打开": {
        "name": "胸部打开", "family": "stretch", "family_name": "拉伸",
        "category": "拉伸",
        "description": "站立位，双手在背后交握，手臂向后上方抬起",
        "views": ["正面"],
        "standard_keypoints": {
            "正面": {
                "description": "正面检查手臂后展幅度",
                "target_angles": {
                    "left_shoulder": {"min": 10, "max": 60, "optimal": 30},
                    "right_shoulder": {"min": 10, "max": 60, "optimal": 30},
                    "left_elbow": {"min": 150, "max": 180, "optimal": 170},
                    "right_elbow": {"min": 150, "max": 180, "optimal": 170},
                },
                "key_checks": [
                    {"joint": "left_shoulder", "rule": "手臂充分后展", "threshold": 10, "unit": "°", "direction": "min"},
                ],
            },
        },
        "common_errors": [
            {"name": "耸肩", "feedback": "侦测到耸肩，请肩膀下沉", "joint": "shoulder", "threshold": 5},
        ],
    },
    "侧卧胸椎旋转": {
        "name": "侧卧胸椎旋转", "family": "warmup", "family_name": "热身",
        "category": "拉伸",
        "description": "侧卧屈膝，双手前伸，上方手臂向对侧打开旋转",
        "views": ["正面"],
        "standard_keypoints": {
            "正面": {
                "description": "正面检查手臂打开幅度和旋转范围",
                "target_angles": {
                    "left_shoulder": {"min": 10, "max": 120, "optimal": 90},
                    "right_shoulder": {"min": 10, "max": 120, "optimal": 90},
                },
                "key_checks": [
                    {"joint": "left_shoulder", "rule": "手臂旋转幅度充足", "threshold": 10, "unit": "°", "direction": "min"},
                ],
            },
        },
        "common_errors": [
            {"name": "骨盆跟随旋转", "feedback": "骨盆跟随旋转过多，请保持骨盆稳定", "joint": "hip", "threshold": 10},
        ],
    },
    "肩部拉伸": {
        "name": "肩部拉伸", "family": "stretch", "family_name": "拉伸",
        "category": "拉伸",
        "description": "一侧手臂横过胸前，另一手辅助拉向身体",
        "views": ["正面"],
        "standard_keypoints": {
            "正面": {
                "description": "正面检查肩部拉伸幅度",
                "target_angles": {
                    "left_shoulder": {"min": 10, "max": 60, "optimal": 30},
                    "right_shoulder": {"min": 10, "max": 60, "optimal": 30},
                    "left_elbow": {"min": 120, "max": 180, "optimal": 150},
                    "right_elbow": {"min": 120, "max": 180, "optimal": 150},
                },
                "key_checks": [
                    {"joint": "left_shoulder", "rule": "手臂靠近身体", "threshold": 60, "unit": "°", "direction": "max"},
                ],
            },
        },
        "common_errors": [
            {"name": "肩膀耸起", "feedback": "拉伸侧肩膀耸起，请放松下沉", "joint": "shoulder", "threshold": 5},
        ],
    },
}


def main():
    # ── 1. Update action_library.json ────────────────────
    lib_path = os.path.join(BASE, "models", "prescription_v2", "action_library.json")
    with open(lib_path, "r", encoding="utf-8") as f:
        lib = json.load(f)

    old_count = len(lib["actions"])
    # Remove deleted actions
    lib["actions"] = [a for a in lib["actions"] if a["name"] not in DELETE_NAMES]
    removed = old_count - len(lib["actions"])
    print(f"action_library.json: removed {removed} actions ({old_count} -> {len(lib['actions'])})")

    # Add new actions
    existing_names = {a["name"] for a in lib["actions"]}
    for new_a in NEW_ACTION_LIBRARY:
        if new_a["name"] not in existing_names:
            lib["actions"].append(new_a)
            print(f"  + added: {new_a['name']}")
        else:
            print(f"  - skipped (already exists): {new_a['name']}")

    # Sort by id for consistency
    # lib["actions"].sort(key=lambda a: a["id"])

    with open(lib_path, "w", encoding="utf-8") as f:
        json.dump(lib, f, ensure_ascii=False, indent=2)
    print(f"action_library.json: final count = {len(lib['actions'])}")

    # ── 2. Update standard_actions.json ──────────────────
    std_path = os.path.join(BASE, "models", "knowledge", "standard_actions.json")
    with open(std_path, "r", encoding="utf-8") as f:
        std = json.load(f)

    old_count = len(std["actions"])
    # Remove deleted actions
    for name in DELETE_NAMES:
        if name in std["actions"]:
            del std["actions"][name]
    removed = old_count - len(std["actions"])
    print(f"\nstandard_actions.json: removed {removed} actions ({old_count} -> {len(std['actions'])})")

    # Add new standard actions
    for name, entry in NEW_STANDARD_ACTIONS.items():
        if name not in std["actions"]:
            std["actions"][name] = entry
            print(f"  + added: {name}")
        else:
            print(f"  - skipped (already exists): {name}")

    # Update meta
    std["_meta"]["total_actions"] = len(std["actions"])
    # Remove "updated" key if present
    if "updated" in std.get("_meta", {}):
        del std["_meta"]["updated"]

    with open(std_path, "w", encoding="utf-8") as f:
        json.dump(std, f, ensure_ascii=False, indent=2)
    print(f"standard_actions.json: final count = {len(std['actions'])}")

    print("\n✅ Sync complete!")


if __name__ == "__main__":
    main()
