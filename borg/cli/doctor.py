"""
borg doctor  verify your Borg installation is working.
Run: python3 -m borg.cli.doctor
"""
from __future__ import annotations

import argparse
import hashlib
import json
import os
import sqlite3
import sys
from pathlib import Path
from typing import Any


def _sqlite_count(db_path: Path, table: str) -> int | None:
    if not db_path.exists():
        return None
    try:
        with sqlite3.connect(str(db_path)) as db:
            return int(db.execute(f"SELECT COUNT(*) FROM {table}").fetchone()[0])
    except Exception:
        return None


def runtime_fingerprint() -> dict[str, Any]:
    import borg

    borg_home = Path(os.environ.get("BORG_HOME", "~/.borg")).expanduser()
    module_path = Path(getattr(borg, "__file__", "")).resolve()
    try:
        module_hash = hashlib.sha256(module_path.read_bytes()).hexdigest()[:16]
    except Exception:
        module_hash = ""
    trace_db = borg_home / "traces.db"
    atom_db = borg_home / "atoms.db"
    return {
        "package_version": getattr(borg, "__version__", "unknown"),
        "module_path": str(module_path),
        "module_hash": module_hash,
        "borg_home": str(borg_home),
        "trace_db_path": str(trace_db),
        "atom_db_path": str(atom_db),
        "trace_count": _sqlite_count(trace_db, "traces"),
        "atom_count": _sqlite_count(atom_db, "atoms"),
        "pid": os.getpid(),
        "python": sys.executable,
    }


def run(json_mode: bool = False) -> int:
    borg_home = Path(os.environ.get("BORG_HOME", "~/.borg")).expanduser()
    ok = True
    checks: list[dict[str, Any]] = []

    def record(name: str, passed: bool, detail: str = "") -> None:
        nonlocal ok
        checks.append({"name": name, "passed": bool(passed), "detail": detail})
        if not passed:
            ok = False

    db_path = borg_home / "traces.db"
    if not db_path.exists() or _sqlite_count(db_path, "traces") in (None, 0):
        try:
            from borg.integrations.mcp_server import borg_observe as _bo
            _bo(task="Docker apt-get install fails", context="")
        except Exception as exc:
            record("seed_traces", False, f"seeding failed: {exc}")
    trace_count = _sqlite_count(db_path, "traces")
    record("trace_db", bool(trace_count and trace_count > 0), f"{trace_count or 0} traces at {db_path}")

    try:
        sys.path.insert(0, str(Path(__file__).parent.parent.parent))
        from borg.integrations.mcp_server import borg_observe
        result = borg_observe(task="Docker apt-get package not found", context="")
        action = next((line for line in result.split("\n") if line.startswith("ACTION:")), None)
        conf = next((line for line in result.split("\n") if "BORG [" in line), "")
        record("borg_observe", bool(action), (action or "NO ACTION")[:120] + (f" | {conf}" if conf else ""))
    except Exception as exc:
        record("borg_observe", False, str(exc))

    try:
        from borg.integrations.mcp_server import borg_observe, borg_rate
        borg_observe(task="Django migration error", context="")
        rate = borg_rate(helpful=True)
        record("borg_rate", "recorded" in rate.lower(), rate[:120])
    except Exception as exc:
        record("borg_rate", False, str(exc))

    try:
        import subprocess
        msg = '{"jsonrpc":"2.0","id":1,"method":"initialize","params":{"protocolVersion":"2024-11-05","capabilities":{},"clientInfo":{"name":"doctor","version":"1.0"}}}'
        proc = subprocess.run(
            [sys.executable, "-m", "borg.integrations.mcp_server"],
            input=msg,
            capture_output=True,
            text=True,
            timeout=5,
            cwd=str(Path(__file__).parent.parent.parent),
        )
        record("mcp_stdio", '"result"' in proc.stdout, "responds to initialize" if '"result"' in proc.stdout else proc.stderr[:120])
    except Exception as exc:
        record("mcp_stdio", False, str(exc))

    payload = {"success": ok, "runtime": runtime_fingerprint(), "checks": checks}
    if json_mode:
        print(json.dumps(payload, indent=2, sort_keys=True))
    else:
        print("\n         BORG DOCTOR                  \n")
        for check in checks:
            status = "PASS" if check["passed"] else "FAIL"
            print(f"  {status}: {check['name']} — {check['detail']}")
        print("\nRuntime fingerprint:")
        for key, value in payload["runtime"].items():
            print(f"  {key}: {value}")
        print("\n   ALL CHECKS PASSED  Borg is ready\n" if ok else "\n   SOME CHECKS FAILED  see above\n")
    return 0 if ok else 1


def main() -> int:
    parser = argparse.ArgumentParser(description="Verify Borg runtime and print a runtime fingerprint")
    parser.add_argument("--json", action="store_true", help="emit machine-readable runtime proof")
    args = parser.parse_args()
    return run(json_mode=args.json)


def run_doctor() -> int:
    """Console-script entrypoint used by pyproject.toml."""
    return main()


if __name__ == "__main__":
    raise SystemExit(main())
