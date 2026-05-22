> **Historical/internal — not current product documentation.**
> Current public docs start at [the root README](https://github.com/borg-farther/Borg-Directory/blob/main/README.md) and [docs index](https://github.com/borg-farther/Borg-Directory/blob/main/docs/README.md). Do not treat old commands, credentials, metrics, version numbers, repo names, or launch claims in this file as current.

# Borg M0 publish hardening verification result

Workdir: `/root/hermes-workspace/borg`

Status: PASS after one minimal M0 fix.

Minimal fix applied:
- `borg/core/learning_atoms.py`: learning atom signatures now use order-independent canonical atom JSON for signing and verification, preserving legacy pack signing APIs. This fixed signed learning atom publish verification after YAML round-trip key reordering.

## Command 1

```bash
python -m pytest -q borg/tests/test_privacy_structured.py borg/tests/test_prompt_injection.py borg/tests/test_learning_atoms.py borg/tests/test_atom_policy.py borg/tests/test_atom_retrieval_firewall.py borg/tests/test_atom_store.py borg/tests/test_learning_atom_publish.py
```

Exit status: `0`

stdout:

```text
................................                                         [100%]
32 passed in 0.29s
```

stderr:

```text

```

## Command 2

```bash
python -m pytest -q borg/tests/test_privacy.py
```

Exit status: `0`

stdout:

```text
................................................                         [100%]
48 passed in 0.06s
```

stderr:

```text

```
