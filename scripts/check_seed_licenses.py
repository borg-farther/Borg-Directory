#!/usr/bin/env python3
"""
Seed Pack License Compliance Checker

Validates all seed packs in /root/hermes-workspace/borg/borg/seeds_data/packs/ for:
1. License allowlist compliance
2. Provenance source presence and validity
3. No forbidden secrets in any field values
"""

import sys
import os
import yaml
import re
from pathlib import Path
from typing import List, Dict, Any, Tuple

# Configuration
PACKS_DIR = Path("/root/hermes-workspace/borg/borg/seeds_data/packs")
ALLOWED_LICENSES = {"MIT", "Apache-2.0", "BSD-3-Clause", "CC-BY-4.0", "CC0-1.0"}
FORBIDDEN_PATTERNS = ["api_key", "secret", "password", "token", "private_key"]
# URL pattern for validating provenance.source
URL_PATTERN = re.compile(
    r"^(https?://|git@|ssh://|ftp://|file://)"
    r"[^\s]+$",
    re.IGNORECASE
)


def find_yaml_files(packs_dir: Path) -> List[Path]:
    """Find all YAML files in the packs directory."""
    if not packs_dir.exists():
        print(f"ERROR: Packs directory does not exist: {packs_dir}")
        sys.exit(1)
    
    yaml_files = list(packs_dir.glob("*.yaml")) + list(packs_dir.glob("*.yml"))
    if not yaml_files:
        print(f"WARNING: No YAML files found in {packs_dir}")
    return sorted(yaml_files)


def load_yaml_file(file_path: Path) -> Tuple[Dict[str, Any], str]:
    """Load a YAML file and return its contents."""
    try:
        with open(file_path, 'r', encoding='utf-8') as f:
            content = yaml.safe_load(f)
            return content, None
    except yaml.YAMLError as e:
        return None, f"YAML parse error: {e}"
    except Exception as e:
        return None, f"Failed to read file: {e}"


def check_license_allowlist(pack_data: Dict[str, Any], pack_name: str) -> List[str]:
    """Check if the license field is in the allowlist."""
    errors = []
    license_value = pack_data.get("license", "")
    
    if not license_value:
        errors.append(f"[{pack_name}] Missing 'license' field")
    elif license_value not in ALLOWED_LICENSES:
        errors.append(
            f"[{pack_name}] License '{license_value}' not in allowlist. "
            f"Allowed: {', '.join(sorted(ALLOWED_LICENSES))}"
        )
    
    return errors


def check_provenance_source(pack_data: Dict[str, Any], pack_name: str) -> List[str]:
    """
    Check that provenance.source exists and is a valid URL or repo reference.
    Valid formats:
    - http:// or https:// URLs
    - git@host:path (Git SSH)
    - ssh://host/path
    - ftp://, file:// URLs
    - github.com, gitlab.com style repo paths without protocol
    """
    errors = []
    
    # Check for provenance.source specifically
    provenance = pack_data.get("provenance", {})
    if not provenance:
        # Fall back to source_url if no provenance block
        source_url = pack_data.get("source_url", "")
        if not source_url:
            errors.append(f"[{pack_name}] Missing 'provenance.source' or 'source_url' field")
        elif not is_valid_source(source_url):
            errors.append(f"[{pack_name}] provenance.source/source_url '{source_url}' is not a valid URL or repo")
        return errors
    
    source = provenance.get("source", "")
    if not source:
        errors.append(f"[{pack_name}] Missing 'provenance.source' field")
    elif not is_valid_source(source):
        errors.append(f"[{pack_name}] provenance.source '{source}' is not a valid URL or repo")
    
    return errors


def is_valid_source(source: str) -> bool:
    """Check if a source string is a valid URL or repo reference."""
    if not source or not isinstance(source, str):
        return False
    
    # Check for URL patterns
    if URL_PATTERN.match(source):
        return True
    
    # Check for common repo path patterns (github.com/user/repo, etc.)
    repo_pattern = re.compile(
        r"^(github|gitlab|bitbucket|sourcehut)\.com[/:]"
        r"[\w\-]+/[\w\-\.]+"
        r"(/.*)?$",
        re.IGNORECASE
    )
    if repo_pattern.match(source):
        return True
    
    # Check for bare repo names (alphanumeric with dashes, dots, underscores)
    if re.match(r"^[\w\-\.]+$", source) and len(source) > 2:
        return True
    
    return False


def check_forbidden_secrets(pack_data: Dict[str, Any], pack_name: str) -> List[str]:
    """
    Check that no field values contain forbidden patterns like api_key, secret,
    password, token, or private_key.
    """
    errors = []
    
    def recursive_check(obj: Any, path: str = "") -> None:
        if isinstance(obj, dict):
            for key, value in obj.items():
                current_path = f"{path}.{key}" if path else key
                # Check the key itself
                key_lower = key.lower()
                for pattern in FORBIDDEN_PATTERNS:
                    if pattern in key_lower:
                        errors.append(
                            f"[{pack_name}] Forbidden key '{key}' found at '{current_path}'"
                        )
                # Check string values
                if isinstance(value, str):
                    value_lower = value.lower()
                    for pattern in FORBIDDEN_PATTERNS:
                        if pattern in value_lower and pattern != key_lower:
                            # Avoid duplicate errors for keys that are already flagged
                            # but still check if the VALUE contains secrets
                            if re.search(rf"\b{re.escape(pattern)}\b", value_lower):
                                errors.append(
                                    f"[{pack_name}] Forbidden pattern '{pattern}' found "
                                    f"in value of '{current_path}'"
                                )
                # Recurse into nested structures
                recursive_check(value, current_path)
        elif isinstance(obj, list):
            for i, item in enumerate(obj):
                recursive_check(item, f"{path}[{i}]")
    
    recursive_check(pack_data)
    return errors


def validate_pack(file_path: Path) -> Tuple[str, List[str]]:
    """
    Validate a single pack file.
    Returns (pack_name, list_of_errors)
    """
    pack_data, load_error = load_yaml_file(file_path)
    
    if load_error:
        return file_path.stem, [load_error]
    
    if pack_data is None:
        return file_path.stem, [f"Empty YAML file: {file_path}"]
    
    pack_name = pack_data.get("name", file_path.stem)
    
    all_errors = []
    all_errors.extend(check_license_allowlist(pack_data, pack_name))
    all_errors.extend(check_provenance_source(pack_data, pack_name))
    all_errors.extend(check_forbidden_secrets(pack_data, pack_name))
    
    return pack_name, all_errors


def main():
    """Main entry point."""
    print("=" * 60)
    print("Seed Pack License Compliance Checker")
    print("=" * 60)
    print(f"Scanning directory: {PACKS_DIR}")
    print(f"Allowed licenses: {', '.join(sorted(ALLOWED_LICENSES))}")
    print(f"Forbidden patterns: {', '.join(FORBIDDEN_PATTERNS)}")
    print("-" * 60)
    
    yaml_files = find_yaml_files(PACKS_DIR)
    print(f"Found {len(yaml_files)} YAML file(s)")
    print()
    
    if not yaml_files:
        print("No packs to validate - exiting with success")
        sys.exit(0)
    
    all_errors = []
    packs_checked = 0
    
    for file_path in yaml_files:
        pack_name, errors = validate_pack(file_path)
        packs_checked += 1
        
        if errors:
            print(f"FAIL: {pack_name}")
            for error in errors:
                print(f"  - {error}")
            all_errors.extend(errors)
        else:
            print(f"PASS: {pack_name}")
    
    print()
    print("=" * 60)
    print(f"Results: {packs_checked} pack(s) checked, {len(all_errors)} error(s) found")
    print("=" * 60)
    
    if all_errors:
        print()
        print("VALIDATION FAILED")
        print("=" * 60)
        for error in all_errors:
            print(f"  {error}")
        sys.exit(1)
    else:
        print()
        print("VALIDATION PASSED - All packs are compliant")
        sys.exit(0)


if __name__ == "__main__":
    main()
