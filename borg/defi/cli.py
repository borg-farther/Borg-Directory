"""
CLI entry point for borg defi scans.

Usage:
    borg-defi yields [--min-apy N] [--min-tvl N] [--limit N]
    borg-defi tokens [--limit N]
    borg-defi tvl [--limit N]
    borg-defi stablecoins [--depeg-threshold N] [--top N]
    borg-defi scan-all

Installed via pyproject.toml entry point: borg-defi = "borg.defi.cli:main"
"""

from __future__ import annotations

import argparse
import sys

# Guard: require aiohttp before any scan logic runs
_AIOHTTP_AVAILABLE: bool
try:
    import aiohttp  # noqa: F401
    _AIOHTTP_AVAILABLE = True
except ImportError:
    _AIOHTTP_AVAILABLE = False


def _die(message: str) -> int:
    """Print error and exit with error code."""
    print(f"Error: {message}", file=sys.stderr)
    return 1


def _cmd_yields(args: argparse.Namespace) -> int:
    """Run yield hunter scan."""
    from borg.defi.mcp_tools import borg_defi_yields
    result = borg_defi_yields(
        min_apy=args.min_apy,
        min_tvl=args.min_tvl,
        max_results=args.limit,
    )
    print(result)
    return 0


def _cmd_tokens(args: argparse.Namespace) -> int:
    """Run token radar scan."""
    from borg.defi.mcp_tools import borg_defi_tokens
    result = borg_defi_tokens(max_results=args.limit)
    print(result)
    return 0


def _cmd_tvl(args: argparse.Namespace) -> int:
    """Run TVL pulse scan."""
    from borg.defi.mcp_tools import borg_defi_tvl
    result = borg_defi_tvl(max_results=args.limit)
    print(result)
    return 0


def _cmd_stablecoins(args: argparse.Namespace) -> int:
    """Run stablecoin watch scan."""
    from borg.defi.mcp_tools import borg_defi_stablecoins
    result = borg_defi_stablecoins(
        depeg_threshold=args.depeg_threshold,
        top_n=args.top,
    )
    print(result)
    return 0


def _cmd_scan_all(args: argparse.Namespace) -> int:
    """Run all four scans."""
    from borg.defi.mcp_tools import borg_defi_scan_all
    result = borg_defi_scan_all()
    print(result)
    return 0


def main() -> int:
    """Parse CLI arguments and run the requested scan."""
    if not _AIOHTTP_AVAILABLE:
        print(
            "aiohttp is required for DeFi scans. Install it with:\n"
            "  pip install agent-borg[defi]\n"
            "  # or\n"
            "  pip install aiohttp>=3.9.0",
            file=sys.stderr,
        )
        return 1

    parser = argparse.ArgumentParser(
        prog="borg-defi",
        description="DeFi scanner — yields, tokens, TVL, stablecoins.",
    )
    sub = parser.add_subparsers(dest="command", required=True)

    # borg-defi yields
    p_yields = sub.add_parser("yields", help="Top yield opportunities from DeFiLlama")
    p_yields.add_argument(
        "--min-apy", type=float, default=5.0,
        help="Minimum APY %% to include (default: 5.0)",
    )
    p_yields.add_argument(
        "--min-tvl", type=float, default=1_000_000,
        help="Minimum TVL in USD (default: 1_000_000)",
    )
    p_yields.add_argument(
        "--limit", type=int, default=15,
        help="Maximum number of pools to return (default: 15)",
    )

    # borg-defi tokens
    p_tokens = sub.add_parser("tokens", help="Latest and boosted tokens from DexScreener")
    p_tokens.add_argument(
        "--limit", type=int, default=10,
        help="Maximum number of latest tokens to return (default: 10)",
    )

    # borg-defi tvl
    p_tvl = sub.add_parser("tvl", help="Protocol TVL and biggest movers from DeFiLlama")
    p_tvl.add_argument(
        "--limit", type=int, default=20,
        help="Maximum number of movers to return (default: 20)",
    )

    # borg-defi stablecoins
    p_stable = sub.add_parser(
        "stablecoins", help="Stablecoin peg monitor from DeFiLlama"
    )
    p_stable.add_argument(
        "--depeg-threshold", type=float, default=0.005,
        help="Price deviation from $1.0 to trigger depeg alert as decimal (default: 0.005)",
    )
    p_stable.add_argument(
        "--top", type=int, default=10,
        help="Number of top stablecoins to display (default: 10)",
    )

    # borg-defi scan-all
    sub.add_parser("scan-all", help="Run all four DeFi scans")

    args = parser.parse_args()

    if args.command == "yields":
        return _cmd_yields(args)
    elif args.command == "tokens":
        return _cmd_tokens(args)
    elif args.command == "tvl":
        return _cmd_tvl(args)
    elif args.command == "stablecoins":
        return _cmd_stablecoins(args)
    elif args.command == "scan-all":
        return _cmd_scan_all(args)
    else:
        return _die(f"Unknown command: {args.command}")


if __name__ == "__main__":
    sys.exit(main())
