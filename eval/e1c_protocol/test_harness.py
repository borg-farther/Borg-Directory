#!/usr/bin/env python3
"""
E1c Protocol — Borg CLI Usability Test Harness
Manages evaluation sessions, task execution, and data collection.

Usage:
    python test_harness.py --mode=screening    # Verify participant eligibility
    python test_harness.py --mode=session       # Run a full evaluation session
    python test_harness.py --mode=analysis      # Analyze collected data
    python test_harness.py --mode=report        # Generate summary report
"""

import argparse
import json
import os
import sys
import time
from dataclasses import dataclass, field, asdict
from datetime import datetime
from pathlib import Path
from typing import Optional

# Configuration
EVAL_DIR = Path(__file__).parent
DATA_DIR = EVAL_DIR / "data"
SESSIONS_DIR = DATA_DIR / "sessions"
TASKS_FILE = EVAL_DIR / "tasks.json"
CONFIG_FILE = EVAL_DIR / "config.json"

# Ensure directories exist
DATA_DIR.mkdir(exist_ok=True)
SESSIONS_DIR.mkdir(exist_ok=True)


@dataclass
class Task:
    """Definition of a single usability evaluation task."""
    id: str
    name: str
    description: str
    instructions: str
    expected_steps: list[str]
    expert_time_seconds: int
    success_criteria: str
    hints: list[str] = field(default_factory=list)


@dataclass
class TaskResult:
    """Results from a single task attempt."""
    task_id: str
    participant_id: str
    started_at: str
    completed_at: Optional[str] = None
    success_score: int = 0  # 1-5
    time_score: int = 0  # 1-5
    error_score: int = 0  # 1-5
    cognitive_load: int = 0  # 1-5
    seq_score: int = 0  # 1-7 (Single Ease Question)
    completed: bool = False
    prompts_given: int = 0
    error_count: int = 0
    critical_incidents: list[dict] = field(default_factory=list)
    notes: str = ""


@dataclass
class Session:
    """Full evaluation session data."""
    session_id: str
    participant_id: str
    started_at: str
    completed_at: Optional[str] = None
    screening_verified: bool = False
    consent_obtained: bool = False
    task_results: list[TaskResult] = field(default_factory=list)
    sus_score: Optional[float] = None
    post_task_responses: dict = field(default_factory=dict)
    moderator_notes: str = ""
    status: str = "pending"  # pending, in_progress, completed, abandoned


def load_tasks() -> list[Task]:
    """Load task definitions from tasks.json."""
    tasks_path = TASKS_FILE
    if not tasks_path.exists():
        # Create default tasks if file doesn't exist
        default_tasks = get_default_tasks()
        save_tasks(default_tasks)
        return default_tasks
    
    with open(tasks_path, 'r') as f:
        data = json.load(f)
        return [Task(**t) for t in data]


def save_tasks(tasks: list[Task]) -> None:
    """Save tasks to tasks.json."""
    with open(TASKS_FILE, 'w') as f:
        json.dump([asdict(t) for t in tasks], f, indent=2)


def load_config() -> dict:
    """Load configuration."""
    if CONFIG_FILE.exists():
        with open(CONFIG_FILE, 'r') as f:
            return json.load(f)
    return {
        "max_session_duration_minutes": 60,
        "min_prompts_before_help": 3,
        "expert_time_multipliers": {"optimal": 1.2, "acceptable": 2.0, "slow": 3.0},
        "random_seed": 42,
    }


def save_config(config: dict) -> None:
    """Save configuration."""
    with open(CONFIG_FILE, 'w') as f:
        json.dump(config, f, indent=2)


def get_default_tasks() -> list[Task]:
    """Return default task definitions for Borg CLI evaluation."""
    return [
        Task(
            id="e1c-t1",
            name="Initial Setup",
            description="Install and configure Borg CLI for first use.",
            instructions="Install Borg CLI and run the initial setup command to configure your API credentials.",
            expected_steps=[
                "Run: borg init",
                "Follow setup prompts",
                "Verify installation with: borg status"
            ],
            expert_time_seconds=120,
            success_criteria="borg status returns a valid response without errors",
            hints=[
                "Try 'borg init --help' to see available options",
                "Check if BORG_API_KEY environment variable is needed"
            ]
        ),
        Task(
            id="e1c-t2",
            name="Search for a Pattern",
            description="Find existing approaches for a common debugging problem.",
            instructions="Search Borg for approaches related to 'null pointer exception' debugging.",
            expected_steps=[
                "Run: borg search 'null pointer'",
                "Review results",
                "Select an approach to view"
            ],
            expert_time_seconds=60,
            success_criteria="At least one approach is displayed for null pointer exceptions",
            hints=[
                "The search syntax is: borg search <query>",
                "Results are ranked by relevance"
            ]
        ),
        Task(
            id="e1c-t3",
            name="Apply an Approach",
            description="Use an existing approach to solve a simulated problem.",
            instructions="Apply the 'debug-null-pointer' approach to a test file.",
            expected_steps=[
                "Run: borg apply debug-null-pointer",
                "Review the suggested steps",
                "Execute the recommended fix"
            ],
            expert_time_seconds=180,
            success_criteria="Approach is loaded and steps are displayed",
            hints=[
                "Try 'borg apply --list' to see available approaches",
                "Use 'borg apply <name> --dry-run' to preview"
            ]
        ),
        Task(
            id="e1c-t4",
            name="Custom Query",
            description="Ask Borg a specific question about your codebase.",
            instructions="Ask Borg how to handle rate limiting in API calls.",
            expected_steps=[
                "Run: borg suggest 'rate limiting'",
                "Interpret the suggestion",
                "Ask a follow-up if needed"
            ],
            expert_time_seconds=90,
            success_criteria="A relevant suggestion or approach is returned",
            hints=[
                "The suggest command: borg suggest <description>",
                "Be specific about your use case for better results"
            ]
        ),
        Task(
            id="e1c-t5",
            name="Feedback Loop",
            description="Provide feedback on an approach to improve Borg's knowledge.",
            instructions="After trying an approach, submit feedback about its effectiveness.",
            expected_steps=[
                "Run: borg feedback --approach debug-null-pointer",
                "Rate effectiveness",
                "Add optional notes"
            ],
            expert_time_seconds=60,
            success_criteria="Feedback is recorded and acknowledged",
            hints=[
                "Use 'borg feedback --list' to see recent approaches",
                "Honest feedback helps improve the hive"
            ]
        ),
    ]


def verify_screening(responses: dict) -> tuple[bool, list[str]]:
    """
    Verify if participant meets screening criteria.
    
    Required:
    - At least 1 year CLI experience
    - Uses CLI at least weekly
    - Has used at least 2 CLI tools
    - Comfort level >= "Somewhat comfortable"
    
    Returns: (eligible, reasons)
    """
    ineligible_reasons = []
    
    # B1: CLI experience >= 1-3 years
    cli_experience = responses.get("b1", "")
    if cli_experience in ["Never used", "Less than 1 year"]:
        ineligible_reasons.append(f"Insufficient CLI experience: {cli_experience}")
    
    # B2: CLI usage >= 3-4 days per week
    cli_frequency = responses.get("b2", "")
    if cli_frequency in ["Never", "1-2 days per week"]:
        ineligible_reasons.append(f"Insufficient CLI frequency: {cli_frequency}")
    
    # B3: At least 2 CLI tools
    cli_tools = responses.get("b3", [])
    if len(cli_tools) < 2:
        ineligible_reasons.append(f"Too few CLI tools used: {len(cli_tools)}")
    
    # B4: Comfort level >= 4 (Somewhat comfortable)
    comfort_level = responses.get("b4", 0)
    if comfort_level < 4:
        ineligible_reasons.append(f"Comfort level too low: {comfort_level}")
    
    return len(ineligible_reasons) == 0, ineligible_reasons


def calculate_time_score(elapsed_seconds: int, expert_seconds: int, config: dict) -> int:
    """Calculate time score based on expert baseline."""
    multipliers = config.get("expert_time_multipliers", {})
    ratio = elapsed_seconds / expert_seconds
    
    if ratio <= multipliers.get("optimal", 1.2):
        return 5
    elif ratio <= multipliers.get("acceptable", 2.0):
        return 4 if ratio <= 1.5 else 3
    elif ratio <= multipliers.get("slow", 3.0):
        return 2
    else:
        return 1


def calculate_sus_score(responses: dict[str, int]) -> float:
    """
    Calculate System Usability Scale score.
    
    SUS scoring: Odd items: (response - 1) * 2.5
                 Even items: (6 - response) * 2.5
    Total score: sum of all items (max 100)
    """
    sus_questions = {
        1: "odd", 2: "even", 3: "odd", 4: "even", 5: "odd",
        6: "even", 7: "odd", 8: "even", 9: "odd", 10: "even"
    }
    
    total = 0.0
    for q_num, q_type in sus_questions.items():
        response = responses.get(f"sus_{q_num}", 0)
        if q_type == "odd":
            total += (response - 1) * 2.5
        else:
            total += (6 - response) * 2.5
    
    return round(total, 1)


def run_session(participant_id: str, tasks: list[Task], config: dict) -> Session:
    """Run a complete evaluation session."""
    session_id = f"session-{participant_id}-{int(time.time())}"
    session = Session(
        session_id=session_id,
        participant_id=participant_id,
        started_at=datetime.now().isoformat(),
        status="in_progress"
    )
    
    print(f"\n{'='*60}")
    print(f"E1c Protocol — Borg CLI Usability Evaluation")
    print(f"Session ID: {session_id}")
    print(f"{'='*60}\n")
    
    print("NOTE: This is a simulated session runner for protocol testing.")
    print("In production, the moderator would run these tasks manually.\n")
    
    # Show tasks
    print("TASKS FOR THIS SESSION:\n")
    for i, task in enumerate(tasks, 1):
        print(f"  {i}. [{task.id}] {task.name}")
        print(f"     {task.description}")
        print()
    
    # Simulate task completion (for protocol testing)
    print("\n--- Simulating task completions (for harness testing) ---\n")
    
    for task in tasks:
        print(f"Processing task: {task.name}")
        
        result = TaskResult(
            task_id=task.id,
            participant_id=participant_id,
            started_at=datetime.now().isoformat(),
            completed_at=datetime.now().isoformat(),
            success_score=4,  # Simulated
            time_score=4,
            error_score=4,
            cognitive_load=3,
            seq_score=5,
            completed=True,
            prompts_given=1,
            error_count=1,
            critical_incidents=[],
            notes=""
        )
        session.task_results.append(result)
    
    # Simulate SUS score
    sus_responses = {f"sus_{i}": 4 for i in range(1, 11)}
    session.sus_score = calculate_sus_score(sus_responses)
    
    session.completed_at = datetime.now().isoformat()
    session.status = "completed"
    
    # Save session
    save_session(session)
    print(f"\nSession saved: {session_id}")
    print(f"SUS Score: {session.sus_score}")
    
    return session


def save_session(session: Session) -> None:
    """Save session data to JSON file."""
    session_file = SESSIONS_DIR / f"{session.session_id}.json"
    with open(session_file, 'w') as f:
        json.dump(asdict(session), f, indent=2)


def load_session(session_id: str) -> Optional[Session]:
    """Load session data from JSON file."""
    session_file = SESSIONS_DIR / f"{session_id}.json"
    if not session_file.exists():
        return None
    with open(session_file, 'r') as f:
        data = json.load(f)
        # Convert task_results dicts back to TaskResult objects
        data['task_results'] = [TaskResult(**tr) for tr in data.get('task_results', [])]
        return Session(**data)


def analyze_sessions() -> dict:
    """Analyze all completed sessions."""
    sessions = []
    for f in SESSIONS_DIR.glob("session-*.json"):
        with open(f) as fp:
            data = json.load(fp)
            data['task_results'] = [TaskResult(**tr) for tr in data.get('task_results', [])]
            sessions.append(Session(**data))
    
    if not sessions:
        return {"error": "No sessions found"}
    
    completed = [s for s in sessions if s.status == "completed"]
    
    # Aggregate metrics
    total_tasks = sum(len(s.task_results) for s in completed)
    avg_success = sum(
        sum(t.success_score for t in s.task_results) / max(len(s.task_results), 1)
        for s in completed
    ) / max(len(completed), 1)
    
    avg_sus = sum(s.sus_score or 0 for s in completed) / max(len(completed), 1)
    
    # Count critical incidents
    total_incidents = sum(
        sum(len(t.critical_incidents) for t in s.task_results)
        for s in completed
    )
    
    return {
        "total_sessions": len(sessions),
        "completed_sessions": len(completed),
        "total_tasks_attempted": total_tasks,
        "average_task_success": round(avg_success, 2),
        "average_sus_score": round(avg_sus, 1),
        "total_critical_incidents": total_incidents,
        "sessions": [asdict(s) for s in sessions]
    }


def generate_report(analysis: dict) -> str:
    """Generate a summary report from analysis."""
    if "error" in analysis:
        return f"Error: {analysis['error']}"
    
    report = []
    report.append("=" * 60)
    report.append("E1c PROTOCOL — USABILITY EVALUATION REPORT")
    report.append("=" * 60)
    report.append("")
    report.append(f"Generated: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    report.append("")
    report.append("SUMMARY STATISTICS")
    report.append("-" * 40)
    report.append(f"  Total Sessions:           {analysis['total_sessions']}")
    report.append(f"  Completed Sessions:       {analysis['completed_sessions']}")
    report.append(f"  Total Tasks Attempted:     {analysis['total_tasks_attempted']}")
    report.append(f"  Average Task Success:     {analysis['average_task_success']}/5.0")
    report.append(f"  Average SUS Score:         {analysis['average_sus_score']}/100")
    report.append(f"  Critical Incidents:       {analysis['total_critical_incidents']}")
    report.append("")
    
    # SUS interpretation
    sus = analysis['average_sus_score']
    if sus >= 90:
        interpretation = "EXCEPTIONAL"
    elif sus >= 80:
        interpretation = "EXCELLENT"
    elif sus >= 70:
        interpretation = "GOOD"
    elif sus >= 60:
        interpretation = "OK"
    elif sus >= 50:
        interpretation = "POOR"
    else:
        interpretation = "UNACCEPTABLE"
    
    report.append(f"SUS Interpretation: {interpretation}")
    report.append("")
    report.append("=" * 60)
    
    return "\n".join(report)


def main():
    parser = argparse.ArgumentParser(description="E1c Protocol Test Harness")
    parser.add_argument("--mode", choices=["screening", "session", "analysis", "report"], 
                        default="session", help="Operation mode")
    parser.add_argument("--participant-id", help="Participant identifier")
    parser.add_argument("--session-id", help="Session identifier (for loading)")
    parser.add_argument("--tasks", help="Path to custom tasks.json")
    
    args = parser.parse_args()
    
    # Handle custom tasks file
    global TASKS_FILE
    if args.tasks:
        TASKS_FILE = Path(args.tasks)
    
    config = load_config()
    tasks = load_tasks()
    
    if args.mode == "screening":
        print("E1c Screening Verification Tool")
        print("-" * 40)
        print("Enter screening responses (or provide JSON):")
        
        # For testing, use mock responses
        test_responses = {
            "b1": "1-3 years",  # CLI experience
            "b2": "Daily",       # CLI frequency
            "b3": ["git", "docker", "npm"],  # CLI tools
            "b4": 4,  # Comfort level
        }
        
        eligible, reasons = verify_screening(test_responses)
        print(f"\nEligibility: {'QUALIFIED' if eligible else 'NOT QUALIFIED'}")
        if not eligible:
            for r in reasons:
                print(f"  - {r}")
    
    elif args.mode == "session":
        participant_id = args.participant_id or f"p-{int(time.time())}"
        session = run_session(participant_id, tasks, config)
        print(f"\nSession complete. ID: {session.session_id}")
    
    elif args.mode == "analysis":
        analysis = analyze_sessions()
        print(json.dumps(analysis, indent=2, default=str))
    
    elif args.mode == "report":
        analysis = analyze_sessions()
        report = generate_report(analysis)
        print(report)


if __name__ == "__main__":
    main()