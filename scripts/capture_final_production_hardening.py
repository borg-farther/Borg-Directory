#!/usr/bin/env python3
import json
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
PYTHON = sys.executable
commands = [
    [PYTHON, "-m", "pytest", "-q", "borg/tests/test_e2e_learning_loop_v3.py", "borg/tests/test_v3_integration.py", "borg/tests/test_failure_memory.py", "borg/tests/test_mutation_engine.py", "borg/tests/test_feedback_loop.py", "borg/tests/test_contextual_selector.py", "--tb=short"],
    [PYTHON, "-m", "pytest", "-q", "borg/tests/test_rescue.py", "borg/tests/test_runtime_fingerprint.py", "borg/tests/test_embeddings_schema_compat.py", "eval/tests/test_security_hardening_baseline.py", "borg/tests/test_confidence_gate.py", "borg/tests/test_borg_observe_confidence_gate.py", "borg/tests/test_first_10_readiness.py", "--tb=short"],
    [PYTHON, "-m", "pytest", "-q", "eval/tests/test_benchmark_evidence_contract.py", "--tb=short"],
    [PYTHON, "eval/run_first_user_release_gate.py"],
    [PYTHON, "scripts/security_gate_check.py"],
    [PYTHON, "-c", "from borg.integrations import mcp_server\nfor name,kw in [('unrelated',dict(task='continue Borg readiness/get it there: fix borg_observe irrelevant guidance/runtime mismatch and proceed toward first-user readiness',context='python borg mcp runtime readiness')),('permission',dict(task='Fix bash: ./deploy.sh: Permission denied',context='bash permission denied chmod'))]:\n out=mcp_server.borg_observe(**kw)\n print('---',name,'---')\n print(out[:1200])\n print('NO_CONFIDENT=', 'NO_CONFIDENT_MATCH' in out or 'NO CONFIDENT MATCH' in out)\n print('STALE=', 'Plugin directory ~/.hermes/plugins/' in out or 'BORG_HOME env var' in out or 'PACK GUIDANCE (python-type-error)' in out)\n print('PERMISSION=', 'Permission denied' in out or 'chmod' in out or 'PACK GUIDANCE (bash-permission-denied)' in out)"],
    [PYTHON, "-c", "import json, pathlib\np=pathlib.Path('eval/first_10_user_scoreboard.json')\nprint(p.read_text() if p.exists() else 'MISSING')"],
    ["git", "status", "--short"],
]
labels = [
    "learning_loop_suite",
    "core_production_gates",
    "benchmark_evidence_contract",
    "first_user_release_gate",
    "security_gate_check",
    "mcp_observe_canaries_in_process",
    "first_10_scoreboard",
    "git_status_short",
]
results = []
for label, cmd in zip(labels, commands):
    proc = subprocess.run(cmd, cwd=ROOT, text=True, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
    results.append({"label": label, "command": cmd, "returncode": proc.returncode, "stdout": proc.stdout, "stderr": proc.stderr})

out = ROOT / "eval" / "20260515_final_production_hardening_commands.json"
out.write_text(json.dumps({"results": results}, indent=2), encoding="utf-8")
print(str(out))
print(json.dumps([{r["label"]: r["returncode"]} for r in results], indent=2))
raise SystemExit(0 if all(r["returncode"] == 0 for r in results[:-1]) else 1)
