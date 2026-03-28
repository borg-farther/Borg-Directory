"""
Change Awareness for Borg Brain — Detect recent git changes and cross-reference with errors.

Phase 4 of Borg Brain spec: https://www.notion.so/hermes-lab/Borg-Brain-Spec-1-0-f01d1c7c21a4808085bd40e140c1b0f4
"""

from __future__ import annotations

import subprocess
import time
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, List, Optional


def detect_recent_changes(project_path: str = '.', hours: int = 24) -> dict:
    """Detect recent git changes in a project.

    Runs git commands to detect recent changes. Returns immediately with empty
    results if not a git repo or if git is unavailable.

    Args:
        project_path: Path to the git repository. Defaults to '.'.
        hours: Look for changes in the last N hours. Defaults to 24.

    Returns:
        A dict with keys:
        - is_git_repo: bool — True if project_path is a git repo
        - recent_files: list of dicts with path (str) and hours_ago (float)
        - uncommitted: list of str — uncommitted changed file paths
        - last_commits: list of dicts with hash (str), message (str), hours_ago (float)
          (up to 5 commits)
    """
    result = {
        'is_git_repo': False,
        'recent_files': [],
        'uncommitted': [],
        'last_commits': [],
    }

    # Validate project_path
    repo_root = Path(project_path).resolve()
    if not repo_root.exists():
        return result

    # Check if it's a git repo
    try:
        git_dir = repo_root / ".git"
        if not git_dir.is_dir():
            return result
    except (OSError, PermissionError):
        return result

    start_time = time.time()
    cutoff_time = start_time - (hours * 3600)

    def run_git(cmd: List[str], cwd: Path = repo_root, timeout: float = 1.5) -> Optional[str]:
        """Run a git command and return stdout, or None on failure."""
        try:
            proc = subprocess.run(
                cmd,
                cwd=cwd,
                capture_output=True,
                text=True,
                timeout=timeout,
            )
            if proc.returncode == 0:
                return proc.stdout.strip()
            return None
        except (subprocess.TimeoutExpired, FileNotFoundError, PermissionError, OSError):
            return None

    # Check git repo
    git_check = run_git(["git", "rev-parse", "--is-inside-work-tree"], timeout=1.0)
    if git_check != "true":
        return result

    result['is_git_repo'] = True

    # Get recent files changed in last N hours
    # Use git log with --name-only to get files, since --since doesn't work with --name-only nicely
    # We use --pretty to get commits and --name-only for files
    since_str = f"{hours} hours ago"
    log_output = run_git(
        ["git", "log", f"--since={since_str}", "--format=%H %ct", "--name-only"],
        timeout=1.5,
    )
    if log_output:
        current_commit_hash = None
        current_commit_time = None
        for line in log_output.split('\n'):
            if not line.strip():
                continue
            parts = line.split(' ', 1)
            if len(parts) == 2 and len(parts[0]) == 40:
                # This is a commit hash line
                current_commit_hash = parts[0]
                try:
                    current_commit_time = int(parts[1])
                except ValueError:
                    current_commit_time = None
            elif current_commit_hash and current_commit_time:
                # This is a file path
                file_path = line.strip()
                if file_path:
                    file_time = datetime.fromtimestamp(current_commit_time, tz=timezone.utc)
                    hours_ago = (start_time - current_commit_time) / 3600
                    if hours_ago <= hours:
                        result['recent_files'].append({
                            'path': file_path,
                            'hours_ago': round(hours_ago, 2),
                        })

    # Get uncommitted changes
    status_output = run_git(["git", "status", "--porcelain"], timeout=1.0)
    if status_output:
        for line in status_output.split('\n'):
            if not line.strip():
                continue
            # Format: XY filename where XY is status like M, A, D, ??, etc.
            parts = line[2:].strip()
            if parts:
                result['uncommitted'].append(parts)

    # Get last 5 commits with messages
    log_commits = run_git(["git", "log", "--oneline", "-5", "--format=%H %ct %s"], timeout=1.0)
    if log_commits:
        for line in log_commits.split('\n'):
            if not line.strip():
                continue
            parts = line.split(' ', 2)
            if len(parts) >= 3:
                commit_hash = parts[0]
                try:
                    commit_time = int(parts[1])
                    commit_message = parts[2]
                    hours_ago = (start_time - commit_time) / 3600
                    result['last_commits'].append({
                        'hash': commit_hash,
                        'message': commit_message,
                        'hours_ago': round(hours_ago, 2),
                    })
                except ValueError:
                    continue

    return result


def cross_reference_error(changes: dict, error_context: str) -> Optional[str]:
    """Check if any recently changed file appears in an error context.

    Args:
        changes: A changes dict from detect_recent_changes().
        error_context: An error message or stack trace string.

    Returns:
        A message string like 'auth.py was modified 2 hours ago and appears in your error.'
        if a recently changed file is found in the error context.
        Returns None if no match is found.
    """
    if not error_context or not isinstance(error_context, str):
        return None

    recent_files = changes.get('recent_files', [])
    if not recent_files:
        return None

    error_lower = error_context.lower()

    for file_info in recent_files:
        file_path = file_info.get('path', '')
        if not file_path:
            continue

        # Get just the filename for matching
        filename = Path(file_path).name.lower()

        # Check if filename appears in error context
        if filename in error_lower:
            hours_ago = file_info.get('hours_ago', 0)
            hours_str = _format_hours(hours_ago)
            return f"{Path(file_path).name} was modified {hours_str} and appears in your error."

    return None


def _format_hours(hours: float) -> str:
    """Format hours as a human-readable string."""
    if hours < 1:
        minutes = int(hours * 60)
        if minutes <= 1:
            return "1 minute ago"
        return f"{minutes} minutes ago"
    elif hours < 24:
        if int(hours) == 1:
            return "1 hour ago"
        return f"{int(hours)} hours ago"
    else:
        days = int(hours / 24)
        if days == 1:
            return "1 day ago"
        return f"{days} days ago"
