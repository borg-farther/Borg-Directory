"""Borg Evaluation Instrumentation v1.0  structured logging for every task run."""
from __future__ import annotations
from dataclasses import dataclass, field, asdict
from datetime import datetime, timezone
from typing import Optional
import json, os, sqlite3, uuid

@dataclass
class BorgTaskRecord:
    record_id: str = ""
    timestamp: str = ""
    experiment_id: str = ""
    experiment_arm: str = "control"
    borg_version: str = ""
    model_version: str = ""
    task_id: str = ""
    task_bucket: str = ""
    task_type: str = ""
    task_title: str = ""
    complexity_band: str = "medium"
    tool_heavy: bool = False
    trace_retrieved: bool = False
    trace_ids_used: list = field(default_factory=list)
    trace_count_injected: int = 0
    trace_relevance_scores: list = field(default_factory=list)
    guidance_token_count: int = 0
    guidance_followed: Optional[bool] = None
    completion_status: int = 0
    tokens_total: int = 0
    latency_seconds: float = 0.0
    tools_called: list = field(default_factory=list)
    tool_call_count: int = 0
    errors_encountered: list = field(default_factory=list)
    severe_failure: bool = False
    human_intervention: bool = False
    cost_usd: float = 0.0

    def __post_init__(self):
        if not self.record_id: self.record_id = str(uuid.uuid4())[:8]
        if not self.timestamp: self.timestamp = datetime.now(timezone.utc).isoformat()
    def to_dict(self): return asdict(self)
    def to_json(self): return json.dumps(self.to_dict(), default=str)

@dataclass
class BorgExperimentMetrics:
    arm: str
    task_count: int = 0
    completion_rate: float = 0.0
    success_rate: float = 0.0
    tokens_per_task_mean: float = 0.0
    tokens_per_success_mean: float = 0.0
    latency_p50: float = 0.0
    severe_failure_rate: float = 0.0
    human_rescue_rate: float = 0.0
    completion_rate_bucket_a: float = 0.0
    completion_rate_bucket_b: float = 0.0
    completion_rate_bucket_c: float = 0.0
    trace_retrieval_rate: float = 0.0
    trace_relevance_mean: float = 0.0

    @classmethod
    def from_records(cls, arm, records):
        if not records: return cls(arm=arm)
        n = len(records)
        successes = [r for r in records if r.completion_status == 2]
        completions = [r for r in records if r.completion_status >= 1]
        tokens = [r.tokens_total for r in records]
        tokens_s = [r.tokens_total for r in successes]
        lats = sorted([r.latency_seconds for r in records])
        def bc(recs):
            return len([r for r in recs if r.completion_status >= 1]) / len(recs) if recs else 0
        ba = [r for r in records if r.task_bucket == "A"]
        bb = [r for r in records if r.task_bucket == "B"]
        bcc = [r for r in records if r.task_bucket == "C"]
        all_rel = []
        for r in records: all_rel.extend(r.trace_relevance_scores)
        return cls(
            arm=arm, task_count=n,
            completion_rate=len(completions)/n, success_rate=len(successes)/n,
            tokens_per_task_mean=sum(tokens)/n,
            tokens_per_success_mean=sum(tokens_s)/len(successes) if successes else 0,
            latency_p50=lats[int(n*0.5)] if lats else 0,
            severe_failure_rate=len([r for r in records if r.severe_failure])/n,
            human_rescue_rate=len([r for r in records if r.human_intervention])/n,
            completion_rate_bucket_a=bc(ba), completion_rate_bucket_b=bc(bb), completion_rate_bucket_c=bc(bcc),
            trace_retrieval_rate=len([r for r in records if r.trace_retrieved])/n,
            trace_relevance_mean=sum(all_rel)/len(all_rel) if all_rel else 0,
        )

@dataclass
class BorgExperimentComparison:
    control: BorgExperimentMetrics
    treatment: BorgExperimentMetrics

    @property
    def completion_delta(self):
        if self.control.completion_rate == 0: return 0
        return (self.treatment.completion_rate - self.control.completion_rate) / self.control.completion_rate

    @property
    def verdict(self):
        if self.completion_delta < 0: return "KILL"
        if self.completion_delta < 0.05: return "HOLD"
        if self.treatment.severe_failure_rate > self.control.severe_failure_rate * 1.1: return "HOLD"
        return "SHIP"

    def summary(self, eid="BORG-000"):
        return f"""BORG EVAL  {eid} | VERDICT: {self.verdict}
Completion: {self.control.completion_rate:.0%}  {self.treatment.completion_rate:.0%} ( {self.completion_delta:+.0%})
Tokens/task: {self.control.tokens_per_task_mean:.0f}  {self.treatment.tokens_per_task_mean:.0f}
Bucket A: {self.control.completion_rate_bucket_a:.0%}  {self.treatment.completion_rate_bucket_a:.0%}
Bucket B: {self.control.completion_rate_bucket_b:.0%}  {self.treatment.completion_rate_bucket_b:.0%}
Bucket C: {self.control.completion_rate_bucket_c:.0%}  {self.treatment.completion_rate_bucket_c:.0%}
Severe failures: {self.control.severe_failure_rate:.0%}  {self.treatment.severe_failure_rate:.0%}
Trace retrieval: {self.treatment.trace_retrieval_rate:.0%} | Relevance: {self.treatment.trace_relevance_mean:.2f}"""

DB_PATH = os.path.expanduser("~/.borg/eval_results.db")

def _ensure_db():
    os.makedirs(os.path.dirname(DB_PATH), exist_ok=True)
    db = sqlite3.connect(DB_PATH)
    db.execute("""CREATE TABLE IF NOT EXISTS task_records (
        record_id TEXT PRIMARY KEY, timestamp TEXT, experiment_id TEXT,
        experiment_arm TEXT, task_id TEXT, task_bucket TEXT,
        completion_status INTEGER, data_json TEXT)""")
    db.execute("CREATE INDEX IF NOT EXISTS idx_exp ON task_records(experiment_id)")
    db.commit(); db.close()

def record_task(rec):
    _ensure_db()
    db = sqlite3.connect(DB_PATH)
    db.execute("INSERT OR REPLACE INTO task_records VALUES (?,?,?,?,?,?,?,?)",
        (rec.record_id, rec.timestamp, rec.experiment_id, rec.experiment_arm,
         rec.task_id, rec.task_bucket, rec.completion_status, rec.to_json()))
    db.commit(); db.close()

def load_experiment(eid):
    _ensure_db()
    db = sqlite3.connect(DB_PATH)
    rows = db.execute("SELECT data_json FROM task_records WHERE experiment_id=?", (eid,)).fetchall()
    db.close()
    ctrl, treat = [], []
    for (j,) in rows:
        d = json.loads(j)
        r = BorgTaskRecord(**{k:v for k,v in d.items() if k in BorgTaskRecord.__dataclass_fields__})
        (ctrl if r.experiment_arm == "control" else treat).append(r)
    return ctrl, treat

def evaluate(eid):
    c, t = load_experiment(eid)
    cm = BorgExperimentMetrics.from_records("control", c)
    tm = BorgExperimentMetrics.from_records("treatment", t)
    return BorgExperimentComparison(control=cm, treatment=tm).summary(eid)

if __name__ == "__main__":
    import sys
    print(evaluate(sys.argv[1]) if len(sys.argv) > 1 else "Usage: python instrumentation_schema.py <experiment_id>")
