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
        angle = ctx.get('knee_angle', 90.0)
        return angle > 155.0

    fsm.add_transition('standing', 'descending', cond_descending)
    fsm.add_transition('descending', 'bottom', cond_bottom)
    fsm.add_transition('bottom', 'ascending', cond_ascending)
    fsm.add_transition('ascending', 'complete', cond_complete)
    return fsm

def create_lunge_fsm() -> StateMachine:
    fsm = StateMachine('lunge')
    fsm.add_state('standing')
    fsm.add_state('lunging')
    fsm.add_state('bottom')
    fsm.add_state('recovering')
    fsm.add_state('complete')
    fsm.add_transition('standing', 'lunging', lambda ctx: ctx.get('front_knee_angle', 180.0) < 150.0)
    fsm.add_transition('lunging', 'bottom', lambda ctx: ctx.get('front_knee_angle', 120.0) < 90.0)
    fsm.add_transition('bottom', 'recovering', lambda ctx: ctx.get('front_knee_angle', 90.0) > 100.0)
    fsm.add_transition('recovering', 'complete', lambda ctx: ctx.get('front_knee_angle', 100.0) > 155.0)
    return fsm

def create_pushup_fsm() -> StateMachine:
    fsm = StateMachine('pushup')
    fsm.add_state('top')
    fsm.add_state('descending')
    fsm.add_state('bottom')
    fsm.add_state('ascending')
    fsm.add_state('complete')
    fsm.add_transition('top', 'descending', lambda ctx: ctx.get('elbow_angle', 180.0) < 150.0)
    fsm.add_transition('descending', 'bottom', lambda ctx: ctx.get('elbow_angle', 100.0) < 90.0)
    fsm.add_transition('bottom', 'ascending', lambda ctx: ctx.get('elbow_angle', 80.0) > 100.0)
    fsm.add_transition('ascending', 'complete', lambda ctx: ctx.get('elbow_angle', 100.0) > 160.0)
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
    fsm.add_transition('drooping', 'recovering', lambda ctx: ctx.get('hip_angle', 0.0) >= 160.0)
    fsm.add_transition('recovering', 'complete', lambda ctx: True)
    return fsm

def create_shoulder_press_fsm() -> StateMachine:
    fsm = StateMachine('shoulder_press')
    fsm.add_state('rest')
    fsm.add_state('pressing')
    fsm.add_state('top')
    fsm.add_state('lowering')
    fsm.add_state('complete')
    fsm.add_transition('rest', 'pressing', lambda ctx: ctx.get('elbow_angle', 180.0) < 160.0)
    fsm.add_transition('pressing', 'top', lambda ctx: ctx.get('elbow_angle', 90.0) > 160.0)
    fsm.add_transition('top', 'lowering', lambda ctx: ctx.get('elbow_angle', 170.0) < 150.0)
    fsm.add_transition('lowering', 'complete', lambda ctx: ctx.get('elbow_angle', 0.0) < 100.0)
    return fsm

def create_jumping_jack_fsm() -> StateMachine:
    fsm = StateMachine('jumping_jack')
    fsm.add_state('standing')
    fsm.add_state('jumping_up')
    fsm.add_state('open')
    fsm.add_state('closing')
    fsm.add_state('complete')
    fsm.add_transition('standing', 'jumping_up', lambda ctx: ctx.get('hip_angle', 180.0) < 170.0)
    fsm.add_transition('jumping_up', 'open', lambda ctx: ctx.get('hip_angle', 150.0) < 150.0)
    fsm.add_transition('open', 'closing', lambda ctx: ctx.get('hip_angle', 130.0) > 150.0)
    fsm.add_transition('closing', 'complete', lambda ctx: ctx.get('hip_angle', 160.0) > 170.0)
    return fsm


def create_deadlift_fsm() -> StateMachine:
    fsm = StateMachine('deadlift')
    fsm.add_state('standing')
    fsm.add_state('lowering')
    fsm.add_state('bottom')
    fsm.add_state('lifting')
    fsm.add_state('complete')
    fsm.add_transition('standing', 'lowering', lambda ctx: ctx.get('hip_angle', 180.0) < 160.0)
    fsm.add_transition('lowering', 'bottom', lambda ctx: ctx.get('hip_angle', 100.0) < 100.0)
    fsm.add_transition('bottom', 'lifting', lambda ctx: ctx.get('hip_angle', 50.0) > 100.0)
    fsm.add_transition('lifting', 'complete', lambda ctx: ctx.get('hip_angle', 120.0) > 160.0)
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
    }
    return initials.get(action_name.lower(), 'standing')

def get_fsm_context(action_name: str, angles: dict) -> dict:
    """Extract relevant angles from full angle dict for a given action."""
    ctx = {}
    name = action_name.lower()
    if name == 'squat':
        ctx['knee_angle'] = angles.get('left_knee') or angles.get('right_knee') or 180.0
    elif name == 'lunge':
        ctx['front_knee_angle'] = angles.get('left_knee') or angles.get('right_knee') or 180.0
        ctx['knee_angle'] = ctx['front_knee_angle']
    elif name == 'pushup':
        ctx['elbow_angle'] = angles.get('left_elbow') or angles.get('right_elbow') or 180.0
    elif name == 'plank':
        ctx['hip_angle'] = angles.get('left_hip') or angles.get('right_hip') or 180.0
    elif name == 'shoulder_press':
        ctx['elbow_angle'] = angles.get('left_elbow') or angles.get('right_elbow') or 180.0
    elif name == 'jumping_jack':
        ctx['hip_angle'] = angles.get('left_hip') or angles.get('right_hip') or 180.0
    elif name == 'deadlift':
        ctx['hip_angle'] = angles.get('left_hip') or angles.get('right_hip') or 180.0
        ctx['knee_angle'] = angles.get('left_knee') or angles.get('right_knee') or 180.0
    else:
        ctx['knee_angle'] = angles.get('left_knee') or angles.get('right_knee') or 180.0
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
    }
    if action_name.lower() in fsms:
        return fsms[action_name.lower()]()
    return create_squat_fsm()

