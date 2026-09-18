---
type: workflow_pack
version: '1.0'
id: permission-denied
problem_class: permission_denied
framework: python
problem_signature:
  error_types:
  - PermissionError
  - AccessDenied
  - EACCES
  - EPERM
  framework: python
  problem_description: The code tried to access a resource it does not have permission
    for. File, directory, database, or network resource.
root_cause:
  category: permission_denied
  explanation: The OS denied access to a resource because the process user does not
    have the required permissions on that resource.
investigation_trail:
- file: <denied-path>
  position: FIRST
  what: Identify the exact denied operation, process user, owner/group, mode bits, ACLs, and parent-directory traversal permissions before mutating anything
  grep_pattern: permission denied|EACCES|EPERM|read-only file system
resolution_sequence:
- action: inspect_identity_and_path
  command: id && ls -ld -- <denied-path> && namei -l -- <denied-path>
  why: Distinguishes missing execute/read/write bits from wrong ownership, parent traversal, read-only mounts, ACLs, and policy controls
- action: reproduce_as_intended_user
  command: rerun the exact failing command as the intended non-root process user
  why: Confirms which operation and identity are actually denied before choosing a fix
- action: apply_minimum_targeted_change
  command: change only the required owner/group/mode/ACL or mount policy after the diagnosis identifies it
  why: The safe repair depends on whether the denied operation is read, write, execute, directory traversal, or a read-only mount
anti_patterns:
- action: chmod 777
  why_fails: Security risk — gives everyone full access
- action: Running as root
  why_fails: Security risk — creates files owned by root
- action: Blind chmod 644 or chown
  why_fails: Can remove required execute permission or corrupt ownership without identifying the denied operation
- action: Disabling SELinux or AppArmor
  why_fails: Masks the permission problem and creates security risks
evidence:
  success_count: 34
  failure_count: 3
  success_rate: 0.92
  avg_time_to_resolve_minutes: 2.0
  uses: 37
provenance: Seed pack v1 | Updated with SWE-bench patch file analysis | 2026-04-03
---


## When to Use This Pack

Use when you encounter:
- `PermissionError: [Errno 13] Permission denied`
- `Access Denied` errors

Do NOT use for database permission errors (check the database user permissions instead).
