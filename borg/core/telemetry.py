"""Borg retrieval telemetry. All queries PII-stripped before logging."""
import json, logging, os, re
from datetime import datetime, timezone
from pathlib import Path

logger = logging.getLogger(__name__)
TELEMETRY_FILE = Path(os.path.expanduser("~/.borg/telemetry.jsonl"))
_session_recalls = []

def _strip_pii_query(t):
    if not t: return t
    t = re.sub(r'(/[\w./-]{3,})', '<path>', t)
    t = re.sub(r'([A-Z]:\\[\w\\.-]+)', '<path>', t)
    t = re.sub(r'(sk-[a-zA-Z0-9]{10,})', '<key>', t)
    t = re.sub(r'(ghp_[a-zA-Z0-9]{10,})', '<token>', t)
    t = re.sub(r'(Bearer\s+[a-zA-Z0-9._-]{10,})', '<bearer>', t)
    t = re.sub(r'\b(?!127\.0\.0\.1)(\d{1,3}\.\d{1,3}\.\d{1,3}\.\d{1,3})\b', '<ip>', t)
    t = re.sub(r'[\w.-]+@[\w.-]+\.\w+', '<email>', t)
    t = re.sub(r'(arn:aws:[a-zA-Z0-9:/_-]+)', '<arn>', t)
    t = re.sub(r'(postgresql|mysql|mongodb)://[^\s]+', '<dburl>', t)
    return t

def log_recall(query, results, source="borg_observe"):
    safe_query = _strip_pii_query(query)
    entry = {"ts": datetime.now(timezone.utc).isoformat(), "event": "recall", "source": source, "query": safe_query[:100], "result_count": len(results), "result_ids": [r.get("trace_id","") for r in results[:5] if isinstance(r,dict)]}
    _session_recalls.append(entry)
    try:
        TELEMETRY_FILE.parent.mkdir(parents=True, exist_ok=True)
        with open(TELEMETRY_FILE, "a") as f: f.write(json.dumps(entry)+"\n")
    except Exception: pass

def log_usage(trace_id, action="referenced"):
    entry = {"ts": datetime.now(timezone.utc).isoformat(), "event": "usage", "trace_id": trace_id, "action": action}
    try:
        with open(TELEMETRY_FILE, "a") as f: f.write(json.dumps(entry)+"\n")
    except Exception: pass

def get_usage_rate(last_n=50):
    if not TELEMETRY_FILE.exists(): return 0.0
    lines = TELEMETRY_FILE.read_text().strip().split("\n")[-last_n:]
    recalled, used = set(), set()
    for l in lines:
        try:
            e = json.loads(l)
            if e.get("event")=="recall": recalled.update(e.get("result_ids",[]))
            elif e.get("event")=="usage": used.add(e.get("trace_id",""))
        except (json.JSONDecodeError, ValueError, TypeError, AttributeError, KeyError):  # F-05 FIX
            pass
    recalled.discard(""); used.discard("")
    return len(used & recalled) / max(len(recalled), 1)
