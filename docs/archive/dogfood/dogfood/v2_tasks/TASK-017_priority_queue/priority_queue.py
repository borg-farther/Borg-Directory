"""Priority queue implementation with a subtle comparison bug."""

import heapq
from typing import Any, List, Optional, Tuple


class PriorityQueue:
    """
    A priority queue that supports custom priority values.
    
    Lower priority number = higher priority (comes out first).
    
    Items are stored as (priority, counter, item) tuples.
    The counter ensures FIFO ordering for items with equal priority.
    """
    
    def __init__(self):
        self._heap: List[Tuple[int, int, Any]] = []
        self._counter = 0  # Tiebreaker for same priority (FIFO)
    
    def push(self, item: Any, priority: int = 0):
        """
        Add an item to the queue with given priority.
        
        Args:
            item: Item to add
            priority: Priority value (lower = higher priority)
        """
        entry = (priority, self._counter, item)
        self._counter += 1
        heapq.heappush(self._heap, entry)
    
    def pop(self) -> Optional[Any]:
        """
        Remove and return the highest priority item.
        
        Returns None if queue is empty.
        """
        if not self._heap:
            return None
        
        # Pop returns (priority, counter, item)
        _, _, item = heapq.heappop(self._heap)
        return item
    
    def peek(self) -> Optional[Any]:
        """
        View the highest priority item without removing it.
        
        Returns None if queue is empty.
        """
        if not self._heap:
            return None
        
        _, _, item = self._heap[0]
        return item
    
    def size(self) -> int:
        """Return the number of items in the queue."""
        return len(self._heap)
    
    def is_empty(self) -> bool:
        """Return True if queue is empty."""
        return len(self._heap) == 0
    
    def get_priority(self, item: Any) -> Optional[int]:
        """
        Get the priority of an item.
        
        Returns None if item is not in queue.
        """
        for prio, queued_item in self._heap:
            if queued_item == item:
                return prio
        return None


class TaskScheduler:
    """
    A task scheduler using priority queue.
    
    Tasks with lower priority number execute first.
    """
    
    def __init__(self):
        self.queue = PriorityQueue()
    
    def schedule_task(self, task_name: str, priority: int):
        """Schedule a task with given priority."""
        self.queue.push(task_name, priority)
    
    def execute_next(self) -> Optional[str]:
        """Execute (pop) the next task."""
        task = self.queue.pop()
        if task:
            print(f"Executing: {task}")
        return task
    
    def show_next(self) -> Optional[str]:
        """Show the next task without executing."""
        return self.queue.peek()


def main():
    """Demonstrate the priority queue behavior."""
    
    scheduler = TaskScheduler()
    
    # Schedule tasks with different priorities
    scheduler.schedule_task("low_priority_task", priority=10)
    scheduler.schedule_task("high_priority_task", priority=1)
    scheduler.schedule_task("medium_priority_task", priority=5)
    scheduler.schedule_task("another_high", priority=1)
    
    print("=== Task Scheduling Demo ===\n")
    
    print("Scheduled tasks (priority, name):")
    print("- high_priority_task: priority=1")
    print("- another_high: priority=1") 
    print("- medium_priority_task: priority=5")
    print("- low_priority_task: priority=10")
    
    print("\nExecution order should be:")
    print("1. high_priority_task (priority=1)")
    print("2. another_high (priority=1, tiebreaker)")
    print("3. medium_priority_task (priority=5)")
    print("4. low_priority_task (priority=10)")
    
    print("\nActual execution:")
    while not scheduler.queue.is_empty():
        scheduler.execute_next()
    
    print("\n=== The Bug ===")
    print("With two tasks at priority=1, the order depends on")
    print("alphabetical comparison of item names, not FIFO!")


if __name__ == "__main__":
    main()
