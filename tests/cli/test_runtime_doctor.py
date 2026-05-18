from __future__ import annotations

from borg.cli.doctor import runtime_fingerprint


def test_runtime_fingerprint_contains_release_and_db_paths() -> None:
    fp = runtime_fingerprint()
    assert fp["package_version"]
    assert fp["module_path"].endswith("__init__.py")
    assert fp["borg_home"]
    assert fp["trace_db_path"].endswith("traces.db")
    assert fp["atom_db_path"].endswith("atoms.db")
    assert fp["python"]
