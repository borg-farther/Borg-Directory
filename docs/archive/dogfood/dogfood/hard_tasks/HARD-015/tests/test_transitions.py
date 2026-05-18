"""Tests for HARD-015: State Machine Transition Bug.

These tests verify that state machine transitions with guards work correctly.
They should FAIL due to the bug where guards run AFTER state change.
"""

import pytest
from src.states import State
from src.transitions import TransitionManager, TransitionRule, TransitionGuardFailed
from src.machine import StateMachine, InvalidTransitionError


class TestStateMachineTransitions:
    """Tests for state machine transition behavior."""
    
    def test_valid_transition_idle_to_running(self):
        """Test a simple valid transition."""
        machine = StateMachine(State.IDLE)
        
        machine.transition(State.RUNNING)
        
        assert machine.get_state() == State.RUNNING
        assert machine.is_valid_state()
    
    def test_valid_transition_running_to_paused(self):
        """Test transitioning from RUNNING to PAUSED."""
        machine = StateMachine(State.RUNNING)
        
        machine.transition(State.PAUSED)
        
        assert machine.get_state() == State.PAUSED
    
    def test_invalid_transition_idle_to_paused(self):
        """Test that invalid transition is rejected."""
        machine = StateMachine(State.IDLE)
        
        # IDLE -> PAUSED is not a valid transition
        with pytest.raises(InvalidTransitionError):
            machine.transition(State.PAUSED)
        
        # State should remain IDLE
        assert machine.get_state() == State.IDLE
        assert machine.is_valid_state()
    
    def test_guard_runs_before_transition(self):
        """Test that guards are checked BEFORE state change.
        
        This test should FAIL because the bug causes guards to run
        AFTER the state change.
        """
        machine = StateMachine(State.IDLE)
        
        # Define a guard that checks we're not in IDLE
        tm = machine.transition_manager
        tm.add_rule(State.IDLE, State.STOPPED, lambda m: m.current_state != State.IDLE)
        
        # Attempt IDLE -> STOPPED (should fail because guard checks state != IDLE)
        with pytest.raises(InvalidTransitionError):
            machine.transition(State.STOPPED)
        
        # State should still be IDLE (not STOPPED)
        # BUG: Due to the bug, state might be corrupted
        assert machine.get_state() == State.IDLE, "State should remain IDLE"
        assert machine.is_valid_state(), "State should be valid"
    
    def test_state_corruption_on_guard_failure(self):
        """Test that state becomes corrupted when guard fails.
        
        This test demonstrates the bug: invalid transitions are applied
        first, then rejected, leaving the machine in a wrong state.
        """
        machine = StateMachine(State.IDLE)
        
        # Add a transition with a guard that will fail
        tm = machine.transition_manager
        tm.add_rule(State.IDLE, State.RUNNING, lambda m: m.current_state != State.IDLE)
        
        # Attempt IDLE -> RUNNING, guard should fail (because current_state is IDLE)
        # But due to bug, state changes to RUNNING first, then guard fails
        try:
            machine.transition(State.RUNNING)
        except InvalidTransitionError:
            pass
        
        # BUG: After failed transition attempt, state might be corrupted
        # The reported state and internal state may not match
        reported = machine.get_state()
        internal = machine.get_internal_state()
        
        # This assertion should pass (state reverts on guard failure)
        # But the internal mechanism is broken
        assert reported == State.IDLE
        assert machine.is_valid_state()
    
    def test_guard_receives_correct_current_state(self):
        """Test that guard function receives the correct current state.
        
        This test should FAIL because the bug changes state before
        running the guard.
        """
        machine = StateMachine(State.IDLE)
        
        received_states = []
        
        def guard_tracker(m):
            received_states.append(m.current_state)
            return True
        
        tm = machine.transition_manager
        tm.add_rule(State.IDLE, State.RUNNING, guard_tracker)
        
        machine.transition(State.RUNNING)
        
        # Guard should have received IDLE as current state
        assert len(received_states) == 1
        assert received_states[0] == State.IDLE, "Guard should see IDLE before transition"
    
    def test_internal_state_consistency(self):
        """Test that internal state remains consistent with reported state."""
        machine = StateMachine(State.IDLE)
        
        # Perform several valid transitions
        machine.transition(State.RUNNING)
        assert machine.is_valid_state()
        
        machine.transition(State.PAUSED)
        assert machine.is_valid_state()
        
        machine.transition(State.STOPPED)
        assert machine.is_valid_state()
        
        # All transitions should maintain consistency
        assert machine.get_state() == machine.get_internal_state()
    
    def test_history_records_transitions(self):
        """Test that transition history is recorded correctly."""
        machine = StateMachine(State.IDLE)
        
        machine.transition(State.RUNNING)
        machine.transition(State.PAUSED)
        
        history = machine.get_history()
        
        # Should have: init + 2 transitions
        assert len(history) >= 3
        
        # Check last transition
        last = history[-1]
        assert last["from"] == State.RUNNING.value
        assert last["to"] == State.PAUSED.value
        assert "success" in last["result"]
    
    def test_multiple_guard_failures(self):
        """Test multiple consecutive guard failures don't corrupt state."""
        machine = StateMachine(State.IDLE)
        
        tm = machine.transition_manager
        tm.add_rule(State.IDLE, State.ERROR, lambda m: m.current_state != State.IDLE)
        
        # Try multiple times to trigger the bug
        for i in range(5):
            try:
                machine.transition(State.ERROR)
            except InvalidTransitionError:
                pass
            
            # State should always be IDLE after failed attempt
            assert machine.get_state() == State.IDLE
            assert machine.is_valid_state()
