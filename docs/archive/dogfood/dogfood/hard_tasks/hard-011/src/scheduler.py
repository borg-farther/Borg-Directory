"""Priority queue-based task scheduler."""

import heapq
from collections import defaultdict
from typing import Dict, List, Set


class Task:
    """Represents a task with dependencies."""
    
    def __init__(self, task_id: str, priority: int = 0):
        self.task_id = task_id
        self.priority = priority
        self.dependencies: Set[str] = set()
    
    def __repr__(self):
        return f"Task({self.task_id}, priority={self.priority})"
    
    def __lt__(self, other):
        return self.priority < other.priority


class Scheduler:
    """
    Priority queue-based task scheduler.
    
    BUG: Does not handle diamond dependencies correctly!
    When A->B and A->C and B->D and C->D (diamond), task D gets
    executed twice because it gets added to the ready heap once
    per path that completes, and there's no tracking of what's
    already been queued.
    """
    
    def __init__(self):
        self._tasks: Dict[str, Task] = {}
        self._dependents: Dict[str, Set[str]] = defaultdict(set)
    
    def add_task(self, task_id: str, priority: int = 0) -> None:
        """Add a task to the scheduler."""
        if task_id not in self._tasks:
            self._tasks[task_id] = Task(task_id, priority)
    
    def add_dependency(self, task_id: str, depends_on: str) -> None:
        """Add a dependency: task_id depends on depends_on."""
        if task_id not in self._tasks:
            self.add_task(task_id)
        if depends_on not in self._tasks:
            self.add_task(depends_on)
        
        self._tasks[task_id].dependencies.add(depends_on)
        self._dependents[depends_on].add(task_id)
    
    def schedule(self) -> List[str]:
        """
        Schedule tasks in dependency order.
        
        BUG: Uses remaining_deps correctly to track dependencies, but
        when diamond deps exist, D gets added to heap once per incoming
        edge (B->D and C->D). The bug is that we should check if D is
        already in the heap before adding, but we don't - we just check
        remaining_deps which becomes empty after first B->D, allowing D
        to be added again when C->D completes.
        """
        execution_order: List[str] = []
        completed: Set[str] = set()
        queued: Set[str] = set()  # BUG: This is never checked!
        
        remaining_deps: Dict[str, Set[str]] = {
            task_id: set(task.dependencies) 
            for task_id, task in self._tasks.items()
        }
        
        ready_heap: List[Task] = []
        
        for task_id, deps in remaining_deps.items():
            if not deps:
                heapq.heappush(ready_heap, self._tasks[task_id])
                queued.add(task_id)
        
        while ready_heap:
            task = heapq.heappop(ready_heap)
            
            execution_order.append(task.task_id)
            completed.add(task.task_id)
            queued.discard(task.task_id)  # Remove from queued
            
            for dependent_id in self._dependents[task.task_id]:
                if dependent_id in remaining_deps:
                    remaining_deps[dependent_id].discard(task.task_id)
                    
                    if not remaining_deps[dependent_id]:
                        heapq.heappush(ready_heap, self._tasks[dependent_id])
                        queued.add(dependent_id)  # Track but not checked!
        
        return execution_order
