"""Manager that creates and destroys observables, exposing the memory leak."""

import gc
import sys
from typing import Dict, List

from .observable import Observable
from .observers import EventCounter, EventLogger


class ObservableManager:
    """Manages creation and destruction of observables.
    
    Due to the strong reference bug in Observable, when observables
    are destroyed, their observers are not garbage collected because
    the observable still holds references to them.
    """
    
    def __init__(self):
        self.observables: Dict[int, Observable] = {}
        self.observers: Dict[int, EventCounter] = {}
        self._creation_order: List[int] = []
    
    def create_observable(self, observer: EventCounter = None) -> Observable:
        """Create a new observable and optionally register an observer."""
        obs = Observable()
        obs_id = id(obs)
        self.observables[obs_id] = obs
        self._creation_order.append(obs_id)
        
        if observer:
            obs.add_observer(observer)
            self.observers[id(observer)] = observer
        
        return obs
    
    def destroy_observable(self, obs: Observable) -> None:
        """Destroy an observable by removing all observers and clearing."""
        obs_id = id(obs)
        if obs_id in self.observables:
            del self.observables[obs_id]
        if obs_id in self._creation_order:
            self._creation_order.remove(obs_id)
    
    def create_batch(self, count: int) -> List[Observable]:
        """Create multiple observables with observers."""
        result = []
        for _ in range(count):
            obs = Observable()
            observer = EventCounter(f"obs_{len(self._creation_order)}")
            obs.add_observer(observer)
            obs_id = id(obs)
            self.observables[obs_id] = obs
            self.observers[id(observer)] = observer
            self._creation_order.append(obs_id)
            result.append(obs)
        return result
    
    def destroy_all(self) -> None:
        """Attempt to destroy all observables."""
        self.observables.clear()
        gc.collect()
    
    def get_memory_stats(self) -> Dict[str, int]:
        """Return memory statistics."""
        return {
            "observable_count": len(self.observables),
            "observer_count": len(self.observers),
            "total_created": len(self._creation_order)
        }


def create_and_destroy_many(manager: ObservableManager, count: int) -> Dict[str, int]:
    """Create many observables with observers, then destroy them.
    
    This function demonstrates the memory leak: even after destroy_all(),
    the observer count remains high because Observable holds strong refs.
    """
    observables = manager.create_batch(count)
    manager.destroy_all()
    
    # Force garbage collection
    gc.collect()
    
    return manager.get_memory_stats()
