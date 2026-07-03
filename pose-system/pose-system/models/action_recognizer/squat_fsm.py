from .state_machine import StateMachine

def create_squat_fsm() -> StateMachine:
    fsm = StateMachine('squat')
    fsm.add_state('standing')
    fsm.add_state('descending')
    fsm.add_state('bottom')
    fsm.add_state('ascending')
    fsm.add_state('complete')

    def cond_descending(ctx):
        angle = ctx.get('knee_angle', 180.0)
        return angle < 150.0
    def cond_bottom(ctx):
        angle = ctx.get('knee_angle', 180.0)
        return angle < 90.0
    def cond_ascending(ctx):
        angle = ctx.get('knee_angle', 180.0)
        return angle > 100.0
    def cond_complete(ctx):
        angle = ctx.get('knee_angle', 180.0)
        return angle > 155.0

    fsm.add_transition('standing', 'descending', cond_descending)
    fsm.add_transition('descending', 'bottom', cond_bottom)
    fsm.add_transition('bottom', 'ascending', cond_ascending)
    fsm.add_transition('ascending', 'complete', cond_complete)
    # 回路：完成一次后需再次弯曲膝盖才开启下一次计数（防止站立不动时误触发）
    fsm.add_transition('complete', 'standing', lambda ctx: ctx.get('knee_angle', 180.0) < 140.0)
    return fsm

def create_lunge_fsm() -> StateMachine:
    fsm = StateMachine('lunge')
    fsm.add_state('standing')
    fsm.add_state('lunging')
    fsm.add_state('bottom')
    fsm.add_state('recovering')
    fsm.add_state('complete')
    fsm.add_transition('standing', 'lunging', lambda ctx: ctx.get('front_knee_angle', 180.0) < 150.0)
    fsm.add_transition('lunging', 'bottom', lambda ctx: ctx.get('front_knee_angle', 180.0) < 90.0)
    fsm.add_transition('bottom', 'recovering', lambda ctx: ctx.get('front_knee_angle', 180.0) > 100.0)
    fsm.add_transition('recovering', 'complete', lambda ctx: ctx.get('front_knee_angle', 180.0) > 155.0)
    fsm.add_transition('complete', 'standing', lambda ctx: ctx.get('front_knee_angle', 180.0) < 140.0)
    return fsm

def create_pushup_fsm() -> StateMachine:
    fsm = StateMachine('pushup')
    fsm.add_state('top')
    fsm.add_state('descending')
    fsm.add_state('bottom')
    fsm.add_state('ascending')
    fsm.add_state('complete')
    # 阈值已放宽，适配墙壁俯卧撑、上斜俯卧撑等变体
    fsm.add_transition('top', 'descending', lambda ctx: ctx.get('elbow_angle', 180.0) < 130.0)
    fsm.add_transition('descending', 'bottom', lambda ctx: ctx.get('elbow_angle', 180.0) < 110.0)
    fsm.add_transition('bottom', 'ascending', lambda ctx: ctx.get('elbow_angle', 180.0) > 115.0)
    fsm.add_transition('ascending', 'complete', lambda ctx: ctx.get('elbow_angle', 180.0) > 140.0)
    fsm.add_transition('complete', 'top', lambda ctx: ctx.get('elbow_angle', 180.0) < 130.0)
    return fsm

def create_plank_fsm() -> StateMachine:
    fsm = StateMachine('plank')
    fsm.add_state('ready')
    fsm.add_state('holding')
    fsm.add_state('drooping')
    fsm.add_state('recovering')
    fsm.add_state('complete')
    fsm.add_transition('ready', 'holding', lambda ctx: 160.0 <= (ctx.get('hip_angle', 180.0)) <= 185.0)
    fsm.add_transition('holding', 'drooping', lambda ctx: ctx.get('hip_angle', 180.0) < 160.0)
    fsm.add_transition('drooping', 'recovering', lambda ctx: ctx.get('hip_angle', 180.0) >= 160.0)
    # 需要髋角恢复到正常范围才计为完成一次（防止边界抖动误触发）
    fsm.add_transition('recovering', 'complete', lambda ctx: 170.0 <= ctx.get('hip_angle', 180.0) <= 185.0)
    fsm.add_transition('complete', 'ready', lambda ctx: ctx.get('hip_angle', 180.0) < 150.0)
    return fsm

def create_shoulder_press_fsm() -> StateMachine:
    fsm = StateMachine('shoulder_press')
    fsm.add_state('rest')
    fsm.add_state('pressing')
    fsm.add_state('top')
    fsm.add_state('lowering')
    fsm.add_state('complete')
    fsm.add_transition('rest', 'pressing', lambda ctx: ctx.get('elbow_angle', 180.0) < 160.0)
    fsm.add_transition('pressing', 'top', lambda ctx: ctx.get('elbow_angle', 180.0) > 160.0)
    fsm.add_transition('top', 'lowering', lambda ctx: ctx.get('elbow_angle', 180.0) < 150.0)
    fsm.add_transition('lowering', 'complete', lambda ctx: ctx.get('elbow_angle', 180.0) < 100.0)
    fsm.add_transition('complete', 'rest', lambda ctx: ctx.get('elbow_angle', 180.0) < 130.0)
    return fsm

def create_jumping_jack_fsm() -> StateMachine:
    fsm = StateMachine('jumping_jack')
    fsm.add_state('standing')
    fsm.add_state('jumping_up')
    fsm.add_state('open')
    fsm.add_state('closing')
    fsm.add_state('complete')
    fsm.add_transition('standing', 'jumping_up', lambda ctx: ctx.get('hip_angle', 180.0) < 170.0)
    fsm.add_transition('jumping_up', 'open', lambda ctx: ctx.get('hip_angle', 180.0) < 150.0)
    fsm.add_transition('open', 'closing', lambda ctx: ctx.get('hip_angle', 180.0) > 150.0)
    fsm.add_transition('closing', 'complete', lambda ctx: ctx.get('hip_angle', 180.0) > 170.0)
    fsm.add_transition('complete', 'standing', lambda ctx: ctx.get('hip_angle', 180.0) < 165.0)
    return fsm


def create_deadlift_fsm() -> StateMachine:
    fsm = StateMachine('deadlift')
    fsm.add_state('standing')
    fsm.add_state('lowering')
    fsm.add_state('bottom')
    fsm.add_state('lifting')
    fsm.add_state('complete')
    fsm.add_transition('standing', 'lowering', lambda ctx: ctx.get('hip_angle', 180.0) < 160.0)
    fsm.add_transition('lowering', 'bottom', lambda ctx: ctx.get('hip_angle', 180.0) < 100.0)
    fsm.add_transition('bottom', 'lifting', lambda ctx: ctx.get('hip_angle', 180.0) > 100.0)
    fsm.add_transition('lifting', 'complete', lambda ctx: ctx.get('hip_angle', 180.0) > 160.0)
    fsm.add_transition('complete', 'standing', lambda ctx: ctx.get('hip_angle', 180.0) < 150.0)
    return fsm


# ── 新增 FSM ──────────────────────────────────────

def create_neck_side_bend_fsm() -> StateMachine:
    """颈部侧屈拉伸：头从正中 → 侧屈 → 回正 = 1 次"""
    fsm = StateMachine('neck_side_bend')
    fsm.add_state('center')
    fsm.add_state('tilting')
    fsm.add_state('tilted')
    fsm.add_state('returning')
    fsm.add_state('complete')
    fsm.add_transition('center', 'tilting', lambda ctx: ctx.get('neck_tilt', 0) > 10.0)
    fsm.add_transition('tilting', 'tilted', lambda ctx: ctx.get('neck_tilt', 0) > 18.0)
    fsm.add_transition('tilted', 'returning', lambda ctx: ctx.get('neck_tilt', 0) < 10.0)
    fsm.add_transition('returning', 'complete', lambda ctx: ctx.get('neck_tilt', 0) < 3.0)
    fsm.add_transition('complete', 'center', lambda ctx: ctx.get('neck_tilt', 0) > 12.0)
    return fsm


def create_chin_tuck_fsm() -> StateMachine:
    """收下巴（坐姿）：头前倾 → 后收 → 放松 = 1 次"""
    fsm = StateMachine('chin_tuck')
    fsm.add_state('forward')
    fsm.add_state('tucking')
    fsm.add_state('tucked')
    fsm.add_state('complete')
    fsm.add_transition('forward', 'tucking', lambda ctx: ctx.get('neck_tilt', 30) < 8.0)
    fsm.add_transition('tucking', 'tucked', lambda ctx: ctx.get('neck_tilt', 30) < 3.0)
    fsm.add_transition('tucked', 'complete', lambda ctx: ctx.get('neck_tilt', 30) > 6.0)
    fsm.add_transition('complete', 'forward', lambda ctx: ctx.get('neck_tilt', 30) > 10.0)
    return fsm


def create_cat_cow_fsm() -> StateMachine:
    """猫牛式：四足跪姿，脊柱拱起(猫) ↔ 下沉(牛) = 1 个循环"""
    fsm = StateMachine('cat_cow')
    fsm.add_state('neutral')
    fsm.add_state('cat')
    fsm.add_state('cow')
    fsm.add_state('complete')
    # 猫式：脊柱拱起 → hip_angle 变小（肩-髋-膝夹角变小）
    fsm.add_transition('neutral', 'cat', lambda ctx: ctx.get('hip_angle', 180) < 150.0)
    # 牛式：脊柱下沉 → hip_angle 变大
    fsm.add_transition('cat', 'cow', lambda ctx: ctx.get('hip_angle', 180) > 170.0)
    # 回到中立
    fsm.add_transition('cow', 'complete', lambda ctx: 150.0 <= ctx.get('hip_angle', 180) <= 170.0)
    fsm.add_transition('complete', 'neutral', lambda ctx: ctx.get('hip_angle', 180) < 145.0)
    return fsm


def create_hamstring_stretch_fsm() -> StateMachine:
    """仰卧腘绳肌拉伸：腿放下 → 抬起 → 放下 = 1 次"""
    fsm = StateMachine('hamstring_stretch')
    fsm.add_state('resting')
    fsm.add_state('raising')
    fsm.add_state('raised')
    fsm.add_state('lowering')
    fsm.add_state('complete')
    fsm.add_transition('resting', 'raising', lambda ctx: ctx.get('hip_angle', 180) < 150.0)
    fsm.add_transition('raising', 'raised', lambda ctx: ctx.get('hip_angle', 180) < 100.0)
    fsm.add_transition('raised', 'lowering', lambda ctx: ctx.get('hip_angle', 180) > 120.0)
    fsm.add_transition('lowering', 'complete', lambda ctx: ctx.get('hip_angle', 180) > 160.0)
    fsm.add_transition('complete', 'resting', lambda ctx: ctx.get('hip_angle', 180) < 140.0)
    return fsm


def create_bridge_fsm() -> StateMachine:
    """臀桥：躺平 → 抬臀 → 放下 = 1 次"""
    fsm = StateMachine('bridge')
    fsm.add_state('down')
    fsm.add_state('lifting')
    fsm.add_state('up')
    fsm.add_state('lowering')
    fsm.add_state('complete')
    fsm.add_transition('down', 'lifting', lambda ctx: ctx.get('hip_angle', 90) > 130.0)
    fsm.add_transition('lifting', 'up', lambda ctx: ctx.get('hip_angle', 90) > 170.0)
    fsm.add_transition('up', 'lowering', lambda ctx: ctx.get('hip_angle', 90) < 160.0)
    fsm.add_transition('lowering', 'complete', lambda ctx: ctx.get('hip_angle', 90) < 130.0)
    fsm.add_transition('complete', 'down', lambda ctx: ctx.get('hip_angle', 90) > 140.0)
    return fsm


def create_bulgarian_split_squat_fsm() -> StateMachine:
    """保加利亚分腿蹲：站立 → 下蹲 → 底部 → 站起 = 1次"""
    fsm = StateMachine('bulgarian_split_squat')
    fsm.add_state('standing')
    fsm.add_state('descending')
    fsm.add_state('bottom')
    fsm.add_state('ascending')
    fsm.add_state('complete')
    fsm.add_transition('standing', 'descending', lambda ctx: ctx.get('knee_angle', 180) < 150.0)
    fsm.add_transition('descending', 'bottom', lambda ctx: ctx.get('knee_angle', 180) < 90.0)
    fsm.add_transition('bottom', 'ascending', lambda ctx: ctx.get('knee_angle', 180) > 100.0)
    fsm.add_transition('ascending', 'complete', lambda ctx: ctx.get('knee_angle', 180) > 155.0)
    fsm.add_transition('complete', 'standing', lambda ctx: ctx.get('knee_angle', 180) < 140.0)
    return fsm


def create_mountain_climber_fsm() -> StateMachine:
    """登山者（慢速控制）：平板 → 提膝 → 回位 = 1次（左右交替）"""
    fsm = StateMachine('mountain_climber')
    fsm.add_state('plank')
    fsm.add_state('knee_drive')
    fsm.add_state('knee_in')
    fsm.add_state('returning')
    fsm.add_state('complete')
    fsm.add_transition('plank', 'knee_drive', lambda ctx: ctx.get('hip_angle', 180) < 150.0)
    fsm.add_transition('knee_drive', 'knee_in', lambda ctx: ctx.get('hip_angle', 180) < 100.0)
    fsm.add_transition('knee_in', 'returning', lambda ctx: ctx.get('hip_angle', 180) > 130.0)
    fsm.add_transition('returning', 'complete', lambda ctx: ctx.get('hip_angle', 180) > 160.0)
    fsm.add_transition('complete', 'plank', lambda ctx: ctx.get('hip_angle', 180) < 140.0)
    return fsm


def create_bird_dog_fsm() -> StateMachine:
    """鸟狗式：四足跪姿 → 伸展对侧手脚 → 收回 = 1次"""
    fsm = StateMachine('bird_dog')
    fsm.add_state('start')
    fsm.add_state('extending')
    fsm.add_state('extended')
    fsm.add_state('returning')
    fsm.add_state('complete')
    fsm.add_transition('start', 'extending', lambda ctx: ctx.get('hip_angle', 160) > 170.0)
    fsm.add_transition('extending', 'extended', lambda ctx: ctx.get('hip_angle', 160) < 155.0)
    fsm.add_transition('extended', 'returning', lambda ctx: ctx.get('hip_angle', 160) > 165.0)
    fsm.add_transition('returning', 'complete', lambda ctx: 150.0 <= ctx.get('hip_angle', 160) <= 170.0)
    fsm.add_transition('complete', 'start', lambda ctx: ctx.get('hip_angle', 160) > 172.0)
    return fsm


def create_doorway_stretch_fsm() -> StateMachine:
    """门框胸拉伸：保持拉伸姿势（计时类）"""
    fsm = StateMachine('doorway_stretch')
    fsm.add_state('ready')
    fsm.add_state('stretching')
    fsm.add_state('holding')
    fsm.add_state('complete')
    fsm.add_transition('ready', 'stretching', lambda ctx: ctx.get('shoulder_angle', 0) > 70.0)
    fsm.add_transition('stretching', 'holding', lambda ctx: ctx.get('shoulder_angle', 0) > 85.0)
    fsm.add_transition('holding', 'complete', lambda ctx: ctx.get('shoulder_angle', 0) < 70.0)
    fsm.add_transition('complete', 'ready', lambda ctx: ctx.get('shoulder_angle', 0) > 75.0)
    return fsm


def create_shoulder_circle_fsm() -> StateMachine:
    """肩部环绕：肩角周期性变化 = 1圈"""
    fsm = StateMachine('shoulder_circle')
    fsm.add_state('rest')
    fsm.add_state('moving_up')
    fsm.add_state('top')
    fsm.add_state('moving_down')
    fsm.add_state('complete')
    fsm.add_transition('rest', 'moving_up', lambda ctx: ctx.get('shoulder_angle', 90) > 110.0)
    fsm.add_transition('moving_up', 'top', lambda ctx: ctx.get('shoulder_angle', 90) > 140.0)
    fsm.add_transition('top', 'moving_down', lambda ctx: ctx.get('shoulder_angle', 90) < 120.0)
    fsm.add_transition('moving_down', 'complete', lambda ctx: ctx.get('shoulder_angle', 90) < 70.0)
    fsm.add_transition('complete', 'rest', lambda ctx: ctx.get('shoulder_angle', 90) > 100.0)
    return fsm


def create_cobra_fsm() -> StateMachine:
    """眼镜蛇式：俯卧 → 推起 → 保持（计时类）"""
    fsm = StateMachine('cobra')
    fsm.add_state('prone')
    fsm.add_state('pushing_up')
    fsm.add_state('holding')
    fsm.add_state('complete')
    fsm.add_transition('prone', 'pushing_up', lambda ctx: ctx.get('hip_angle', 120) > 140.0)
    fsm.add_transition('pushing_up', 'holding', lambda ctx: ctx.get('hip_angle', 120) > 160.0)
    fsm.add_transition('holding', 'complete', lambda ctx: ctx.get('hip_angle', 120) < 140.0)
    fsm.add_transition('complete', 'prone', lambda ctx: ctx.get('hip_angle', 120) > 145.0)
    return fsm


def create_prone_y_raise_fsm() -> StateMachine:
    """俯卧Y字举：手臂放下 → 上举 → 放下 = 1次"""
    fsm = StateMachine('prone_y_raise')
    fsm.add_state('down')
    fsm.add_state('raising')
    fsm.add_state('up')
    fsm.add_state('lowering')
    fsm.add_state('complete')
    fsm.add_transition('down', 'raising', lambda ctx: ctx.get('shoulder_angle', 90) > 100.0)
    fsm.add_transition('raising', 'up', lambda ctx: ctx.get('shoulder_angle', 90) > 145.0)
    fsm.add_transition('up', 'lowering', lambda ctx: ctx.get('shoulder_angle', 90) < 130.0)
    fsm.add_transition('lowering', 'complete', lambda ctx: ctx.get('shoulder_angle', 90) < 100.0)
    fsm.add_transition('complete', 'down', lambda ctx: ctx.get('shoulder_angle', 90) > 110.0)
    return fsm


def create_prone_t_raise_fsm() -> StateMachine:
    """俯卧T字举：手臂放下 → 侧举 → 放下 = 1次"""
    fsm = StateMachine('prone_t_raise')
    fsm.add_state('down')
    fsm.add_state('raising')
    fsm.add_state('up')
    fsm.add_state('lowering')
    fsm.add_state('complete')
    fsm.add_transition('down', 'raising', lambda ctx: ctx.get('shoulder_angle', 45) > 55.0)
    fsm.add_transition('raising', 'up', lambda ctx: ctx.get('shoulder_angle', 45) > 70.0)
    fsm.add_transition('up', 'lowering', lambda ctx: ctx.get('shoulder_angle', 45) < 65.0)
    fsm.add_transition('lowering', 'complete', lambda ctx: ctx.get('shoulder_angle', 45) < 55.0)
    fsm.add_transition('complete', 'down', lambda ctx: ctx.get('shoulder_angle', 45) > 60.0)
    return fsm


def create_side_bend_fsm() -> StateMachine:
    """站姿体侧屈：直立 → 侧屈 → 回正 = 1次"""
    fsm = StateMachine('side_bend')
    fsm.add_state('upright')
    fsm.add_state('bending')
    fsm.add_state('bent')
    fsm.add_state('returning')
    fsm.add_state('complete')
    fsm.add_transition('upright', 'bending', lambda ctx: ctx.get('trunk_tilt', 0) > 10.0)
    fsm.add_transition('bending', 'bent', lambda ctx: ctx.get('trunk_tilt', 0) > 20.0)
    fsm.add_transition('bent', 'returning', lambda ctx: ctx.get('trunk_tilt', 0) < 15.0)
    fsm.add_transition('returning', 'complete', lambda ctx: ctx.get('trunk_tilt', 0) < 5.0)
    fsm.add_transition('complete', 'upright', lambda ctx: ctx.get('trunk_tilt', 0) > 12.0)
    return fsm


def create_hip_flexor_stretch_fsm() -> StateMachine:
    """髋屈肌半跪拉伸：保持拉伸（计时类）"""
    fsm = StateMachine('hip_flexor_stretch')
    fsm.add_state('kneeling')
    fsm.add_state('stretching')
    fsm.add_state('holding')
    fsm.add_state('complete')
    fsm.add_transition('kneeling', 'stretching', lambda ctx: ctx.get('knee_angle', 180) < 120.0)
    fsm.add_transition('stretching', 'holding', lambda ctx: ctx.get('knee_angle', 180) < 100.0)
    fsm.add_transition('holding', 'complete', lambda ctx: ctx.get('knee_angle', 180) > 105.0)
    fsm.add_transition('complete', 'kneeling', lambda ctx: ctx.get('knee_angle', 180) < 95.0)
    return fsm


def create_piriformis_stretch_fsm() -> StateMachine:
    """坐姿梨状肌拉伸：保持拉伸（计时类）"""
    fsm = StateMachine('piriformis_stretch')
    fsm.add_state('seated')
    fsm.add_state('stretching')
    fsm.add_state('holding')
    fsm.add_state('complete')
    fsm.add_transition('seated', 'stretching', lambda ctx: ctx.get('knee_angle', 120) < 110.0)
    fsm.add_transition('stretching', 'holding', lambda ctx: ctx.get('knee_angle', 120) < 95.0)
    fsm.add_transition('holding', 'complete', lambda ctx: ctx.get('knee_angle', 120) > 100.0)
    fsm.add_transition('complete', 'seated', lambda ctx: ctx.get('knee_angle', 120) < 105.0)
    return fsm


def create_balance_stand_fsm() -> StateMachine:
    """双腿闭眼站立：保持稳定（计时类）"""
    fsm = StateMachine('balance_stand')
    fsm.add_state('ready')
    fsm.add_state('balancing')
    fsm.add_state('unstable')
    fsm.add_state('complete')
    fsm.add_transition('ready', 'balancing', lambda ctx: ctx.get('trunk_tilt', 10) <= 5.0)
    fsm.add_transition('balancing', 'unstable', lambda ctx: ctx.get('trunk_tilt', 10) > 5.0)
    fsm.add_transition('unstable', 'balancing', lambda ctx: ctx.get('trunk_tilt', 10) <= 5.0)
    fsm.add_transition('balancing', 'complete', lambda ctx: ctx.get('trunk_tilt', 10) > 5.0)
    fsm.add_transition('complete', 'ready', lambda ctx: ctx.get('trunk_tilt', 10) <= 3.0)
    return fsm


def create_ankle_circle_fsm() -> StateMachine:
    """踝关节环绕：膝角周期变化 = 1圈"""
    fsm = StateMachine('ankle_circle')
    fsm.add_state('rest')
    fsm.add_state('moving')
    fsm.add_state('flexed')
    fsm.add_state('returning')
    fsm.add_state('complete')
    fsm.add_transition('rest', 'moving', lambda ctx: ctx.get('knee_angle', 90) < 80.0)
    fsm.add_transition('moving', 'flexed', lambda ctx: ctx.get('knee_angle', 90) < 72.0)
    fsm.add_transition('flexed', 'returning', lambda ctx: ctx.get('knee_angle', 90) > 82.0)
    fsm.add_transition('returning', 'complete', lambda ctx: ctx.get('knee_angle', 90) > 88.0)
    fsm.add_transition('complete', 'rest', lambda ctx: ctx.get('knee_angle', 90) < 78.0)
    return fsm


def create_hip_circle_fsm() -> StateMachine:
    """髋关节环绕：髋角周期变化 = 1圈"""
    fsm = StateMachine('hip_circle')
    fsm.add_state('rest')
    fsm.add_state('moving')
    fsm.add_state('extended')
    fsm.add_state('returning')
    fsm.add_state('complete')
    fsm.add_transition('rest', 'moving', lambda ctx: ctx.get('hip_angle', 150) < 140.0)
    fsm.add_transition('moving', 'extended', lambda ctx: ctx.get('hip_angle', 150) < 128.0)
    fsm.add_transition('extended', 'returning', lambda ctx: ctx.get('hip_angle', 150) > 145.0)
    fsm.add_transition('returning', 'complete', lambda ctx: ctx.get('hip_angle', 150) > 155.0)
    fsm.add_transition('complete', 'rest', lambda ctx: ctx.get('hip_angle', 150) < 138.0)
    return fsm


def create_star_touch_fsm() -> StateMachine:
    """单腿星形触地：站立 → 伸腿点地 → 收回 = 1次"""
    fsm = StateMachine('star_touch')
    fsm.add_state('standing')
    fsm.add_state('reaching')
    fsm.add_state('touched')
    fsm.add_state('returning')
    fsm.add_state('complete')
    # 伸腿时支撑腿膝盖弯曲
    fsm.add_transition('standing', 'reaching', lambda ctx: ctx.get('knee_angle', 180) < 160.0)
    fsm.add_transition('reaching', 'touched', lambda ctx: ctx.get('knee_angle', 180) < 145.0)
    fsm.add_transition('touched', 'returning', lambda ctx: ctx.get('knee_angle', 180) > 155.0)
    fsm.add_transition('returning', 'complete', lambda ctx: ctx.get('knee_angle', 180) > 170.0)
    fsm.add_transition('complete', 'standing', lambda ctx: ctx.get('knee_angle', 180) < 155.0)
    return fsm


def create_quad_stretch_fsm() -> StateMachine:
    """侧卧股四头肌拉伸：屈膝拉伸保持（计时类）"""
    fsm = StateMachine('quad_stretch')
    fsm.add_state('resting')
    fsm.add_state('stretching')
    fsm.add_state('holding')
    fsm.add_state('complete')
    fsm.add_transition('resting', 'stretching', lambda ctx: ctx.get('knee_angle', 180) < 100.0)
    fsm.add_transition('stretching', 'holding', lambda ctx: ctx.get('knee_angle', 180) < 80.0)
    fsm.add_transition('holding', 'complete', lambda ctx: ctx.get('knee_angle', 180) > 90.0)
    fsm.add_transition('complete', 'resting', lambda ctx: ctx.get('knee_angle', 180) < 95.0)
    return fsm


def create_child_pose_fsm() -> StateMachine:
    """婴儿式：折叠保持（计时类）"""
    fsm = StateMachine('child_pose')
    fsm.add_state('upright')
    fsm.add_state('folding')
    fsm.add_state('holding')
    fsm.add_state('complete')
    fsm.add_transition('upright', 'folding', lambda ctx: ctx.get('hip_angle', 180) < 120.0)
    fsm.add_transition('folding', 'holding', lambda ctx: ctx.get('hip_angle', 180) < 80.0)
    fsm.add_transition('holding', 'complete', lambda ctx: ctx.get('hip_angle', 180) > 90.0)
    fsm.add_transition('complete', 'upright', lambda ctx: ctx.get('hip_angle', 180) < 110.0)
    return fsm


def get_initial_state(action_name: str) -> str:
    initials = {
        'squat': 'standing',
        'lunge': 'standing',
        'pushup': 'top',
        'plank': 'ready',
        'shoulder_press': 'rest',
        'jumping_jack': 'standing',
        'deadlift': 'standing',
        'neck_side_bend': 'center',
        'chin_tuck': 'forward',
        'cat_cow': 'neutral',
        'hamstring_stretch': 'resting',
        'bridge': 'down',
        'star_touch': 'standing',
        'quad_stretch': 'resting',
        'child_pose': 'upright',
        'bulgarian_split_squat': 'standing',
        'mountain_climber': 'plank',
        'bird_dog': 'start',
        'doorway_stretch': 'ready',
        'shoulder_circle': 'rest',
        'cobra': 'prone',
        'prone_y_raise': 'down',
        'prone_t_raise': 'down',
        'side_bend': 'upright',
        'hip_flexor_stretch': 'kneeling',
        'piriformis_stretch': 'seated',
        'balance_stand': 'ready',
        'ankle_circle': 'rest',
        'hip_circle': 'rest',
    }
    return initials.get(action_name.lower(), 'standing')

def get_fsm_context(action_name: str, angles: dict) -> dict:
    """Extract relevant angles from full angle dict for a given action."""
    ctx = {}
    name = action_name.lower()
    if name == 'squat':
        ctx['knee_angle'] = angles.get('left_knee') if angles.get('left_knee') is not None else (angles.get('right_knee') if angles.get('right_knee') is not None else 180.0)
    elif name == 'lunge':
        ctx['front_knee_angle'] = angles.get('left_knee') if angles.get('left_knee') is not None else (angles.get('right_knee') if angles.get('right_knee') is not None else 180.0)
        ctx['knee_angle'] = ctx['front_knee_angle']
    elif name == 'pushup':
        ctx['elbow_angle'] = angles.get('left_elbow') if angles.get('left_elbow') is not None else (angles.get('right_elbow') if angles.get('right_elbow') is not None else 180.0)
    elif name == 'plank':
        ctx['hip_angle'] = angles.get('left_hip') if angles.get('left_hip') is not None else (angles.get('right_hip') if angles.get('right_hip') is not None else 180.0)
    elif name == 'shoulder_press':
        ctx['elbow_angle'] = angles.get('left_elbow') if angles.get('left_elbow') is not None else (angles.get('right_elbow') if angles.get('right_elbow') is not None else 180.0)
    elif name == 'jumping_jack':
        ctx['hip_angle'] = angles.get('left_hip') if angles.get('left_hip') is not None else (angles.get('right_hip') if angles.get('right_hip') is not None else 180.0)
    elif name == 'deadlift':
        ctx['hip_angle'] = angles.get('left_hip') if angles.get('left_hip') is not None else (angles.get('right_hip') if angles.get('right_hip') is not None else 180.0)
        ctx['knee_angle'] = angles.get('left_knee') if angles.get('left_knee') is not None else (angles.get('right_knee') if angles.get('right_knee') is not None else 180.0)
    elif name in ('neck_side_bend', 'chin_tuck'):
        ctx['neck_tilt'] = angles.get('neck_tilt') if angles.get('neck_tilt') is not None else 0.0
    elif name in ('cat_cow', 'hamstring_stretch', 'bridge', 'child_pose'):
        ctx['hip_angle'] = angles.get('left_hip') if angles.get('left_hip') is not None else (angles.get('right_hip') if angles.get('right_hip') is not None else 180.0)
    elif name in ('star_touch', 'quad_stretch', 'bulgarian_split_squat'):
        ctx['knee_angle'] = angles.get('left_knee') if angles.get('left_knee') is not None else (angles.get('right_knee') if angles.get('right_knee') is not None else 180.0)
    elif name in ('mountain_climber', 'bird_dog'):
        ctx['hip_angle'] = angles.get('left_hip') if angles.get('left_hip') is not None else (angles.get('right_hip') if angles.get('right_hip') is not None else 180.0)
    elif name in ('doorway_stretch', 'shoulder_circle', 'prone_y_raise', 'prone_t_raise'):
        ctx['shoulder_angle'] = angles.get('left_shoulder') if angles.get('left_shoulder') is not None else (angles.get('right_shoulder') if angles.get('right_shoulder') is not None else 90.0)
    elif name == 'cobra':
        ctx['hip_angle'] = angles.get('left_hip') if angles.get('left_hip') is not None else (angles.get('right_hip') if angles.get('right_hip') is not None else 120.0)
    elif name in ('side_bend', 'balance_stand'):
        ctx['trunk_tilt'] = angles.get('trunk_tilt') if angles.get('trunk_tilt') is not None else 0.0
    elif name in ('hip_flexor_stretch', 'piriformis_stretch', 'ankle_circle'):
        ctx['knee_angle'] = angles.get('left_knee') if angles.get('left_knee') is not None else (angles.get('right_knee') if angles.get('right_knee') is not None else 90.0)
    elif name == 'hip_circle':
        ctx['hip_angle'] = angles.get('left_hip') if angles.get('left_hip') is not None else (angles.get('right_hip') if angles.get('right_hip') is not None else 150.0)
    else:
        ctx['knee_angle'] = angles.get('left_knee') if angles.get('left_knee') is not None else (angles.get('right_knee') if angles.get('right_knee') is not None else 180.0)
    return ctx

def get_fsm_for_action(action_name: str) -> StateMachine:
    fsms = {
        'squat': create_squat_fsm,
        'lunge': create_lunge_fsm,
        'pushup': create_pushup_fsm,
        'plank': create_plank_fsm,
        'shoulder_press': create_shoulder_press_fsm,
        'jumping_jack': create_jumping_jack_fsm,
        'deadlift': create_deadlift_fsm,
        'neck_side_bend': create_neck_side_bend_fsm,
        'chin_tuck': create_chin_tuck_fsm,
        'cat_cow': create_cat_cow_fsm,
        'hamstring_stretch': create_hamstring_stretch_fsm,
        'bridge': create_bridge_fsm,
        'star_touch': create_star_touch_fsm,
        'quad_stretch': create_quad_stretch_fsm,
        'child_pose': create_child_pose_fsm,
        'bulgarian_split_squat': create_bulgarian_split_squat_fsm,
        'mountain_climber': create_mountain_climber_fsm,
        'bird_dog': create_bird_dog_fsm,
        'doorway_stretch': create_doorway_stretch_fsm,
        'shoulder_circle': create_shoulder_circle_fsm,
        'cobra': create_cobra_fsm,
        'prone_y_raise': create_prone_y_raise_fsm,
        'prone_t_raise': create_prone_t_raise_fsm,
        'side_bend': create_side_bend_fsm,
        'hip_flexor_stretch': create_hip_flexor_stretch_fsm,
        'piriformis_stretch': create_piriformis_stretch_fsm,
        'balance_stand': create_balance_stand_fsm,
        'ankle_circle': create_ankle_circle_fsm,
        'hip_circle': create_hip_circle_fsm,
    }
    if action_name.lower() in fsms:
        return fsms[action_name.lower()]()
    return create_squat_fsm()

