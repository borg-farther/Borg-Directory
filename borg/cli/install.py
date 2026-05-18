"""Compatibility entry point for installing Borg into Claude Code.

The public setup path is:

    borg setup-claude --scope user --verify --fix

``borg-install`` remains as a convenience alias for older docs/scripts.  It must
not write stale Claude Desktop config or call removed Borg subcommands.
"""

from __future__ import annotations

from argparse import Namespace

from borg.cli import _cmd_setup_claude


def main() -> int:
    """Run the canonical Claude Code setup command."""
    print("borg-install is an alias for: borg setup-claude --scope user --verify --fix")
    return _cmd_setup_claude(Namespace(scope="user", verify=True, fix=True))


if __name__ == "__main__":  # pragma: no cover
    raise SystemExit(main())
