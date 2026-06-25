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

# Other action FSMs (lunges, push-ups, planks, etc.)
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

def get_fsm_for_action(action_name: str) -> StateMachine:
    fsms = {
        'squat': create_squat_fsm,
        'lunge': create_lunge_fsm,
        'pushup': create_pushup_fsm,
    }
    if action_name.lower() in fsms:
        return fsms[action_name.lower()]()
    return create_squat_fsm()
