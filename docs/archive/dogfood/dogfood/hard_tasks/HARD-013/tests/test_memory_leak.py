"""Tests for HARD-013: Observer Pattern Memory Leak.

These tests verify that observers are properly garbage collected when
observables are destroyed. They should FAIL due to the memory leak bug.
"""

import gc
import weakref
import pytest

from src.observable import Observable
from src.observers import EventCounter, EventLogger
from src.manager import ObservableManager, create_and_destroy_many


class TestObserverMemoryLeak:
    """Tests demonstrating the memory leak in observer pattern."""
    
    def test_weak_reference_should_work(self):
        """Test that weak references to observers work correctly.
        
        This test uses weak references and should PASS - it demonstrates
        the correct behavior that the buggy code doesn't follow.
        """
        obs = Observable()
        observer = EventCounter("test")
        weak_ref = weakref.ref(observer)
        
        obs.add_observer(observer)
        
        # Delete the strong reference
        del observer
        gc.collect()
        
        # With proper weak reference implementation, this would be None
        # But since Observable stores strong refs, the observer still exists
        # This assertion should FAIL because the observer is still alive
        assert weak_ref() is None, "Observer should have been garbage collected"
    
    def test_observer_count_after_cleanup(self):
        """Test that observer count is zero after destroying observables."""
        manager = ObservableManager()
        manager.create_batch(10)
        
        initial_stats = manager.get_memory_stats()
        assert initial_stats["observer_count"] == 10
        
        manager.destroy_all()
        gc.collect()
        
        # After destroy_all, observer_count should be 0
        # But it remains high due to the memory leak
        final_stats = manager.get_memory_stats()
        assert final_stats["observer_count"] == 0, "Observers should have been cleaned up"
    
    def test_memory_leak_demonstration(self):
        """Demonstrate the memory leak with specific counts."""
        manager = ObservableManager()
        
        # Create and destroy many observables
        stats = create_and_destroy_many(manager, 100)
        
        # After destroying all observables, the observer count should be 0
        # But it will still be 100 due to the strong reference bug
        assert stats["observer_count"] == 0, "Memory leak: observers not freed"
        assert stats["observable_count"] == 0, "Observables should be destroyed"
    
    def test_weakref_observer_collection(self):
        """Test that observers can be garbage collected when not referenced elsewhere."""
        obs = Observable()
        weak_refs = []
        
        # Create observables and observers, store only weak refs
        for i in range(5):
            obs = Observable()
            observer = EventCounter(f"obs_{i}")
            weak_refs.append(weakref.ref(observer))
            obs.add_observer(observer)
        
        # Delete strong references
        del obs
        del observer
        gc.collect()
        
        # Most weak refs should be dead if proper cleanup happened
        alive_count = sum(1 for ref in weak_refs if ref() is not None)
        assert alive_count == 0, f"Expected 0 alive observers, got {alive_count}"
    
    def test_reregister_observer_after_destroy(self):
        """Test observer behavior when observable is recreated."""
        manager = ObservableManager()
        
        obs1 = manager.create_observable()
        observer = EventCounter("shared")
        obs1.add_observer(observer)
        
        # Destroy first observable
        manager.destroy_observable(obs1)
        del obs1
        gc.collect()
        
        # Create new observable
        obs2 = manager.create_observable()
        obs2.add_observer(observer)
        
        # Notify and check
        obs2.notify_observers("test", "data")
        
        # Observer should have received the event
        assert observer.get_event_count() == 1, "Observer should receive events"
    
    def test_observer_strong_ref_count(self):
        """Test that Observable holds strong references (the bug)."""
        obs = Observable()
        observer1 = EventCounter("obs1")
        observer2 = EventLogger("obs2")
        
        obs.add_observer(observer1)
        obs.add_observer(observer2)
        
        # Check observer count
        assert obs.get_observer_count() == 2
        
        # Now delete observers and check if they're still accessible
        del observer1
        del observer2
        gc.collect()
        
        # This is the bug - observers are still registered because
        # Observable holds strong references
        # After proper fix (weak refs), this would be 0
        assert obs.get_observer_count() == 0, "BUG: Strong references prevent GC"
