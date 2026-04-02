#!/usr/bin/env python3
"""
Helper script to manually record experiment results.

Usage:
    python3 record_result.py <task_id> <condition> <success> <tokens> <time_seconds> <tool_calls> [borg_searches]

Examples:
    python3 record_result.py DEBUG-001 control true 15000 300.0 25
    python3 record_result.py DEBUG-001 treatment true 12000 250.0 30 5
    python3 record_result.py TEST-001 control false 5000 1800.0 50

Arguments:
    task_id        Task identifier (e.g., DEBUG-001)
    condition      'control' or 'treatment'
    success        'true' or 'false' (case insensitive)
    tokens         Estimated token count (integer or float)
    time_seconds   Wall clock time in seconds (float)
    tool_calls     Number of tool invocations (integer)
    borg_searches  Number of borg_search calls (optional, default: 0 for control, -1 for treatment if not provided)
"""

import argparse
import json
import sys
from datetime import datetime, timezone
from pathlib import Path

EXPERIMENT_ID = "borg-ab-001"
RESULTS_FILE = "/root/hermes-workspace/borg/dogfood/results.json"


def load_results() -> dict:
    """Load existing results or create new structure."""
    results_path = Path(RESULTS_FILE)
    
    if results_path.exists():
        try:
            with open(results_path, 'r') as f:
                data = json.load(f)
            # Validate structure
            if 'experiment_id' not in data or 'results' not in data:
                print(f"Warning: Invalid results file structure, creating new")
                data = {
                    'experiment_id': EXPERIMENT_ID,
                    'started_at': datetime.now(timezone.utc).isoformat(),
                    'results': []
                }
            return data
        except json.JSONDecodeError as e:
            print(f"Warning: Corrupted results file, creating new: {e}")
            data = {
                'experiment_id': EXPERIMENT_ID,
                'started_at': datetime.now(timezone.utc).isoformat(),
                'results': []
            }
            return data
    else:
        return {
            'experiment_id': EXPERIMENT_ID,
            'started_at': datetime.now(timezone.utc).isoformat(),
            'results': []
        }


def save_results(data: dict) -> None:
    """Save results to file."""
    results_path = Path(RESULTS_FILE)
    
    # Ensure directory exists
    results_path.parent.mkdir(parents=True, exist_ok=True)
    
    with open(results_path, 'w') as f:
        json.dump(data, f, indent=2)


def validate_task_id(task_id: str) -> bool:
    """Validate task_id format."""
    # Expected format: CATEGORY-XXX (e.g., DEBUG-001, TEST-002, CONTROL-005)
    if not task_id or len(task_id) < 8:
        return False
    parts = task_id.rsplit('-', 1)
    if len(parts) != 2:
        return False
    category, number = parts
    if not category.isupper() or len(category) < 3:
        return False
    if not number.isdigit() or len(number) != 3:
        return False
    return True


def validate_condition(condition: str) -> bool:
    """Validate condition value."""
    return condition.lower() in ('control', 'treatment')


def record_result(
    task_id: str,
    condition: str,
    success: bool,
    tokens_used: float,
    time_seconds: float,
    tool_calls: int,
    borg_searches: int = None,
    order: int = None,
    error: str = None
) -> dict:
    """
    Record a single experiment result.
    
    Returns the result dict that was recorded.
    """
    # Validate inputs
    if not validate_task_id(task_id):
        raise ValueError(f"Invalid task_id format: {task_id}. Expected format: CATEGORY-XXX")
    
    condition = condition.lower()
    if not validate_condition(condition):
        raise ValueError(f"Invalid condition: {condition}. Must be 'control' or 'treatment'")
    
    # Determine order and borg_searches if not provided
    if order is None:
        # Load existing results to find how many runs for this task
        data = load_results()
        existing_runs = [r for r in data['results'] if r['task_id'] == task_id]
        order = len(existing_runs) + 1
    
    if borg_searches is None:
        if condition == 'control':
            borg_searches = 0
        else:
            borg_searches = -1  # Unknown until actual run
    
    # Build result record
    result = {
        'task_id': task_id,
        'condition': condition,
        'order': order,
        'success': success,
        'tokens_used': int(tokens_used) if tokens_used == int(tokens_used) else tokens_used,
        'time_seconds': round(time_seconds, 2),
        'tool_calls': tool_calls,
        'borg_searches': borg_searches,
        'error': error,
        'recorded_at': datetime.now(timezone.utc).isoformat()
    }
    
    # Load and update results
    data = load_results()
    data['results'].append(result)
    save_results(data)
    
    return result


def main():
    parser = argparse.ArgumentParser(
        description='Record a manual experiment result',
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
    python3 record_result.py DEBUG-001 control true 15000 300.0 25
    python3 record_result.py DEBUG-001 treatment true 12000 250.0 30 5
    python3 record_result.py TEST-001 control false 5000 1800.0 50
        """
    )
    
    parser.add_argument('task_id', type=str, help='Task identifier (e.g., DEBUG-001)')
    parser.add_argument('condition', type=str, help='Condition: control or treatment')
    parser.add_argument('success', type=str, help='Success: true or false')
    parser.add_argument('tokens', type=float, help='Estimated tokens used')
    parser.add_argument('time_seconds', type=float, help='Wall clock time in seconds')
    parser.add_argument('tool_calls', type=int, help='Number of tool invocations')
    parser.add_argument('borg_searches', type=int, nargs='?', default=None,
                       help='Number of borg_search calls (optional)')
    parser.add_argument('--order', type=int, default=None,
                       help='Run order for this task (auto-detected if not provided)')
    parser.add_argument('--error', type=str, default=None,
                       help='Error message if task failed')
    parser.add_argument('--results-file', type=str, default=RESULTS_FILE,
                       help=f'Path to results file (default: {RESULTS_FILE})')
    
    args = parser.parse_args()
    
    # Parse success
    success = args.success.lower() in ('true', 'yes', '1', 't', 'y')
    
    # Validate
    if not validate_task_id(args.task_id):
        print(f"Error: Invalid task_id format: {args.task_id}")
        print("Expected format: CATEGORY-XXX (e.g., DEBUG-001, TEST-002)")
        sys.exit(1)
    
    if not validate_condition(args.condition):
        print(f"Error: Invalid condition: {args.condition}")
        print("Must be 'control' or 'treatment'")
        sys.exit(1)
    
    # Record result
    try:
        result = record_result(
            task_id=args.task_id,
            condition=args.condition,
            success=success,
            tokens_used=args.tokens,
            time_seconds=args.time_seconds,
            tool_calls=args.tool_calls,
            borg_searches=args.borg_searches,
            order=args.order,
            error=args.error
        )
        
        print(f"✓ Result recorded:")
        print(f"  Task: {result['task_id']}")
        print(f"  Condition: {result['condition']}")
        print(f"  Order: {result['order']}")
        print(f"  Success: {result['success']}")
        print(f"  Tokens: {result['tokens_used']}")
        print(f"  Time: {result['time_seconds']}s")
        print(f"  Tool calls: {result['tool_calls']}")
        print(f"  Borg searches: {result['borg_searches']}")
        if result['error']:
            print(f"  Error: {result['error']}")
        
        # Show total results count
        data = load_results()
        print(f"\nTotal results recorded: {len(data['results'])}")
        
    except Exception as e:
        print(f"Error recording result: {e}")
        sys.exit(1)


if __name__ == '__main__':
    main()
