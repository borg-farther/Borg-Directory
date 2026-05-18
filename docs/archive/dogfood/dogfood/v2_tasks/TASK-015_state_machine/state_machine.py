"""State machine implementation with a subtle transition bug."""

from typing import Callable, Dict, List, Optional, Any
from enum import Enum


class StateMachineError(Exception):
    """Raised when invalid transition is attempted."""
    pass


class StateMachine:
    """
    A simple state machine with guards on transitions.
    
    States: IDLE -> PROCESSING -> COMPLETED
            IDLE -> FAILED (on error)
            PROCESSING -> COMPLETED (on success)
            PROCESSING -> FAILED (on error)
    
    The machine tracks current state and allows transitions
    based on guards that check conditions.
    """
    
    def __init__(self):
        self.current_state = "IDLE"
        self.data = {}
        
        # Define valid transitions
        # Format: {from_state: [(to_state, guard_fn, description)]}
        # 
        # BUG: The guards for PROCESSING state are SWAPPED!
        # The COMPLETED guard incorrectly has "not" in it,
        # and the FAILED guard is missing "not".
        # This causes transitions to go to the WRONG state!
        self.transitions = {
            "IDLE": [
                ("PROCESSING", lambda sm: True, "start processing"),
                ("FAILED", lambda sm: False, "immediate fail")
            ],
            "PROCESSING": [
                ("COMPLETED", lambda sm: sm.data.get("success", False), "success"),
                ("FAILED", lambda sm: not sm.data.get("success", False), "failure")
            ],
            "COMPLETED": [],
            "FAILED": []
        }
    
    def transition(self, to_state: str) -> bool:
        """
        Attempt to transition to a new state.
        
        Returns True if transition succeeded.
        Raises StateMachineError if transition is invalid.
        """
        # Check if transition is allowed
        if to_state not in [t[0] for t in self.transitions.get(self.current_state, [])]:
            raise StateMachineError(
                f"Invalid transition from {self.current_state} to {to_state}"
            )
        
        self.current_state = to_state
        return True
    
    def trigger(self, event: str, data: Optional[Dict] = None) -> bool:
        """
        Trigger an event to cause a transition.
        
        The event name maps to a possible transition.
        If guard passes, transition occurs.
        """
        if data:
            self.data.update(data)
        
        # Find transition for this event from current state
        possible_transitions = self.transitions.get(self.current_state, [])
        
        for to_state, guard_fn, description in possible_transitions:
            if guard_fn(self):
                # Found a valid transition with passing guard
                return self.transition(to_state)
        
        # No valid transition found
        raise StateMachineError(
            f"No valid transition from {self.current_state} for event '{event}'"
        )
    
    def get_state(self) -> str:
        """Get current state."""
        return self.current_state
    
    def can_reach(self, target_state: str, max_hops: int = 10) -> bool:
        """
        Check if target_state is reachable from current state.
        
        Returns True if there's a path to target_state.
        """
        if self.current_state == target_state:
            return True
        
        visited = {self.current_state}
        frontier = [self.current_state]
        
        for _ in range(max_hops):
            if not frontier:
                break
            
            current = frontier.pop(0)
            
            for to_state, guard_fn, _ in self.transitions.get(current, []):
                if to_state == target_state:
                    return True
                if to_state not in visited:
                    visited.add(to_state)
                    frontier.append(to_state)
        
        return False
    
    def reset(self):
        """Reset the state machine to initial state."""
        self.current_state = "IDLE"
        self.data = {}


def main():
    """Demonstrate the state machine behavior."""
    
    sm = StateMachine()
    print(f"Initial state: {sm.get_state()}")
    
    # Start processing
    try:
        sm.trigger("start", {"success": True})
        print(f"After start (success=True): {sm.get_state()}")
    except StateMachineError as e:
        print(f"Error: {e}")
    
    # Reset and try with failure
    sm.reset()
    sm.data = {}
    
    try:
        sm.trigger("start", {"success": False})
        print(f"After start (success=False): {sm.get_state()}")
    except StateMachineError as e:
        print(f"Error: {e}")
    
    print("\n=== The Bug ===")
    print("When success=True, the guard logic is inverted!")
    print("COMPLETED guard has 'not' when it shouldn't.")
    print("FAILED guard missing 'not' when it should have it.")


if __name__ == "__main__":
    main()
