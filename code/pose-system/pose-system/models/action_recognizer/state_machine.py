from typing import Dict, List, Callable, Any, Optional
from dataclasses import dataclass

@dataclass
class State:
    name: str
    on_enter: Optional[Callable] = None
    on_exit: Optional[Callable] = None

@dataclass
class Transition:
    from_state: str
    to_state: str
    condition: Callable[[Dict[str, Any]], bool]

class StateMachine:
    def __init__(self, name: str = 'FSM'):
        self.name = name
        self.states: Dict[str, State] = {}
        self.transitions: List[Transition] = []
        self.current_state: Optional[str] = None
        self.context: Dict[str, Any] = {}
        self.state_history: List[str] = []
    
    def add_state(self, name: str, on_enter=None, on_exit=None):
        self.states[name] = State(name=name, on_enter=on_enter, on_exit=on_exit)
    
    def add_transition(self, from_state: str, to_state: str, condition: Callable):
        self.transitions.append(Transition(from_state, to_state, condition))
    
    def start(self, initial_state: str, context: Optional[Dict] = None):
        if initial_state not in self.states:
            raise ValueError(f'Unknown state: {initial_state}')
        self.current_state = initial_state
        self.state_history = [initial_state]
        if context:
            self.context.update(context)
        state = self.states[initial_state]
        if state.on_enter:
            state.on_enter(self.context)
    
    def update(self, new_context: Dict[str, Any]) -> Optional[str]:
        self.context.update(new_context)
        prev_state = self.current_state
        for t in self.transitions:
            if t.from_state == self.current_state:
                try:
                    if t.condition(self.context):
                        old_state = self.states[self.current_state]
                        if old_state.on_exit:
                            old_state.on_exit(self.context)
                        self.current_state = t.to_state
                        self.state_history.append(t.to_state)
                        new_state = self.states[self.current_state]
                        if new_state.on_enter:
                            new_state.on_enter(self.context)
                        return t.to_state
                except Exception:
                    pass
        return None
    
    def get_state(self) -> str:
        return self.current_state
    
    def get_progress(self) -> float:
        states_order = list(self.states.keys())
        if self.current_state in states_order:
            idx = states_order.index(self.current_state)
            return idx / max(len(states_order) - 1, 1) * 100.0
        return 0.0
