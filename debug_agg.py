import json
import tempfile
from pathlib import Path
from guild.core.aggregator import PackAggregator

def make_exec(phase_results, session_id="s"):
    lines = []
    lines.append(json.dumps({"type": "execution_started", "session_id": session_id, "phase_index": 0}))
    for phase, result in zip(["Phase1","Phase2","Phase3"], phase_results):
        ev_type = "checkpoint_pass" if result == "pass" else "checkpoint_fail"
        lines.append(json.dumps({
            "type": ev_type,
            "phase": phase,
            "checkpoint": f"{phase}_ck",
            "checkpoint_result": "ok" if result == "pass" else "fail",
            "error": "",
            "duration_s": 1.0,
        }))
    success = all(r == "pass" for r in phase_results)
    lines.append(json.dumps({
        "type": "execution_completed",
        "session_id": session_id,
        "status": "completed" if success else "failed",
        "error": "",
    }))
    return "\n".join(lines)

tmp = Path(tempfile.mkdtemp())

data = [
    ("001", ["pass","pass","pass"]),
    ("002", ["pass","pass","pass"]),
    ("003", ["pass","pass","pass"]),
    ("004", ["pass","fail","pass"]),
    ("005", ["pass","fail","pass"]),
]

agg = PackAggregator("test")
for sid, results in data:
    p = tmp / f"{sid}.jsonl"
    p.write_text(make_exec(results, sid))
    agg.ingest_execution(p)

m = agg.compute_metrics()
print("total:", m["total_executions"])
print("success_count:", m["success_count"])
print("success_rate:", m["success_rate"])
print("phase_metrics:")
for k, v in m["phase_metrics"].items():
    print(f"  {k}:", v)
print("common_failures:", m["common_failures"])
