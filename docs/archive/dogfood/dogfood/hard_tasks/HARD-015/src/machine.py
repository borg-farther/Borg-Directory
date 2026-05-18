"""State machine engine implementation."""

from typing import Optional, List, Dict, Any
from .states import State, StateInfo, STATE_DESCRIPTIONS
from .transitions import TransitionManager, TransitionError, TransitionGuardFailed


class StateMachineError(Exception):
    """Base exception for state machine errors."""
    pass


class InvalidTransitionError(StateMachineError):
    """Raised when an invalid transition is attempted."""
    pass


class StateMachine:
    """State machine engine with transition management.
    
    The state machine maintains:
    - current_state: The current state
    - _internal_state: An internal state that can become corrupted
    - history: Record of state transitions
    """
    
    def __init__(self, initial_state: State = State.IDLE):
        self.current_state = initial_state
        self._internal_state = initial_state  # Separate internal state
        self.transition_manager = TransitionManager()
        self.history: List[Dict[str, Any]] = []
        self.state_info: Dict[State, StateInfo] = {}
        
        # Initialize state info
        for state in State:
            self.state_info[state] = StateInfo(state, STATE_DESCRIPTIONS.get(state, ""))
        
        self._record_transition(None, initial_state, "init")
    
    def _set_state_internal(self, new_state: State) -> None:
        """Internal method to set state - used by TransitionManager.execute_transition.
        
        This modifies both current_state and _internal_state.
        """
        self.current_state = new_state
        self._internal_state = new_state
    
    def transition(self, to_state: State) -> None:
        """Attempt to transition to a new state.
        
        This will raise InvalidTransitionError if the transition is not allowed.
        """
        from_state = self.current_state
        
        try:
            self.transition_manager.execute_transition(self, to_state)
            self._record_transition(from_state, to_state, "success")
        except (TransitionError, TransitionGuardFailed) as e:
            self._record_transition(from_state, to_state, f"failed: {e}")
            raise InvalidTransitionError(f"Transition from {from_state.value} to {to_state.value} failed: {e}")
    
    def _record_transition(self, from_state: Optional[State], to_state: State, result: str) -> None:
        """Record a transition attempt in history."""
        self.history.append({
            "from": from_state.value if from_state else None,
            "to": to_state.value,
            "result": result
        })
    
    def get_state(self) -> State:
        """Get the current state (reports as correct)."""
        return self.current_state
    
    def get_internal_state(self) -> State:
        """Get the internal state (can be corrupted)."""
        return self._internal_state
    
    def is_valid_state(self) -> bool:
        """Check if reported state matches internal state."""
        return self.current_state == self._internal_state
    
    def get_history(self) -> List[Dict[str, Any]]:
        """Get the transition history."""
        return self.history.copy()
    
    def reset(self) -> None:
        """Reset the state machine to initial state."""
        self.current_state = State.IDLE
        self._internal_state = State.IDLE
        self.history.clear()
        self._record_transition(None, State.IDLE, "reset")
    
    def get_available_transitions(self) -> List[State]:
        """Get list of states that can be transitioned to from current state."""
        return self.transition_manager.list_valid_transitions(self.current_state)
    
    def __repr__(self) -> str:
        return f"StateMachine(state={self.current_state.value}, internal={self._internal_state.value})"
