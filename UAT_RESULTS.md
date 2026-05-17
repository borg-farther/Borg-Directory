# Borg First-User UAT Results

Generated: 2026-05-17 11:35:59 UTC

Overall: **GO**

| Check | Result | Detail |
|---|---:|---|
| `file:pyproject.toml` | PASS | present |
| `file:borg/__init__.py` | PASS | present |
| `file:README.md` | PASS | present |
| `file:LICENSE` | PASS | present |
| `version_consistency` | PASS | pyproject=3.3.3 runtime=3.3.3 |
| `script_entrypoints` | PASS | borg, borg-mcp, borg-doctor declared |
| `project_urls` | PASS | Homepage/Repository/Documentation/Issues present |
| `readme_day_one_path` | PASS | README must include install + rescue as first-user path |
| `security_artifact:eval/security_hardening_baseline.json` | PASS | present and non-placeholder |
| `security_artifact:docs/SECURITY_HARDENING_BASELINE.md` | PASS | present and non-placeholder |
| `security_artifact:.github/workflows/security-gates.yml` | PASS | present and non-placeholder |
| `security_artifact:scripts/security_gate_check.py` | PASS | present and non-placeholder |
| `fresh_venv_create` | PASS | exit=0 |
| `install_build_tooling` | PASS | exit=0 |
| `build_wheel` | PASS | exit=0 |
| `fresh_install_agent_borg` | PASS | exit=0 |
| `borg_version` | PASS | public command returned expected value signal |
| `borg_help` | PASS | public command returned expected value signal |
| `borg_rescue_text` | PASS | public command returned expected value signal |
| `borg_rescue_json` | PASS | public command returned expected value signal |
| `borg_doctor_json` | PASS | public command returned expected value signal |
| `borg_try_bare` | PASS | public command returned expected value signal |
| `borg_try_borg_uri` | PASS | public command returned expected value signal |
| `borg_try_guild_uri` | PASS | public command returned expected value signal |
| `borg_setup_claude_flags` | PASS | public command returned expected value signal |
| `public_import_api_check` | PASS | borg.check returned list without crashing |
