#!/bin/bash
# TASK-017: Priority queue with comparison function not maintaining heap property

mkdir -p /root/hermes-workspace/borg/dogfood/v2_tasks/TASK-017_priority_queue

cat > /root/hermes-workspace/borg/dogfood/v2_tasks/TASK-017_priority_queue/priority_queue.py << 'EOF'
"""Priority queue implementation with a subtle comparison bug."""

import heapq
from typing import Any, List, Optional, Tuple


class PriorityQueue:
    """
    A priority queue that supports custom priority values.
    
    Lower priority number = higher priority (comes out first).
    
    Items are stored as (priority, item) tuples - but there's a bug!
    """
    
    def __init__(self):
        self._heap: List[Tuple[int, Any]] = []
    
    def push(self, item: Any, priority: int = 0):
        """
        Add an item to the queue with given priority.
        
        Args:
            item: Item to add
            priority: Priority value (lower = higher priority)
        """
        # BUG: We use (priority, item) without a tiebreaker counter!
        # When two items have the same priority, Python compares the items.
        # String comparison is alphabetical, not FIFO!
        # This violates the heap property for equal priorities.
        entry = (priority, item)
        heapq.heappush(self._heap, entry)
    
    def pop(self) -> Optional[Any]:
        """
        Remove and return the highest priority item.
        
        Returns None if queue is empty.
        """
        if not self._heap:
            return None
        
        # Pop returns (priority, item)
        _, item = heapq.heappop(self._heap)
        return item
    
    def peek(self) -> Optional[Any]:
        """
        View the highest priority item without removing it.
        
        Returns None if queue is empty.
        """
        if not self._heap:
            return None
        
        _, item = self._heap[0]
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
EOF

cat > /root/hermes-workspace/borg/dogfood/v2_tasks/TASK-017_priority_queue/test_priority_queue.py << 'EOF'
"""Test cases for priority queue."""
import sys
sys.path.insert(0, '/root/hermes-workspace/borg/dogfood/v2_tasks/TASK-017_priority_queue')

from priority_queue import PriorityQueue, TaskScheduler


def test_empty_queue():
    """Test operations on empty queue."""
    pq = PriorityQueue()
    assert pq.is_empty()
    assert pq.size() == 0
    assert pq.pop() is None
    assert pq.peek() is None
    print("test_empty_queue: PASS")


def test_single_item():
    """Test queue with single item."""
    pq = PriorityQueue()
    pq.push("task1", priority=5)
    
    assert not pq.is_empty()
    assert pq.size() == 1
    assert pq.peek() == "task1"
    assert pq.pop() == "task1"
    assert pq.is_empty()
    print("test_single_item: PASS")


def test_priority_order():
    """Test that lower priority number = higher priority (comes out first)."""
    pq = PriorityQueue()
    
    pq.push("low", priority=10)   # Low priority
    pq.push("high", priority=1)   # High priority
    pq.push("medium", priority=5) # Medium priority
    
    # Should come out in priority order
    assert pq.pop() == "high", "First should be high priority (1)"
    assert pq.pop() == "medium", "Second should be medium priority (5)"
    assert pq.pop() == "low", "Third should be low priority (10)"
    
    print("test_priority_order: PASS")


def test_same_priority_fifo():
    """
    Test that items with same priority come out in FIFO order.
    
    BUG: Due to using (priority, item) tuple without tiebreaker,
    items with same priority are ordered by string comparison (alphabetical),
    not by insertion order!
    """
    pq = PriorityQueue()
    
    # Add three items with same priority
    pq.push("first", priority=5)
    pq.push("second", priority=5)
    pq.push("third", priority=5)
    
    # They should come out in FIFO order: first, second, third
    # But with the bug, they come out alphabetically: first, second, third
    # Actually "first", "second", "third" IS alphabetical!
    # We need items where alphabetical != FIFO order
    
    pq2 = PriorityQueue()
    pq2.push("zeta", priority=5)   # Added first but comes last alphabetically
    pq2.push("alpha", priority=5)  # Added second but comes first alphabetically
    pq2.push("beta", priority=5)   # Added third but comes second alphabetically
    
    # FIFO order should be: zeta, alpha, beta (insertion order)
    # But alphabetical would be: alpha, beta, zeta
    results = []
    while not pq2.is_empty():
        results.append(pq2.pop())
    
    assert results == ["zeta", "alpha", "beta"], \
        f"Expected FIFO order ['zeta', 'alpha', 'beta'], got {results}"
    
    print("test_same_priority_fifo: PASS")


def test_interleaved_priorities():
    """Test with interleaved priority values."""
    pq = PriorityQueue()
    
    pq.push("A", priority=3)
    pq.push("B", priority=1)
    pq.push("C", priority=4)
    pq.push("D", priority=1)
    pq.push("E", priority=2)
    
    # Should come out: B(1), D(1), E(2), A(3), C(4)
    # B and D both priority 1, should be FIFO (B before D)
    
    expected = ["B", "D", "E", "A", "C"]
    results = []
    while not pq.is_empty():
        results.append(pq.pop())
    
    assert results == expected, f"Expected {expected}, got {results}"
    print("test_interleaved_priorities: PASS")


def test_task_scheduler():
    """Test the task scheduler integration."""
    scheduler = TaskScheduler()
    
    scheduler.schedule_task("task_low", 100)
    scheduler.schedule_task("task_high", 1)
    scheduler.schedule_task("task_medium", 50)
    scheduler.schedule_task("task_urgent", 5)
    
    # High priority should come first
    assert scheduler.execute_next() == "task_high"
    assert scheduler.execute_next() == "task_urgent"
    assert scheduler.execute_next() == "task_medium"
    assert scheduler.execute_next() == "task_low"
    
    print("test_task_scheduler: PASS")


def test_negative_priorities():
    """Test with negative priorities (higher values mean lower priority)."""
    pq = PriorityQueue()
    
    pq.push("neg_high", priority=-10)  # Very high priority
    pq.push("neg_low", priority=-1)    # Lower priority
    pq.push("zero", priority=0)
    pq.push("pos_low", priority=5)
    
    # Should come out: neg_high(-10), neg_low(-1), zero(0), pos_low(5)
    assert pq.pop() == "neg_high"
    assert pq.pop() == "neg_low"
    assert pq.pop() == "zero"
    assert pq.pop() == "pos_low"
    
    print("test_negative_priorities: PASS")


if __name__ == "__main__":
    test_empty_queue()
    test_single_item()
    test_priority_order()
    test_same_priority_fifo()
    test_interleaved_priorities()
    test_task_scheduler()
    test_negative_priorities()
    print("\nAll tests passed!")
EOF
