"""Compatibility entry point for installing Borg into Claude Code.

The public setup path is:

    borg setup-claude --scope user --verify --fix

``borg-install`` remains as a convenience alias for older docs/scripts.  It must
not write stale Claude Desktop config or call removed Borg subcommands.
"""

from __future__ import annotations

import argparse
from argparse import Namespace
from collections.abc import Sequence

from borg.cli import _cmd_setup_claude


def main(argv: Sequence[str] | None = None) -> int:
    """Run the canonical Claude Code setup command.

    ``argparse`` owns ``--help`` so help is side-effect safe: it prints usage and
    exits before the setup alias writes any Claude/Borg config.
    """
    parser = argparse.ArgumentParser(
        prog="borg-install",
        description="Compatibility alias for: borg setup-claude --scope user --verify --fix",
    )
    parser.parse_args(argv)
    print("borg-install is an alias for: borg setup-claude --scope user --verify --fix")
    return _cmd_setup_claude(Namespace(scope="user", verify=True, fix=True))


if __name__ == "__main__":  # pragma: no cover
    raise SystemExit(main())
