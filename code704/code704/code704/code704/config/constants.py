"""
Hardcoded application constants extracted from business logic.
Centralized here to reduce merge conflicts during team development.
"""

# ── Scoring Weights (UnifiedScoringEngine) ──────────────
DIMENSION_WEIGHTS: dict = {
    "balance": 0.20,
    "flexibility": 0.25,
    "upper_limb": 0.15,
    "core": 0.20,
    "symmetry": 0.20,
}

RATIO_THRESHOLDS: dict = {
    "excellent": 1.0,   # ratio >= 1.0 → 100 points
    "good": 0.8,        # ratio >= 0.8 → 80-99
    "fair": 0.6,        # ratio >= 0.6 → 50-79
}

# ── Velocity Analysis Defaults ──────────────────────────
VELOCITY_DEFAULTS: dict = {
    "diff_threshold_pct": 20.0,
    "sustained_frame_count": 15,
    "min_peak_velocity": 0.5,
    "severe_frame_count": 25,
    "realtime_window_size": 30,
}

# ── Fusion Engine ───────────────────────────────────────
SEVERITY_SCORE_MAP: dict = {
    "severe": 0.1,
    "moderate": 0.35,
    "mild": 0.65,
    "normal": 1.0,
}

FUSION_WEIGHTS: dict = {
    "static": 0.3,
    "rom": 0.3,
    "velocity": 0.4,
}

SEVERITY_DOWNGRADE: dict = {
    "severe": "moderate",
    "moderate": "mild",
    "mild": "normal",
    "normal": "normal",
}

# ── Training Guidance Text ──────────────────────────────
GUIDANCE_MAP: dict = {
    "squat": {
        "standing": "准备好了吗？开始下蹲！",
        "descending": "很好，继续蹲下去...",
        "bottom": "到达底部！保持住，然后慢慢站起",
        "ascending": "正在站起，控制动作",
        "complete": "完成一次深蹲！继续下一次",
    },
    "lunge": {
        "standing": "准备好，向前迈出弓步！",
        "lunging": "继续下蹲，前膝不要超过脚尖",
        "bottom": "到达弓步最低点，保持稳定",
        "recovering": "回收前腿，控制节奏",
        "complete": "完成一次弓步！换腿继续",
    },
    "pushup": {
        "top": "手臂伸直，保持身体一条直线",
        "descending": "缓慢下降，肘部贴近身体",
        "bottom": "到达底部，胸接近地面",
        "ascending": "推起身体，保持核心收紧",
        "complete": "完成一次俯卧撑！",
    },
    "plank": {
        "ready": "准备进入平板支撑姿势",
        "holding": "保持！身体成一条直线",
        "drooping": "臀部下降太多，收紧核心抬起",
        "recovering": "调整姿势中...",
        "complete": "平板支撑完成！",
    },
    "shoulder_press": {
        "rest": "准备开始肩推，哑铃在肩部高度",
        "pressing": "向上推起，手臂伸直",
        "top": "到达顶部，不要锁死肘关节",
        "lowering": "缓慢下放，控制动作",
        "complete": "完成一次肩推！",
    },
}

# ── Badge Definitions ───────────────────────────────────
BADGE_DEFINITIONS: list = [
    {"type": "streak_7", "name": "坚持一周", "description": "连续打卡7天",
     "condition_streak": 7},
    {"type": "streak_30", "name": "月度达人", "description": "连续打卡30天",
     "condition_streak": 30},
    {"type": "sessions_100", "name": "百练成钢", "description": "完成100次训练",
     "condition_sessions": 100},
]

# ── FMS Test Definitions ────────────────────────────────
FMS_TEST_DEFINITIONS: list = [
    {
        "idx": 0, "name": "闭眼单腿站立",
        "instruction": "双手叉腰，闭眼，单腿站立保持平衡",
    },
    {
        "idx": 1, "name": "过头深蹲",
        "instruction": "双手举过头顶，缓慢下蹲至最低点再站起",
    },
    {
        "idx": 2, "name": "肩活动度",
        "instruction": "一手从肩上方向后、另一手从腰后方向前，双手背后相触",
    },
    {
        "idx": 3, "name": "平板支撑",
        "instruction": "俯卧，用前臂和脚尖支撑身体，保持成一条直线",
    },
    {
        "idx": 4, "name": "弓步蹲",
        "instruction": "双手叉腰，向前迈出弓步蹲，左右交替完成",
    },
]
