"""Executes tasks in dependency order."""

from typing import Dict, List, Any, Set
from collections import defaultdict

from .scheduler import Scheduler
from .tasks import TaskRegistry, TaskDefinition


class ExecutionResult:
    """Result of task execution."""
    
    def __init__(self):
        self.execution_order: List[str] = []
        self.execution_counts: Dict[str, int] = defaultdict(int)
        self.results: Dict[str, Any] = {}
    
    def record_execution(self, task_id: str, result: Any = None) -> None:
        """Record that a task was executed."""
        self.execution_order.append(task_id)
        self.execution_counts[task_id] += 1
        if result is not None:
            self.results[task_id] = result


class Executor:
    """
    Executes tasks in dependency order.
    
    Uses the scheduler which has the diamond dependency bug.
    """
    
    def __init__(self, registry: TaskRegistry):
        self._registry = registry
        self._scheduler = Scheduler()
        
        # Initialize scheduler with tasks from registry
        for task_id, task_def in registry.get_all().items():
            self._scheduler.add_task(task_id, priority=0)
            for dep in task_def.dependencies:
                self._scheduler.add_dependency(task_id, dep)
    
    def execute_all(self) -> ExecutionResult:
        """
        Execute all tasks.
        
        BUG: Due to scheduler not handling diamond dependencies,
        tasks like D in a diamond (A->B->D, A->C->D) will be
        executed multiple times.
        """
        result = ExecutionResult()
        
        # Get execution order from scheduler
        order = self._scheduler.schedule()
        
        # Execute each task in order
        for task_id in order:
            task_def = self._registry.get(task_id)
            if task_def and task_def.action:
                # Execute the task's action
                task_result = task_def.action()
                result.record_execution(task_id, task_result)
            else:
                result.record_execution(task_id)
        
        return result
    
    def execute_task(self, task_id: str) -> Any:
        """Execute a single task."""
        task_def = self._registry.get(task_id)
        if task_def and task_def.action:
            return task_def.action()
        return None
