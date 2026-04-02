---
type: workflow_pack
version: "1.0"
id: configuration-error
problem_class: configuration_error
framework: django
problem_signature:
  error_types:
    - ImproperlyConfigured
    - ConfigurationError
  framework: django
  problem_description: Django is misconfigured. An environment variable is missing, a setting is contradictory, or Django cannot find what it needs to start.
root_cause:
  category: configuration_error
  explanation: Django requires specific configuration to run. When that configuration is missing, contradictory, or inaccessible, it raises ImproperlyConfigured before any code runs.
investigation_trail:
  - file: settings.py
    position: FIRST
    what: Find the specific setting Django is complaining about
    grep_pattern: ""
  - file: "@env_file"
    position: SECOND
    what: Check if the environment variable is set
    grep_pattern: ""
  - file: "@env_vars"
    position: THIRD
    what: Check all environment variables accessible to the Django process
    grep_pattern: ""
resolution_sequence:
  - action: set_env_variable
    command: "export SECRET_KEY='your-production-secret-key'"
    why: Environment variables are the correct way to manage secrets
  - action: use_env_file
    command: Add the setting to .env and load with python-dotenv or django-environ
    why: .env files keep local config separate from code
  - action: provide_default
    command: "Add default in settings.py: SECRET_KEY = os.environ.get('SECRET_KEY', 'dev-only-key')"
    why: Defaults allow development while requiring production config
anti_patterns:
  - action: Hardcoding secrets in settings.py
    why_fails: Security risk — secrets end up in version control
  - action: Setting DEBUG=True in production
    why_fails: Security risk — exposes internal application details
  - action: Deleting the check that raises the error
    why_fails: Masks the problem rather than solving it
evidence:
  success_count: 31
  failure_count: 2
  success_rate: 0.94
  avg_time_to_resolve_minutes: 1.5
  uses: 33
provenance: Seed pack v1 | General Django debugging | 2026-04-02
---

## When to Use This Pack

Use when you encounter:
- `django.core.exceptions.ImproperlyConfigured`
- Django startup errors mentioning SECRET_KEY, DATABASE_URL, ALLOWED_HOSTS
- Any error that occurs BEFORE the application starts
