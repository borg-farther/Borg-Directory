"""Five Invariants  CI gates.

Current status (Phase 0):
  I3  LIVE
  I4  LIVE
  I1, I2, I5  Phase 1 (require borg-bench harness + JSON schema)
"""
import os, re, sqlite3, pytest

DB_PATH = os.path.expanduser(os.environ.get('BORG_HOME', '~/.borg') + '/traces.db')

PII_PATTERNS = {
    'unix_path':    r'(/home/[a-zA-Z]|/root/|/Users/[a-zA-Z])',
    'openai_key':   r'\bsk-[a-zA-Z0-9]{20,}',
    'github_token': r'\bghp_[a-zA-Z0-9]{20,}',
    'bearer':       r'Bearer\s+[a-zA-Z0-9._-]{20,}',
    'srv_hostname': r'\bsrv\d{7}\b',
    'email':        r'\b[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}\b',
    'db_url':       r'(postgres|mysql|mongodb)://[^:]+:[^@]+@',
}

NON_ORGANIC_SOURCES = ('seed_pack', 'golden_seed', 'curated')


def test_invariant_i3_no_synthetic_in_traces_table():
    """I3: real/synthetic architectural separation  no non-organic rows in traces."""
    if not os.path.exists(DB_PATH):
        pytest.skip("No DB")
    with sqlite3.connect(DB_PATH) as conn:
        n = conn.execute(
            f"SELECT COUNT(*) FROM traces WHERE source IN ({','.join('?'*len(NON_ORGANIC_SOURCES))})",
            NON_ORGANIC_SOURCES,
        ).fetchone()[0]
    assert n == 0, f"INVARIANT I3 VIOLATED: {n} non-organic rows in traces table"


def test_invariant_i3_save_trace_rejects_synthetic():
    """I3 (write-path): save_trace must raise on non-organic source."""
    from borg.core.traces import save_trace
    for src in NON_ORGANIC_SOURCES:
        try:
            save_trace({
                'id': f'test-{src}',
                'task_description': 'invariant check',
                'outcome': 'success',
                'source': src,
                'created_at': '2026-04-16T00:00:00Z',
            })
            pytest.fail(f"save_trace accepted source={src!r}  I3 violated at write path")
        except ValueError:
            pass  # expected


def test_invariant_i4_no_pii_in_committed_db():
    """I4: PII never ships. Scan text columns of both trace tables for known patterns."""
    if not os.path.exists(DB_PATH):
        pytest.skip("No DB")
    offenders = []
    with sqlite3.connect(DB_PATH) as conn:
        for table in ('traces', 'seed_traces'):
            try:
                rows = conn.execute(
                    f"SELECT id, task_description, root_cause, approach_summary FROM {table}"
                ).fetchall()
            except sqlite3.OperationalError:
                continue
            for row in rows:
                tid = row[0]
                for text in row[1:]:
                    if text is None:
                        continue
                    for name, pat in PII_PATTERNS.items():
                        if re.search(pat, text):
                            offenders.append(f"{table}/{tid}: {name}")
    assert not offenders, f"INVARIANT I4 VIOLATED ({len(offenders)} rows): {offenders[:10]}"


def test_tiered_retrieval_labels_source_tier():
    """Phase 0 retrieval contract: every result from find_relevant() must have source_tier."""
    from borg.core.trace_matcher import find_relevant
    r = find_relevant('ModuleNotFoundError: test', technology='python', limit=3)
    if not r:
        pytest.skip("No results returned  DB may be empty")
    for item in r:
        assert 'source_tier' in item, f"Missing source_tier: {item.get('id', '?')}"
        assert item['source_tier'] in ('real', 'synthetic')


# Placeholders  Phase 1 deliverables

def test_invariant_i1_cold_start_first_query():
    pytest.skip("Pending borg-bench harness  Phase 1")

def test_invariant_i2_readme_numbers_match_bench():
    pytest.skip("Pending borg-bench output + BENCH-CLAIMS block  Phase 1")

def test_invariant_i5_exported_trace_validates_format_v1():
    pytest.skip("Pending BORG_TRACE_FORMAT_v1 JSON schema  Phase 1")
