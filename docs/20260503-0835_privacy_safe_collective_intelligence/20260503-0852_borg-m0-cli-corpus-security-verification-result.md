> **Historical/internal — not current product documentation.**
> Current public docs start at [the root README](https://github.com/borg-farther/Borg-Directory/blob/main/README.md) and [docs index](https://github.com/borg-farther/Borg-Directory/blob/main/docs/README.md). Do not treat old commands, credentials, metrics, version numbers, repo names, or launch claims in this file as current.

# Borg M0 CLI / Corpus / Security Verification Result

Workdir: `/root/hermes-workspace/borg`

Status: PASS after one minimal M0 script-path fix.

Minimal fix applied:
- `scripts/run_atom_fixture_corpus.py`: inserted repository root into `sys.path` before importing `borg.core.*`, so the script works when executed exactly as `python scripts/run_atom_fixture_corpus.py` from the repo root.

Initial failure observed before fix:

```text
$ python scripts/run_atom_fixture_corpus.py
Traceback (most recent call last):
  File "/root/hermes-workspace/borg/scripts/run_atom_fixture_corpus.py", line 9, in <module>
    from borg.core.atom_policy import AtomDecision, classify_atom_policy
ModuleNotFoundError: No module named 'borg.core.atom_policy'
```

## Final verification commands

### 1) `python -m pytest -q borg/tests/test_privacy_structured.py borg/tests/test_prompt_injection.py borg/tests/test_learning_atoms.py borg/tests/test_atom_policy.py borg/tests/test_atom_retrieval_firewall.py borg/tests/test_atom_store.py borg/tests/test_learning_atom_publish.py borg/tests/test_cli_atom.py`

Status: 0

stdout:

```text
..................................                                       [100%]
34 passed in 0.27s
```

stderr:

```text
```

### 2) `python -m pytest -q borg/tests/test_privacy.py`

Status: 0

stdout:

```text
................................................                         [100%]
48 passed in 0.05s
```

stderr:

```text
```

### 3) `python scripts/run_atom_fixture_corpus.py`

Status: 0

stdout:

```text
{
  "success": true,
  "total": 10,
  "failed": []
}
```

stderr:

```text
```

### 4) `python scripts/security_gate_check.py`

Status: 0

stdout:

```text
PASS: Borg security hardening policy gate
```

stderr:

```text
```

### 5) `python -m pytest -q borg/tests/test_cli.py::test_help_text_shows_all_commands borg/tests/test_cli.py::test_version_prints_version`

Status: 0

stdout:

```text
..                                                                       [100%]
2 passed in 0.11s
```

stderr:

```text
```
