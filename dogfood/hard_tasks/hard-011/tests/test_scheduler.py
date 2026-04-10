"""Tests for task scheduler diamond dependency bug."""

import pytest
from src.scheduler import Scheduler
from src.tasks import TaskRegistry, TaskDefinition, create_diamond_tasks
from src.executor import Executor, ExecutionResult


def test_scheduler_basic_dependencies():
    """Test basic dependency scheduling."""
    scheduler = Scheduler()
    
    scheduler.add_task("A")
    scheduler.add_task("B")
    scheduler.add_task("C")
    
    scheduler.add_dependency("B", "A")  # B depends on A
    scheduler.add_dependency("C", "B")  # C depends on B
    
    order = scheduler.schedule()
    
    # A should come before B, B should come before C
    assert order.index("A") < order.index("B")
    assert order.index("B") < order.index("C")


def test_scheduler_simple_chain():
    """Test a simple chain of dependencies."""
    scheduler = Scheduler()
    
    scheduler.add_task("A")
    scheduler.add_task("B")
    scheduler.add_dependency("B", "A")
    
    order = scheduler.schedule()
    
    assert len(order) == 2
    assert order.index("A") < order.index("B")


def test_diamond_dependency_executes_once():
    """
    Test that diamond dependencies execute each task once.
    
    Diamond:   A
             / \
            B   C
             \ /
              D
    
    Expected order: A, then B and C (in some order), then D
    D should appear exactly ONCE.
    """
    scheduler = Scheduler()
    
    # Create diamond
    scheduler.add_task("A")
    scheduler.add_task("B")
    scheduler.add_task("C")
    scheduler.add_task("D")
    
    scheduler.add_dependency("B", "A")
    scheduler.add_dependency("C", "A")
    scheduler.add_dependency("D", "B")
    scheduler.add_dependency("D", "C")
    
    order = scheduler.schedule()
    
    # Count occurrences of each task
    a_count = order.count("A")
    b_count = order.count("B")
    c_count = order.count("C")
    d_count = order.count("D")
    
    # Each task should appear exactly once
    assert a_count == 1, f"A appeared {a_count} times, expected 1"
    assert b_count == 1, f"B appeared {b_count} times, expected 1"
    assert c_count == 1, f"C appeared {c_count} times, expected 1"
    assert d_count == 1, f"D appeared {d_count} times, expected 1"


def test_diamond_with_executor():
    """
    Test diamond dependency with executor that tracks side effects.
    
    BUG: D should execute exactly once, but due to scheduler bug it executes twice.
    """
    registry = create_diamond_tasks()
    executor = Executor(registry)
    
    result = executor.execute_all()
    
    # D should execute exactly once
    assert result.execution_counts["D"] == 1, \
        f"D executed {result.execution_counts['D']} times, expected 1"
    
    # All other tasks should execute once
    assert result.execution_counts["A"] == 1
    assert result.execution_counts["B"] == 1
    assert result.execution_counts["C"] == 1


def test_execution_order_respects_dependencies():
    """Test that execution order respects dependencies."""
    registry = TaskRegistry()
    
    execution_order = []
    
    registry.register("A", set(), lambda: execution_order.append("A"))
    registry.register("B", {"A"}, lambda: execution_order.append("B"))
    registry.register("C", {"A"}, lambda: execution_order.append("C"))
    registry.register("D", {"B", "C"}, lambda: execution_order.append("D"))
    
    executor = Executor(registry)
    result = executor.execute_all()
    
    # A must come before B and C
    assert result.execution_order.index("A") < result.execution_order.index("B")
    assert result.execution_order.index("A") < result.execution_order.index("C")
    # D must come after B and C
    assert result.execution_order.index("B") < result.execution_order.index("D")
    assert result.execution_order.index("C") < result.execution_order.index("D")
    
    # D should appear exactly once
    d_occurrences = result.execution_order.count("D")
    assert d_occurrences == 1, f"D appeared {d_occurrences} times"


def test_complex_diamond():
    """
    Test a more complex diamond pattern.
    
        A
       /|\
      B C D
       \|/
        E
       / \
      F   G
    
    E should appear exactly once.
    """
    scheduler = Scheduler()
    
    tasks = ["A", "B", "C", "D", "E", "F", "G"]
    for task in tasks:
        scheduler.add_task(task)
    
    # A is root
    # B, C, D depend on A
    scheduler.add_dependency("B", "A")
    scheduler.add_dependency("C", "A")
    scheduler.add_dependency("D", "A")
    
    # E depends on B, C, D
    scheduler.add_dependency("E", "B")
    scheduler.add_dependency("E", "C")
    scheduler.add_dependency("E", "D")
    
    # F, G depend on E
    scheduler.add_dependency("F", "E")
    scheduler.add_dependency("G", "E")
    
    order = scheduler.schedule()
    
    # E should appear exactly once
    e_count = order.count("E")
    assert e_count == 1, f"E appeared {e_count} times, expected 1"
