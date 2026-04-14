# Re-export CLI functions from borg/cli.py using importlib
# to avoid circular import when the package __init__.py has the same name
# as the .py module file.
import importlib.util
import sys
from pathlib import Path

# cli.py lives two levels up from this __init__.py (borg/cli/__init__.py)
_cli_py_path = Path(__file__).parents[1] / "cli.py"
_spec = importlib.util.spec_from_file_location("borg.cli_impl", str(_cli_py_path))
_cli_impl = importlib.util.module_from_spec(_spec)
sys.modules["borg.cli_impl"] = _cli_impl
_spec.loader.exec_module(_cli_impl)

# Re-export all public CLI commands
__all__ = [
    "main",
    "_cmd_apply",
    "_cmd_recall",
    "_cmd_search",
    "_cmd_pull",
    "_cmd_try",
    "_cmd_init",
    "_cmd_publish",
    "_cmd_feedback",
    "_cmd_feedback_v3",
    "_cmd_debug",
    "_cmd_start",
    "_cmd_convert",
    "_cmd_generate",
    "_cmd_list",
    "_cmd_observe",
    "_cmd_version",
    "_cmd_autopilot",
    "_cmd_setup_claude",
    "_cmd_setup_cursor",
    "_cmd_reputation",
    "_cmd_status",
]

for _name in __all__:
    globals()[_name] = getattr(_cli_impl, _name)
