"""Transition rules and guards for the state machine.

BUG: Guards run AFTER state change instead of BEFORE.
This means invalid transitions are applied, then rejected, leaving
the machine in an inconsistent/corrupted state.
"""

from typing import Callable, Dict, List, Optional, Tuple
from .states import State


class TransitionRule:
    """Defines a transition between states."""
    
    def __init__(self, from_state: State, to_state: State, guard: Callable = None):
        self.from_state = from_state
        self.to_state = to_state
        self.guard = guard  # Function that returns True if transition is allowed
    
    def __repr__(self):
        return f"Transition({self.from_state.value} -> {self.to_state.value})"


class TransitionError(Exception):
    """Exception raised when an invalid transition is attempted."""
    pass


class TransitionGuardFailed(Exception):
    """Exception raised when a transition guard fails."""
    pass


# Guard functions
def always_pass(machine) -> bool:
    """Default guard that always allows transition."""
    return True


def requires_running() -> bool:
    """Guard that requires current state to be RUNNING."""
    def check(machine) -> bool:
        return machine.current_state == State.RUNNING
    return check


def requires_not_idle() -> bool:
    """Guard that prevents transition from IDLE state."""
    def check(machine) -> bool:
        return machine.current_state != State.IDLE
    return check


class TransitionManager:
    """Manages transition rules and guards.
    
    BUG: The execute_transition method changes state BEFORE
    running the guard, causing invalid transitions to be applied
    then rejected, leaving the machine in a wrong state.
    """
    
    def __init__(self):
        self.rules: List[TransitionRule] = []
        self._setup_default_rules()
    
    def _setup_default_rules(self):
        """Set up the default transition rules."""
        # IDLE can go to RUNNING
        self.add_rule(State.IDLE, State.RUNNING, always_pass)
        
        # RUNNING can go to PAUSED or STOPPED
        self.add_rule(State.RUNNING, State.PAUSED, always_pass)
        self.add_rule(State.RUNNING, State.STOPPED, always_pass)
        
        # PAUSED can go to RUNNING or STOPPED
        self.add_rule(State.PAUSED, State.RUNNING, always_pass)
        self.add_rule(State.PAUSED, State.STOPPED, always_pass)
        
        # STOPPED is terminal - no transitions out
        # ERROR can go to IDLE (recovery)
        self.add_rule(State.ERROR, State.IDLE, always_pass)
    
    def add_rule(self, from_state: State, to_state: State, guard: Callable = None) -> None:
        """Add a transition rule."""
        rule = TransitionRule(from_state, to_state, guard)
        self.rules.append(rule)
    
    def get_rule(self, from_state: State, to_state: State) -> Optional[TransitionRule]:
        """Get the transition rule for a given state change."""
        for rule in self.rules:
            if rule.from_state == from_state and rule.to_state == to_state:
                return rule
        return None
    
    def can_transition(self, from_state: State, to_state: State, machine) -> bool:
        """Check if a transition is valid (guard passes)."""
        rule = self.get_rule(from_state, to_state)
        if rule is None:
            return False
        if rule.guard is None:
            return True
        return rule.guard(machine)
    
    def execute_transition(self, machine, to_state: State) -> None:
        """Execute a transition to the target state.
        
        BUG: This method changes the state BEFORE checking the guard,
        so even invalid transitions leave the machine in the wrong state.
        """
        from_state = machine.current_state
        
        rule = self.get_rule(from_state, to_state)
        if rule is None:
            # Unknown transition - raise error
            raise TransitionError(f"No transition rule from {from_state.value} to {to_state.value}")
        
        # BUG: Change state BEFORE checking guard
        machine._set_state_internal(to_state)
        
        # Now check the guard - too late!
        if rule.guard is not None and not rule.guard(machine):
            # Guard failed - but state is already changed!
            # Rollback
            machine._set_state_internal(from_state)
            raise TransitionGuardFailed(f"Guard failed for {from_state.value} -> {to_state.value}")
    
    def list_valid_transitions(self, from_state: State) -> List[State]:
        """List all valid target states from a given state."""
        return [rule.to_state for rule in self.rules if rule.from_state == from_state]
