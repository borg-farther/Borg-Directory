---
type: workflow_pack
version: "1.0"
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
  problem_description: The code tried to access a resource it does not have permission for. File, directory, database, or network resource.
root_cause:
  category: permission_denied
  explanation: The OS denied access to a resource because the process user does not have the required permissions on that resource.
investigation_trail:
  - file: "@resource_path"
    position: FIRST
    what: Run ls -la on the resource path
    grep_pattern: ""
  - file: "@app_code"
    position: SECOND
    what: Find the exact operation failing due to permissions
    grep_pattern: open|read|write|chmod|chown
  - file: "@process_user"
    position: THIRD
    what: Check which user the process is running as
    grep_pattern: ""
resolution_sequence:
  - action: chmod
    command: chmod 644 file (owner rw, others r) or 600 for secrets
    why: Principle of least privilege — give only what is needed
  - action: chown
    command: chown user:group file
    why: Changes ownership so the process user can access the file
  - action: add_to_group
    command: usermod -aG group user
    why: Adds the user to a group that has access to the resource
  - action: docker_user
    command: Ensure Dockerfile USER matches the file owner, or run docker with --user flag
    why: Docker containers run as root unless USER is explicitly set
anti_patterns:
  - action: chmod 777
    why_fails: Security risk — gives everyone full access
  - action: Running as root
    why_fails: Security risk — creates files owned by root
  - action: Disabling SELinux or AppArmor
    why_fails: Masks the permission problem and creates security risks
evidence:
  success_count: 34
  failure_count: 3
  success_rate: 0.92
  avg_time_to_resolve_minutes: 2.0
  uses: 37
provenance: Seed pack v1 | General Python debugging | 2026-04-02
---

## When to Use This Pack

Use when you encounter:
- `PermissionError: [Errno 13] Permission denied`
- `Access Denied` errors

Do NOT use for database permission errors (check the database user permissions instead).
