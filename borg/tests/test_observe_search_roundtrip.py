"""v3.2.4 regression tests — borg observe → borg search roundtrip.

Bug context: In v3.2.3 the P1.1 MiniMax experiment found that `borg search`
never found traces written by observe/apply, because borg_search() only read
from the pack index. This made C2 (seeded) indistinguishable from C1 (empty).

These tests lock in the fix:
  1. save_trace() + borg_search() find the trace immediately
  2. Multiple observations all surface for a shared keyword
  3. The index persists across process boundaries (subprocess call)
"""
from __future__ import annotations

import importlib
import json
import os
import shutil
import subprocess
import sys
import tempfile
import textwrap
import unittest
from pathlib import Path
from unittest.mock import patch


def _reload_traces_stack():
    import borg.core.traces as _t
    importlib.reload(_t)
    import borg.core.trace_matcher as _tm
    importlib.reload(_tm)
    import borg.core.search as _s
    importlib.reload(_s)
    return _t


class TestObserveSearchRoundtrip(unittest.TestCase):
    """Regression guard for the v3.2.3 observe→search bug."""

    def setUp(self):
        self.tmp = tempfile.mkdtemp()
        self.borg_home = Path(self.tmp) / ".borg"
        self.borg_home.mkdir(parents=True, exist_ok=True)
        self._old_env = os.environ.get("BORG_HOME")
        os.environ["BORG_HOME"] = str(self.borg_home)
        self._traces = _reload_traces_stack()

    def tearDown(self):
        if self._old_env is None:
            os.environ.pop("BORG_HOME", None)
        else:
            os.environ["BORG_HOME"] = self._old_env
        _reload_traces_stack()
        shutil.rmtree(self.tmp, ignore_errors=True)

    def _save_observation(self, task: str, context: str = "", error: str = ""):
        capture = self._traces.TraceCapture(task=task, agent_id="test")
        if context or error:
            capture.on_tool_call(
                tool_name="observe",
                args={"task": task, "context": context},
                result=error or context,
            )
        trace = capture.extract_trace(
            outcome="observed",
            approach_summary=context[:500] if context else "",
        )
        trace["source"] = "observe-cli"
        return self._traces.save_trace(trace, db_path=str(self.borg_home / "traces.db"))

    def _search(self, query: str):
        from borg.core.search import borg_search
        with patch("borg.core.uri._fetch_index", return_value={"packs": []}):
            raw = borg_search(query, mode="text")
        return json.loads(raw)

    def test_observe_then_search_finds_trace(self):
        """Regression: observe a django task, search 'django', see the trace."""
        self._save_observation(
            task="Fix django authentication bug in middleware",
            context="AttributeError on request.user in login_required decorator",
        )
        result = self._search("django")
        self.assertTrue(result.get("success"))
        matches = result.get("matches", [])
        trace_matches = [m for m in matches if m.get("source") == "trace"]
        self.assertGreater(
            len(trace_matches), 0,
            "borg_search must find the trace we just observed — "
            "v3.2.3 P1.1 bug guard",
        )

    def test_observe_multiple_then_search_returns_relevant(self):
        """Three observations on related topics all surface for a keyword."""
        self._save_observation(
            task="Fix django migration schema drift",
            context="OperationalError: no such column users.is_verified",
        )
        self._save_observation(
            task="Debug django ORM N+1 query in admin",
            context="django.db.utils.OperationalError too many queries",
        )
        self._save_observation(
            task="Resolve django authentication redirect loop",
            context="django.contrib.auth infinite redirect",
        )
        result = self._search("django")
        matches = result.get("matches", [])
        trace_matches = [m for m in matches if m.get("source") == "trace"]
        self.assertGreaterEqual(
            len(trace_matches), 3,
            f"Expected >=3 trace matches for 'django', got {len(trace_matches)}",
        )

    def test_search_index_persistent_across_processes(self):
        """A trace written in one python call is visible to a subprocess."""
        self._save_observation(
            task="Fix flask blueprint registration order",
            context="werkzeug routing conflict on duplicate endpoint",
        )
        code = textwrap.dedent("""
            import json
            from unittest.mock import patch
            from borg.core.search import borg_search
            with patch('borg.core.uri._fetch_index', return_value={'packs': []}):
                r = borg_search('flask', mode='text')
            print(r)
        """)
        env = os.environ.copy()
        env["BORG_HOME"] = str(self.borg_home)
        repo_root = Path(__file__).resolve().parents[2]
        env["PYTHONPATH"] = str(repo_root) + os.pathsep + env.get("PYTHONPATH", "")
        proc = subprocess.run(
            [sys.executable, "-c", code],
            capture_output=True, text=True, env=env, timeout=30,
        )
        self.assertEqual(proc.returncode, 0,
                         f"subprocess failed: stderr={proc.stderr}")
        last_line = [ln for ln in proc.stdout.strip().splitlines() if ln.strip()][-1]
        result = json.loads(last_line)
        self.assertTrue(result.get("success"))
        matches = result.get("matches", [])
        trace_matches = [m for m in matches if m.get("source") == "trace"]
        self.assertGreater(
            len(trace_matches), 0,
            "Trace written in parent process must be visible in subprocess",
        )


if __name__ == "__main__":
    unittest.main()
