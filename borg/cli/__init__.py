"""Load legacy CLI implementation into package namespace.

This keeps `import borg.cli` patch-friendly for tests that monkeypatch
symbols like `borg.cli.load_session` and `borg.cli.get_borg_dir`.
"""

from pathlib import Path

_cli_py_path = Path(__file__).parents[1] / "cli.py"
_source = _cli_py_path.read_text(encoding="utf-8")
exec(compile(_source, str(_cli_py_path), "exec"), globals(), globals())
