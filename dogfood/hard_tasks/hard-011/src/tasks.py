"""Task definitions with dependencies."""

from dataclasses import dataclass, field
from typing import Set, Dict, Any, Callable


@dataclass
class TaskDefinition:
    """Definition of a task with its dependencies."""
    
    task_id: str
    dependencies: Set[str] = field(default_factory=set)
    action: Callable[[], Any] = field(default=None)
    side_effects: int = 0  # Track how many times this task was executed


class TaskRegistry:
    """Registry for task definitions."""
    
    def __init__(self):
        self._tasks: Dict[str, TaskDefinition] = {}
    
    def register(self, task_id: str, dependencies: Set[str] = None, action: Callable = None) -> TaskDefinition:
        """Register a task."""
        if dependencies is None:
            dependencies = set()
        
        task = TaskDefinition(
            task_id=task_id,
            dependencies=dependencies,
            action=action or (lambda: None)
        )
        self._tasks[task_id] = task
        return task
    
    def get(self, task_id: str) -> TaskDefinition:
        """Get a task by ID."""
        return self._tasks.get(task_id)
    
    def get_all(self) -> Dict[str, TaskDefinition]:
        """Get all tasks."""
        return self._tasks.copy()
    
    def clear(self) -> None:
        """Clear all tasks."""
        self._tasks.clear()


def create_diamond_tasks() -> TaskRegistry:
    """
    Create a diamond dependency task set:
    
        A
       / \
      B   C
       \ /
        D
    
    A -> B, A -> C, B -> D, C -> D
    """
    registry = TaskRegistry()
    
    # Track execution count for D
    d_execution_count = [0]
    
    def task_d_action():
        d_execution_count[0] += 1
        return d_execution_count[0]
    
    registry.register("A", set())
    registry.register("B", {"A"})
    registry.register("C", {"A"})
    registry.register("D", {"B", "C"}, task_d_action)
    
    return registry
