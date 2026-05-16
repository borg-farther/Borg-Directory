"""Regression tests for first-user BORG_HOME storage isolation."""

import json
import os
import subprocess
import sys
from pathlib import Path


def _run_probe(repo_root: Path, env: dict[str, str]) -> dict:
    code = """
import json
from borg.core.dirs import get_borg_home, get_borg_dir, get_trace_db_path, get_v3_db_path, get_atom_db_path
from borg.core.v3_integration import BorgV3
from borg.db.store import AgentStore
from borg.integrations import mcp_server
from borg.core.runtime_fingerprint import runtime_fingerprint
v3 = BorgV3()
store = AgentStore()
print(json.dumps({
    'borg_home': str(get_borg_home()),
    'borg_dir': str(get_borg_dir()),
    'trace_db_path': str(get_trace_db_path()),
    'v3_db_path': str(get_v3_db_path()),
    'atom_db_path': str(get_atom_db_path()),
    'direct_v3_path': v3._db_path,
    'mcp_v3_path': mcp_server._get_borg_v3()._db_path,
    'agent_store_path': store.db_path,
    'fingerprint': runtime_fingerprint()['paths'],
}, sort_keys=True))
"""
    proc = subprocess.run(
        [sys.executable, '-c', code],
        cwd=str(repo_root),
        env=env,
        text=True,
        capture_output=True,
        timeout=30,
        check=True,
    )
    return json.loads(proc.stdout)


def test_borg_home_only_isolates_trace_v3_store_and_fingerprint(tmp_path):
    repo_root = Path(__file__).resolve().parents[2]
    fake_home = tmp_path / 'fake-home'
    borg_home = tmp_path / 'borg-home'
    decoy_hermes = tmp_path / 'decoy-hermes'
    env = os.environ.copy()
    env.update({
        'HOME': str(fake_home),
        'BORG_HOME': str(borg_home),
        'HERMES_HOME': str(decoy_hermes),
        'PYTHONPATH': str(repo_root),
    })
    env.pop('BORG_DIR', None)

    data = _run_probe(repo_root, env)

    assert data['borg_home'] == str(borg_home)
    assert data['borg_dir'] == str(borg_home / 'guild')
    assert data['trace_db_path'] == str(borg_home / 'traces.db')
    assert data['v3_db_path'] == str(borg_home / 'borg_v3.db')
    assert data['direct_v3_path'] == str(borg_home / 'borg_v3.db')
    assert data['mcp_v3_path'] == str(borg_home / 'borg_v3.db')
    assert data['agent_store_path'] == str(borg_home / 'guild' / 'guild.db')
    assert data['fingerprint']['v3_db_path'] == str(borg_home / 'borg_v3.db')
    assert not (decoy_hermes / 'borg' / 'borg_v3.db').exists()
    assert not (fake_home / '.hermes' / 'guild' / 'guild.db').exists()


def test_borg_dir_only_backcompat_isolates_all_core_storage(tmp_path):
    repo_root = Path(__file__).resolve().parents[2]
    fake_home = tmp_path / 'fake-home'
    legacy_root = tmp_path / 'legacy-borg-root'
    env = os.environ.copy()
    env.update({'HOME': str(fake_home), 'BORG_DIR': str(legacy_root), 'PYTHONPATH': str(repo_root)})
    env.pop('BORG_HOME', None)
    env.pop('HERMES_HOME', None)

    data = _run_probe(repo_root, env)

    assert data['borg_home'] == str(legacy_root)
    assert data['borg_dir'] == str(legacy_root)
    assert data['trace_db_path'] == str(legacy_root / 'traces.db')
    assert data['v3_db_path'] == str(legacy_root / 'borg_v3.db')
    assert data['direct_v3_path'] == str(legacy_root / 'borg_v3.db')
    assert data['mcp_v3_path'] == str(legacy_root / 'borg_v3.db')
    assert data['agent_store_path'] == str(legacy_root / 'guild.db')
    assert not (fake_home / '.borg' / 'borg_v3.db').exists()
    assert not (fake_home / '.hermes' / 'guild' / 'guild.db').exists()
