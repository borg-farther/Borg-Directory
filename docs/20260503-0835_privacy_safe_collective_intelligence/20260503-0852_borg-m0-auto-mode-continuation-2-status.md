# Borg M0 Auto Mode Continuation 2 Status

**File rev:** 20260503-0852 rev A

## Added in this continuation

### CLI atom commands

Modified:

- `borg/cli.py`

Added command group:

```bash
borg atom distill --trace-id <id> --scope local|org|global_candidate|global
borg atom validate <path>
borg atom search <query> [--json]
borg atom revoke <atom-id> --reason "..."
```

### CLI tests

Created:

- `borg/tests/test_cli_atom.py`

Coverage:

- `borg atom validate` accepts valid atom YAML;
- `borg atom --help` lists distill/validate/search/revoke.

### Fixture corpus

Created:

- `borg/tests/fixtures/privacy_cases.jsonl`
- `borg/tests/fixtures/prompt_injection_cases.jsonl`
- `borg/tests/fixtures/safe_learning_atom_cases.jsonl`
- `scripts/run_atom_fixture_corpus.py`

### CI update

Modified:

- `.github/workflows/security-gates.yml`

Added:

- `python scripts/run_atom_fixture_corpus.py`
- `borg/tests/test_cli_atom.py` to policy test command.

## Verification queued

Cron job:

- `c9bcc7405851`
- name: `20260503-0852 borg m0 cli corpus security verify`

Commands queued:

```bash
python -m pytest -q borg/tests/test_privacy_structured.py borg/tests/test_prompt_injection.py borg/tests/test_learning_atoms.py borg/tests/test_atom_policy.py borg/tests/test_atom_retrieval_firewall.py borg/tests/test_atom_store.py borg/tests/test_learning_atom_publish.py borg/tests/test_cli_atom.py
python -m pytest -q borg/tests/test_privacy.py
python scripts/run_atom_fixture_corpus.py
python scripts/security_gate_check.py
python -m pytest -q borg/tests/test_cli.py::test_help_text_shows_all_commands borg/tests/test_cli.py::test_version_prints_version
```

## Current honest status

Previous verification passed:

- M0 targeted + publish: 32 passed.
- Legacy privacy regression: 48 passed.

Current continuation adds CLI/corpus/security gate verification. M0 is not COMPLETE until this latest verification returns green.
