> **Historical/internal — not current product documentation.**
> Current public docs start at [the root README](https://github.com/borg-farther/Borg-Directory/blob/main/README.md) and [docs index](https://github.com/borg-farther/Borg-Directory/blob/main/docs/README.md). Do not treat old commands, credentials, metrics, version numbers, repo names, or launch claims in this file as current.

# borg full-suite pytest scope + product polish result

file rev 20260503-2120 rev A

timestamp: 2026-05-04T00:26:54Z

git rev: 88ae0f59b5d86afd4052098dab90d56977e111bf

## honest status

- pyproject pytest config is valid TOML and contains `testpaths = ["borg/tests"]` plus `norecursedirs` excluding docs/build/dist.
- full `python -m pytest -q` no longer enters `docs/eliza_cloned`; collection output references only `borg/tests`.
- full suite still fails during `borg/tests/test_pack_compatibility.py` collection because `UNIQUE_PACK_NAMES` is undefined. I did not fix this unrelated failure in this pass.
- targeted privacy-safe learning atom gates pass after minimal product polish.
- product polish added CLI/help/docs wording that frames atoms as signed, sanitized, revocable learning atoms and publish as fail-closed/no raw traces.

## files changed

this run changed:

- `borg/cli.py`
- `borg/tests/test_cli_atom.py`
- `docs/LEARNING_ATOM_SCHEMA.md`
- `docs/20260503-0835_privacy_safe_collective_intelligence/20260503-2120_borg-full-suite-pytest-scope-product-polish-result.md`

pre-existing working-tree changes also present at git rev above:

- modified: `borg/core/privacy.py`, `borg/core/publish.py`, `pyproject.toml`
- untracked M1 atom/security docs/tests/scripts/modules under `.github/`, `borg/core/`, `borg/tests/`, `docs/`, `eval/`, `scripts/`

## pyproject pytest config validation

command:

```bash
python - <<'PY'
import tomllib, json
with open('pyproject.toml','rb') as f:
    data=tomllib.load(f)
opts=data.get('tool',{}).get('pytest',{}).get('ini_options',{})
print(json.dumps(opts, indent=2))
PY
```

status: 0

stdout:

```text
{
  "testpaths": [
    "borg/tests"
  ],
  "norecursedirs": [
    "docs",
    "build",
    "dist",
    ".git",
    ".pytest_cache",
    "*.egg-info"
  ]
}
```

stderr:

```text

```

## required full pytest verification before polish

command:

```bash
python -m pytest -q
```

status: 2

stdout/stderr as captured by terminal:

```text
==================================== ERRORS ====================================
____________ ERROR collecting borg/tests/test_pack_compatibility.py ____________
borg/tests/test_pack_compatibility.py:199: in <module>
    class TestBorgSearchFindsPacks:
borg/tests/test_pack_compatibility.py:203: in TestBorgSearchFindsPacks
    @pytest.mark.parametrize("pack_name", UNIQUE_PACK_NAMES)
                                          ^^^^^^^^^^^^^^^^^
E   NameError: name 'UNIQUE_PACK_NAMES' is not defined
=============================== warnings summary ===============================
borg/tests/test_pack_compatibility.py:202
  /root/hermes-workspace/borg/borg/tests/test_pack_compatibility.py:202: PytestUnknownMarkWarning: Unknown pytest.mark.network - is this a typo?  You can register custom marks to avoid this warning - for details, see https://docs.pytest.org/en/stable/how-to/mark.html
    @pytest.mark.network

borg/tests/test_pull_network.py:54
  /root/hermes-workspace/borg/borg/tests/test_pull_network.py:54: PytestUnknownMarkWarning: Unknown pytest.mark.network - is this a typo?  You can register custom marks to avoid this warning - for details, see https://docs.pytest.org/en/stable/how-to/mark.html
    @pytest.mark.network

borg/tests/test_pull_network.py:76
  /root/hermes-workspace/borg/borg/tests/test_pull_network.py:76: PytestUnknownMarkWarning: Unknown pytest.mark.network - is this a typo?  You can register custom marks to avoid this warning - for details, see https://docs.pytest.org/en/stable/how-to/mark.html
    @pytest.mark.network

borg/tests/test_pull_network.py:116
  /root/hermes-workspace/borg/borg/tests/test_pull_network.py:116: PytestUnknownMarkWarning: Unknown pytest.mark.network - is this a typo?  You can register custom marks to avoid this warning - for details, see https://docs.pytest.org/en/stable/how-to/mark.html
    @pytest.mark.network

borg/tests/test_pull_network.py:137
  /root/hermes-workspace/borg/borg/tests/test_pull_network.py:137: PytestUnknownMarkWarning: Unknown pytest.mark.network - is this a typo?  You can register custom marks to avoid this warning - for details, see https://docs.pytest.org/en/stable/how-to/mark.html
    @pytest.mark.network

borg/tests/test_pull_network.py:156
  /root/hermes-workspace/borg/borg/tests/test_pull_network.py:156: PytestUnknownMarkWarning: Unknown pytest.mark.network - is this a typo?  You can register custom marks to avoid this warning - for details, see https://docs.pytest.org/en/stable/how-to/mark.html
    @pytest.mark.network

-- Docs: https://docs.pytest.org/en/stable/how-to/capture-warnings.html
=========================== short test summary info ============================
ERROR borg/tests/test_pack_compatibility.py - NameError: name 'UNIQUE_PACK_NA...
!!!!!!!!!!!!!!!!!!!! Interrupted: 1 error during collection !!!!!!!!!!!!!!!!!!!!
6 warnings, 1 error in 26.46s
```

## targeted gates before polish

command:

```bash
python -m pytest -q borg/tests/test_atom_tenant.py borg/tests/test_atom_policy.py borg/tests/test_learning_atoms.py borg/tests/test_atom_store.py borg/tests/test_atom_retrieval_firewall.py borg/tests/test_learning_atom_publish.py borg/tests/test_cli_atom.py
```

status: 0

stdout:

```text
...........................                                              [100%]
27 passed in 0.26s
```

stderr:

```text

```

command:

```bash
python scripts/run_atom_fixture_corpus.py
```

status: 0

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

command:

```bash
python scripts/security_gate_check.py
```

status: 0

stdout:

```text
PASS: Borg security hardening policy gate
```

stderr:

```text

```

## affected cli test after polish

command:

```bash
python -m pytest -q borg/tests/test_cli_atom.py
```

status: 0

stdout:

```text
...                                                                      [100%]
3 passed in 0.11s
```

stderr:

```text

```

## final full pytest after polish

command:

```bash
python -m pytest -q
```

status: 2

stdout:

```text

==================================== ERRORS ====================================
____________ ERROR collecting borg/tests/test_pack_compatibility.py ____________
borg/tests/test_pack_compatibility.py:199: in <module>
    class TestBorgSearchFindsPacks:
borg/tests/test_pack_compatibility.py:203: in TestBorgSearchFindsPacks
    @pytest.mark.parametrize("pack_name", UNIQUE_PACK_NAMES)
                                          ^^^^^^^^^^^^^^^^^
E   NameError: name 'UNIQUE_PACK_NAMES' is not defined
=============================== warnings summary ===============================
borg/tests/test_pack_compatibility.py:202
  /root/hermes-workspace/borg/borg/tests/test_pack_compatibility.py:202: PytestUnknownMarkWarning: Unknown pytest.mark.network - is this a typo?  You can register custom marks to avoid this warning - for details, see https://docs.pytest.org/en/stable/how-to/mark.html
    @pytest.mark.network

borg/tests/test_pull_network.py:54
  /root/hermes-workspace/borg/borg/tests/test_pull_network.py:54: PytestUnknownMarkWarning: Unknown pytest.mark.network - is this a typo?  You can register custom marks to avoid this warning - for details, see https://docs.pytest.org/en/stable/how-to/mark.html
    @pytest.mark.network

borg/tests/test_pull_network.py:76
  /root/hermes-workspace/borg/borg/tests/test_pull_network.py:76: PytestUnknownMarkWarning: Unknown pytest.mark.network - is this a typo?  You can register custom marks to avoid this warning - for details, see https://docs.pytest.org/en/stable/how-to/mark.html
    @pytest.mark.network

borg/tests/test_pull_network.py:116
  /root/hermes-workspace/borg/borg/tests/test_pull_network.py:116: PytestUnknownMarkWarning: Unknown pytest.mark.network - is this a typo?  You can register custom marks to avoid this warning - for details, see https://docs.pytest.org/en/stable/how-to/mark.html
    @pytest.mark.network

borg/tests/test_pull_network.py:137
  /root/hermes-workspace/borg/borg/tests/test_pull_network.py:137: PytestUnknownMarkWarning: Unknown pytest.mark.network - is this a typo?  You can register custom marks to avoid this warning - for details, see https://docs.pytest.org/en/stable/how-to/mark.html
    @pytest.mark.network

borg/tests/test_pull_network.py:156
  /root/hermes-workspace/borg/borg/tests/test_pull_network.py:156: PytestUnknownMarkWarning: Unknown pytest.mark.network - is this a typo?  You can register custom marks to avoid this warning - for details, see https://docs.pytest.org/en/stable/how-to/mark.html
    @pytest.mark.network

-- Docs: https://docs.pytest.org/en/stable/how-to/capture-warnings.html
=========================== short test summary info ============================
ERROR borg/tests/test_pack_compatibility.py - NameError: name 'UNIQUE_PACK_NA...
!!!!!!!!!!!!!!!!!!!! Interrupted: 1 error during collection !!!!!!!!!!!!!!!!!!!!
6 warnings, 1 error in 7.84s
```

stderr:

```text

```

## final targeted gates after polish

command:

```bash
python -m pytest -q borg/tests/test_atom_tenant.py borg/tests/test_atom_policy.py borg/tests/test_learning_atoms.py borg/tests/test_atom_store.py borg/tests/test_atom_retrieval_firewall.py borg/tests/test_learning_atom_publish.py borg/tests/test_cli_atom.py
```

status: 0

stdout:

```text
............................                                             [100%]
28 passed in 0.24s
```

stderr:

```text

```

command:

```bash
python scripts/run_atom_fixture_corpus.py
```

status: 0

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

command:

```bash
python scripts/security_gate_check.py
```

status: 0

stdout:

```text
PASS: Borg security hardening policy gate
```

stderr:

```text

```
