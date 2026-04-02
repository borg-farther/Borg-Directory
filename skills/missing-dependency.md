---
type: workflow_pack
version: "1.0"
id: missing-dependency
problem_class: missing_dependency
framework: python
problem_signature:
  error_types:
    - ModuleNotFoundError
    - ImportError
  framework: python
  problem_description: Python cannot find a module or package. It is not installed, not in the Python path, or not in the correct environment.
root_cause:
  category: missing_dependency
  explanation: Python cannot find the module because it is not installed in the current environment, not in the Python path, or the wrong Python environment is active.
investigation_trail:
  - file: requirements.txt
    position: FIRST
    what: Check if the package is listed
    grep_pattern: ""
  - file: pyproject.toml
    position: SECOND
    what: Check pyproject.toml dependencies
    grep_pattern: dependencies
  - file: "@pip_show"
    position: THIRD
    what: Run pip show to verify installation and location
    grep_pattern: ""
resolution_sequence:
  - action: pip_install
    command: pip install package-name
    why: Installs the package in the current Python environment
  - action: install_in_venv
    command: "source venv/bin/activate && pip install package-name"
    why: Ensures the package is installed in the correct virtual environment
  - action: install_editable
    command: pip install -e .
    why: Installs the local package in editable mode for development
  - action: check_python_path
    command: "import sys; print(sys.path)"
    why: Verify Python is looking in the right directories
anti_patterns:
  - action: pip install without a virtualenv
    why_fails: Pollutes the global Python and causes version conflicts
  - action: Manually copying module files to site-packages
    why_fails: Version conflicts and no automatic updates
  - action: Ignoring which virtualenv is activated
    why_fails: The module is installed but in a different environment
evidence:
  success_count: 42
  failure_count: 3
  success_rate: 0.93
  avg_time_to_resolve_minutes: 1.2
  uses: 45
provenance: Seed pack v1 | General Python debugging | 2026-04-02
---

## When to Use This Pack

Use when you encounter:
- `ModuleNotFoundError: No module named 'something'`
- `ImportError` for a module you believe exists

Do NOT use when the module exists but cannot be imported due to circular dependency.
