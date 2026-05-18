"""Golden Query Test Suite. 16/20 must pass for release. Self-contained."""
import pytest, sys, os, tempfile, shutil, sqlite3, uuid
from datetime import datetime, timezone

GOLDEN_TRACES = [
    ("ModuleNotFoundError: No module named flask", "python", "pip install flask installs the missing package", "success"),
    ("Error: EADDRINUSE :::3000", "nodejs", "Kill process on port 3000 with lsof or change port", "success"),
    ("django.db.utils.OperationalError: no such table", "django", "Run python manage.py makemigrations and migrate", "success"),
    ("fatal: not a git repository", "git", "Run git init in the correct directory", "success"),
    ("Permission denied (publickey)", "git", "Add ssh key with ssh-add or switch to https", "success"),
    ("Cannot find module react", "nodejs", "Run npm install react to install missing dependency", "success"),
    ("TypeError: Cannot read properties of undefined", "typescript", "Add null check or optional chaining before access", "success"),
    ("docker: port already allocated", "docker", "Stop the conflicting container or remap port", "success"),
    ("FATAL: role postgres does not exist", "postgresql", "Run createuser postgres or create the role", "success"),
    ("error[E0382]: borrow of moved value", "rust", "Use clone or pass by reference instead of moving ownership", "success"),
    ("IndentationError: unexpected indent", "python", "Fix whitespace convert tabs to spaces or fix indent", "success"),
    ("OperationalError: database is locked", "python", "Close other connections or enable WAL mode on SQLite", "success"),
    ("Error: ENOMEM", "nodejs", "Increase heap with max-old-space-size or fix memory leak", "success"),
    ("ConnectionRefusedError: [Errno 111]", "python", "Start the target service or check the port", "success"),
    ("error TS2307: Cannot find module", "typescript", "Install missing types package or fix tsconfig paths", "success"),
    ("OCI runtime create failed", "docker", "Rebuild image for correct platform or restart daemon", "success"),
    ("ActionController::RoutingError", "ruby", "Add missing route to routes.rb", "success"),
    ("CORS: No Access-Control-Allow-Origin", "nodejs", "Add cors middleware or configure proxy", "success"),
    ("OSError: [Errno 28] No space left", "linux", "Free disk space with docker system prune or clean files", "success"),
    ("SSL: CERTIFICATE_VERIFY_FAILED", "python", "Install or update ca-certificates or certifi", "success"),
]

@pytest.fixture(autouse=True, scope="session")
def setup_test_db():
    test_home = tempfile.mkdtemp()
    os.environ["BORG_HOME"] = test_home
    db_path = os.path.join(test_home, "traces.db")
    db = sqlite3.connect(db_path)
    db.execute("""CREATE TABLE IF NOT EXISTS traces (
        id TEXT PRIMARY KEY, task_description TEXT, root_cause TEXT,
        approach_summary TEXT, outcome TEXT, technology TEXT,
        helpfulness_score REAL DEFAULT 0.75, times_shown INTEGER DEFAULT 0,
        times_helped INTEGER DEFAULT 0, source TEXT, agent_id TEXT,
        created_at TEXT, tool_calls INTEGER DEFAULT 0,
        errors_encountered INTEGER DEFAULT 0, files_read TEXT DEFAULT '[]',
        files_modified TEXT DEFAULT '[]', key_files TEXT DEFAULT '[]',
        dead_ends TEXT DEFAULT '[]', keywords TEXT, error_patterns TEXT,
        error_class TEXT)""")
    try:
        db.execute("""CREATE VIRTUAL TABLE IF NOT EXISTS traces_fts
            USING fts5(id, task_description, approach_summary, root_cause)""")
    except Exception: pass
    for task, tech, approach, outcome in GOLDEN_TRACES:
        tid = str(uuid.uuid4())
        db.execute("INSERT INTO traces VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)",
            (tid, task, "", approach, outcome, tech, 0.75, 0, 0, "golden_seed", "test",
             datetime.now(timezone.utc).isoformat(), 0, 0, "[]", "[]", "[]", "[]", "", "", ""))
        try: db.execute("INSERT INTO traces_fts VALUES (?,?,?,?)", (tid, task, approach, ""))
        except: pass
    db.commit(); db.close()
    yield
    shutil.rmtree(test_home, ignore_errors=True)

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", ".."))

GOLDEN_QUERIES = [
    ("GQ-01", "ModuleNotFoundError: No module named flask", "python", ["pip install", "install flask"]),
    ("GQ-02", "Error: EADDRINUSE :::3000", "nodejs", ["kill", "port", "lsof"]),
    ("GQ-03", "django.db.utils.OperationalError: no such table", "django", ["migrate", "makemigrations"]),
    ("GQ-04", "fatal: not a git repository", "git", ["git init", "correct directory"]),
    ("GQ-05", "Permission denied (publickey)", "git", ["ssh key", "ssh-add", "https"]),
    ("GQ-06", "Cannot find module react", "nodejs", ["npm install", "install react"]),
    ("GQ-07", "TypeError: Cannot read properties of undefined", "typescript", ["null check", "optional chaining"]),
    ("GQ-08", "docker: port already allocated", "docker", ["stop", "remap", "container"]),
    ("GQ-09", "FATAL: role postgres does not exist", "postgresql", ["createuser", "create", "role"]),
    ("GQ-10", "error[E0382]: borrow of moved value", "rust", ["clone", "reference", "ownership"]),
    ("GQ-11", "IndentationError: unexpected indent", "python", ["whitespace", "spaces", "tabs", "indent"]),
    ("GQ-12", "OperationalError: database is locked", "python", ["close", "wal", "connection"]),
    ("GQ-13", "Error: ENOMEM", "nodejs", ["heap", "memory", "max-old-space"]),
    ("GQ-14", "ConnectionRefusedError: [Errno 111]", "python", ["start", "service", "port"]),
    ("GQ-15", "error TS2307: Cannot find module", "typescript", ["types", "tsconfig", "install"]),
    ("GQ-16", "OCI runtime create failed", "docker", ["daemon", "rebuild", "platform"]),
    ("GQ-17", "ActionController::RoutingError", "ruby", ["route", "routes.rb"]),
    ("GQ-18", "CORS: No Access-Control-Allow-Origin", "nodejs", ["cors", "middleware", "proxy"]),
    ("GQ-19", "OSError: [Errno 28] No space left", "linux", ["free", "prune", "clean", "disk"]),
    ("GQ-20", "SSL: CERTIFICATE_VERIFY_FAILED", "python", ["certificate", "certifi", "ca-certificates"]),
]

@pytest.mark.parametrize("gq_id,query,domain,expected_keywords", GOLDEN_QUERIES)
def test_golden_query(gq_id, query, domain, expected_keywords):
    from borg.core.trace_matcher import find_relevant
    results = find_relevant(query, technology=domain)
    assert len(results) > 0, f"{gq_id}: No results"
    first = results[0].get("approach_summary", "").lower()
    assert any(kw.lower() in first for kw in expected_keywords), f"{gq_id}: Got '{first[:80]}'"

def test_pass_rate():
    from borg.core.trace_matcher import find_relevant
    p = sum(1 for _,q,d,kws in GOLDEN_QUERIES if find_relevant(q,technology=d) and any(k.lower() in find_relevant(q,technology=d)[0].get("approach_summary","").lower() for k in kws))
    assert p >= 16, f"Only {p}/20 passed"
