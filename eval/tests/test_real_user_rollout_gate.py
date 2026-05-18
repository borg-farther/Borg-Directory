from __future__ import annotations

import json
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]


def test_real_user_rollout_gate_script_exists_and_mentions_no_fake_users() -> None:
    path = ROOT / "eval" / "real_user_rollout_gate.py"
    text = path.read_text(encoding="utf-8")
    assert "real_user_rollout" in text
    assert "no_fake_user_policy" in text
    assert "first-10 external-user evidence" in text


def test_real_user_rollout_gate_blocks_100_when_first_10_scoreboard_empty() -> None:
    proc = subprocess.run(
        [sys.executable, "eval/real_user_rollout_gate.py"],
        cwd=str(ROOT),
        text=True,
        capture_output=True,
        timeout=60,
    )
    assert proc.returncode == 1
    payload = json.loads(proc.stdout)
    assert payload["infrastructure_ready_for_100"] is True
    assert payload["ready_for_10_controlled_beta"] is True
    assert payload["ready_for_100_real_users"] is False
    assert payload["max_recommended_real_users_now"] == 10
    assert any("first-10 external-user evidence" in b for b in payload["blockers"])


def test_real_user_rollout_gate_snapshot_is_machine_readable() -> None:
    path = ROOT / "eval" / "real_user_rollout_gate_snapshot.json"
    assert path.exists()
    data = json.loads(path.read_text(encoding="utf-8"))
    assert data["gate_type"] == "real_user_rollout"
    assert data["important_distinction"].startswith("load/readiness snapshots are synthetic")
    assert data["max_recommended_real_users_now"] in {0, 10, 100}
    assert data["no_fake_user_policy"].startswith("Do not mark first-10 complete")
