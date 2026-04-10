#!/usr/bin/env python3
"""
E1a Evaluation: Seed Pack Evaluation against SWE-bench Django Tasks

For each Django SWE-bench task:
1. Extract error type from problem_statement (traceback)
2. Classify using hardcoded taxonomy mapping
3. Load matching seed pack
4. Check if investigation_trail files appear in patch
5. Record results
"""

import json
import re
from pathlib import Path
from typing import Optional, Dict, Any, List, Tuple

# -----------------------------------------------------------------------
# Taxonomy mapping (hardcoded from pack_taxonomy.py)
# -----------------------------------------------------------------------
ERROR_KEYWORDS_TO_PROBLEM_CLASS = [
    # Django migrations
    ("circular", "circular_dependency"),
    ("dependency cycle", "circular_dependency"),
    ("InvalidMoveError", "circular_dependency"),
    ("makemigrations", "migration_state_desync"),
    ("migrate", "migration_state_desync"),
    ("no such table", "migration_state_desync"),
    ("table already exists", "migration_state_desync"),
    ("applied migrations", "migration_state_desync"),
    # Django models / DB
    ("FOREIGN KEY constraint failed", "missing_foreign_key"),
    ("IntegrityError", "missing_foreign_key"),
    ("no such column", "schema_drift"),
    ("table has no column", "schema_drift"),
    # Django config
    ("ImproperlyConfigured", "configuration_error"),
    ("SECRET_KEY", "configuration_error"),
    ("ALLOWED_HOSTS", "configuration_error"),
    ("DATABASE_URL", "configuration_error"),
    # Python types
    ("NoneType", "null_pointer_chain"),
    ("'NoneType'", "null_pointer_chain"),
    ("object is not iterable", "null_pointer_chain"),
    # Python imports
    ("circular import", "import_cycle"),
    ("import cycle", "import_cycle"),
    ("cannot import name", "import_cycle"),
    # Permissions
    ("PermissionError", "permission_denied"),
    ("permission denied", "permission_denied"),
    ("EACCES", "permission_denied"),
    ("EPERM", "permission_denied"),
    # Concurrency
    ("dictionary changed size during iteration", "race_condition"),
    ("TimeoutError", "timeout_hang"),
    ("timed out", "timeout_hang"),
    ("Connection refused", "timeout_hang"),
    ("Connection timed out", "timeout_hang"),
    ("GatewayTimeout", "timeout_hang"),
    # Missing dependencies
    ("ModuleNotFoundError", "missing_dependency"),
    ("No module named", "missing_dependency"),
    ("ImportError", "missing_dependency"),
    # Type errors
    ("TypeError", "type_mismatch"),
    ("mypy", "type_mismatch"),
    # Schema drift
    ("OperationalError", "schema_drift"),
    ("SyncError", "schema_drift"),
    # Generic
    ("Error", "schema_drift"),
]

PROBLEM_CLASSES = [
    "circular_dependency",
    "null_pointer_chain",
    "missing_foreign_key",
    "migration_state_desync",
    "import_cycle",
    "race_condition",
    "configuration_error",
    "type_mismatch",
    "missing_dependency",
    "timeout_hang",
    "schema_drift",
    "permission_denied",
]


def classify_error(error_message: str) -> Optional[str]:
    """Classify an error message string into a problem_class."""
    if not error_message:
        return None
    lower = error_message.lower()
    for keyword, problem_class in ERROR_KEYWORDS_TO_PROBLEM_CLASS:
        if keyword.lower() in lower:
            return problem_class
    return None


def extract_error_type(problem_statement: str) -> Optional[str]:
    """Extract error type from problem statement traceback."""
    if not problem_statement:
        return None
    # Look for common error types in traceback
    error_types = [
        "IntegrityError",
        "OperationalError", 
        "ProgrammingError",
        "TypeError",
        "AttributeError",
        "ImportError",
        "ModuleNotFoundError",
        "PermissionError",
        "TimeoutError",
        "DatabaseError",
    ]
    for err in error_types:
        if err in problem_statement:
            return err
    return None


def extract_files_from_patch(patch: str) -> List[str]:
    """Extract file paths from a unified diff patch."""
    files = []
    if not patch:
        return files
    # Match lines like: diff --git a/django/db/models/foo.py b/django/db/models/foo.py
    # or: --- a/django/db/models/foo.py
    # or: +++ b/django/db/models/foo.py
    for line in patch.split('\n'):
        if line.startswith('diff --git'):
            # Extract the two paths
            parts = line.split()
            if len(parts) >= 4:
                # a/path b/path -> take b/path (or just the filename)
                path = parts[-1]
                if path.startswith('b/'):
                    path = path[2:]
                files.append(path)
        elif line.startswith('--- ') or line.startswith('+++ '):
            # Extract path, handle special cases like /dev/null
            parts = line.split()
            if len(parts) >= 2 and parts[1] != '/dev/null':
                path = parts[1]
                if path.startswith('a/'):
                    path = path[2:]
                if path.startswith('b/'):
                    path = path[2:]
                # Remove leading slashes
                path = path.lstrip('/')
                if path and path not in files:
                    files.append(path)
    return files


def load_seed_packs(skills_dir: Path) -> Dict[str, Dict[str, Any]]:
    """Load all seed packs from skills directory."""
    import yaml
    
    packs = {}
    for f in skills_dir.glob("*.md"):
        try:
            text = f.read_text(encoding="utf-8")
            if not text.startswith("---"):
                continue
            yaml_text = text[3:]
            if yaml_text.startswith("\n"):
                yaml_text = yaml_text[1:]
            idx = yaml_text.find("\n---")
            if idx == -1:
                continue
            frontmatter = yaml_text[:idx]
            data = yaml.safe_load(frontmatter)
            if data and isinstance(data, dict):
                pc = data.get("problem_class", "")
                if pc:
                    packs[pc] = data
        except Exception as e:
            print(f"Error loading pack {f}: {e}")
            continue
    return packs


def get_investigation_trail_files(pack: Dict[str, Any]) -> List[str]:
    """Extract file list from investigation_trail."""
    trail = pack.get("investigation_trail", [])
    if not isinstance(trail, list):
        return []
    files = []
    for item in trail:
        if isinstance(item, dict):
            f = item.get("file", "")
            if f and not f.startswith("@"):
                files.append(f)
        elif isinstance(item, str):
            if not item.startswith("@"):
                files.append(item)
    return files


def check_file_match(trail_files: List[str], patch_files: List[str]) -> Tuple[int, List[str]]:
    """Check how many trail files appear in patch files. Returns (count, matched_files)."""
    matched = []
    for tf in trail_files:
        # Normalize trail file for matching
        tf_normalized = tf.lower().replace('\\', '/')
        for pf in patch_files:
            pf_normalized = pf.lower().replace('\\', '/')
            # Check if they refer to the same file
            if tf_normalized == pf_normalized:
                matched.append(tf)
                break
            # Check if trail file is a suffix of patch file
            if pf_normalized.endswith(tf_normalized) or tf_normalized in pf_normalized:
                matched.append(tf)
                break
    return len(matched), matched


def main():
    # Paths
    skills_dir = Path("/root/hermes-workspace/borg/skills")
    task_dirs = [
        Path("/root/hermes-workspace/borg/dogfood/swebench_experiment"),
        Path("/root/hermes-workspace/borg/dogfood/swebench_tasks"),
    ]
    output_file = Path("/root/hermes-workspace/borg/eval/E1a_results.md")
    
    # Load all task directories
    all_task_dirs = []
    for td in task_dirs:
        if td.exists():
            for d in td.iterdir():
                if d.is_dir() and d.name.startswith("django__django-"):
                    all_task_dirs.append(d)
    
    print(f"Found {len(all_task_dirs)} Django task directories")
    
    # Load seed packs
    packs = load_seed_packs(skills_dir)
    print(f"Loaded {len(packs)} seed packs")
    print(f"Pack IDs: {list(packs.keys())}")
    
    # Process each task
    results = []
    for task_dir in sorted(all_task_dirs):
        task_data_file = task_dir / "task_data.json"
        if not task_data_file.exists():
            continue
            
        try:
            task_data = json.loads(task_data_file.read_text(encoding="utf-8"))
        except Exception as e:
            print(f"Error loading {task_data_file}: {e}")
            continue
            
        instance_id = task_data.get("instance_id", task_dir.name)
        problem_statement = task_data.get("problem_statement", "")
        patch = task_data.get("patch", "")
        
        # Extract error type
        error_type = extract_error_type(problem_statement)
        
        # Classify
        problem_class = classify_error(problem_statement)
        
        # Get pack
        pack = packs.get(problem_class) if problem_class else None
        pack_id = pack.get("id") if pack else None
        
        # Get trail files
        trail_files = get_investigation_trail_files(pack) if pack else []
        
        # Get patch files
        patch_files = extract_files_from_patch(patch)
        
        # Check match
        match_count, matched_files = check_file_match(trail_files, patch_files)
        match_1_plus = match_count >= 1
        match_2_plus = match_count >= 2
        
        results.append({
            "instance_id": instance_id,
            "error_type": error_type,
            "problem_class": problem_class,
            "pack_id": pack_id,
            "trail_files": trail_files,
            "patch_files": patch_files,
            "match_count": match_count,
            "match_1_plus": match_1_plus,
            "match_2_plus": match_2_plus,
            "matched_files": matched_files,
        })
        
        print(f"\n{instance_id}:")
        print(f"  Error type: {error_type}")
        print(f"  Problem class: {problem_class}")
        print(f"  Pack ID: {pack_id}")
        print(f"  Trail files: {trail_files[:5]}{'...' if len(trail_files) > 5 else ''}")
        print(f"  Patch files: {patch_files[:5]}{'...' if len(patch_files) > 5 else ''}")
        print(f"  Match count: {match_count}")
    
    # Summary statistics
    total = len(results)
    with_1_plus = sum(1 for r in results if r["match_1_plus"])
    with_2_plus = sum(1 for r in results if r["match_2_plus"])
    no_pack = sum(1 for r in results if not r["pack_id"])
    
    print(f"\n\n=== SUMMARY ===")
    print(f"Total tasks: {total}")
    print(f"Tasks with 1+ matching file: {with_1_plus}/{total}")
    print(f"Tasks with 2+ matching files: {with_2_plus}/{total}")
    print(f"Tasks with no matching pack: {no_pack}/{total}")
    
    # Write markdown table
    lines = []
    lines.append("# E1a Results: Seed Pack Evaluation against SWE-bench Django Tasks\n")
    lines.append(f"**Evaluation Date:** 2026-04-02\n")
    lines.append(f"**Total Tasks:** {total}\n")
    lines.append(f"**Tasks with 1+ matching file:** {with_1_plus}/{total}\n")
    lines.append(f"**Tasks with 2+ matching files:** {with_2_plus}/{total}\n")
    lines.append(f"**Tasks with no matching pack:** {no_pack}/{total}\n")
    lines.append("\n## Detailed Results\n")
    lines.append("| Task ID | Error Type | problem_class | Pack ID | Trail Files | Patch Files | Match (1+) | Match (2+) |")
    lines.append("|---------|------------|---------------|---------|-------------|------------|-----------|-----------|")
    
    for r in sorted(results, key=lambda x: x["instance_id"]):
        trail_str = ", ".join(r["trail_files"][:3])
        if len(r["trail_files"]) > 3:
            trail_str += "..."
        patch_str = ", ".join(r["patch_files"][:3])
        if len(r["patch_files"]) > 3:
            patch_str += "..."
        lines.append(
            f"| {r['instance_id']} | {r['error_type'] or 'N/A'} | {r['problem_class'] or 'N/A'} | "
            f"{r['pack_id'] or 'no_pack_found'} | {trail_str} | {patch_str} | "
            f"{'Yes' if r['match_1_plus'] else 'No'} | {'Yes' if r['match_2_plus'] else 'No'} |"
        )
    
    lines.append("\n## Summary\n")
    lines.append(f"**E1a: {with_1_plus}/{total} tasks had at least 1 matching file, {with_2_plus}/{total} had 2+ matching files**\n")
    
    output_file.write_text("\n".join(lines), encoding="utf-8")
    print(f"\nResults written to {output_file}")


if __name__ == "__main__":
    main()