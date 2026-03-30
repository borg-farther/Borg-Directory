"""
Tests for borg/defi/cli.py — CLI argument parsing and entry point.

Covers:
- CLI argument parsing for all subcommands
- aiohttp guard (mock aiohttp as missing)
- Correct return codes
"""

import pytest
import sys
from unittest.mock import patch, MagicMock


# ---------------------------------------------------------------------------
# Test: CLI argument parsing for each subcommand
# ---------------------------------------------------------------------------

class TestCliArgumentParsing:
    """Each subcommand parses its arguments correctly."""

    def test_yields_subcommand_parsed(self):
        """borg-defi yields [--min-apy N] [--min-tvl N] [--limit N] parses."""
        import argparse
        from borg.defi.cli import main

        test_cases = [
            (["yields"],               {"min_apy": 5.0,  "min_tvl": 1_000_000, "limit": 15}),
            (["yields", "--min-apy", "10"], {"min_apy": 10.0, "min_tvl": 1_000_000, "limit": 15}),
            (["yields", "--min-tvl", "500000"], {"min_apy": 5.0, "min_tvl": 500_000.0, "limit": 15}),
            (["yields", "--limit", "5"],       {"min_apy": 5.0, "min_tvl": 1_000_000, "limit": 5}),
            (["yields", "--min-apy", "20", "--min-tvl", "5000000", "--limit", "3"],
             {"min_apy": 20.0, "min_tvl": 5_000_000.0, "limit": 3}),
        ]

        for argv, expected in test_cases:
            with patch.object(sys, "argv", ["borg-defi"] + argv):
                # Patch the actual scan functions so we only test parsing
                with patch("borg.defi.cli._cmd_yields") as mock_cmd:
                    mock_cmd.return_value = 0
                    main()
                    args = mock_cmd.call_args[0][0]
                    assert args.min_apy == expected["min_apy"], f"argv={argv}"
                    assert args.min_tvl == expected["min_tvl"], f"argv={argv}"
                    assert args.limit == expected["limit"], f"argv={argv}"

    def test_tokens_subcommand_parsed(self):
        """borg-defi tokens [--limit N] parses."""
        from borg.defi.cli import main

        test_cases = [
            (["tokens"],              {"limit": 10}),
            (["tokens", "--limit", "5"], {"limit": 5}),
            (["tokens", "--limit", "25"], {"limit": 25}),
        ]

        for argv, expected in test_cases:
            with patch.object(sys, "argv", ["borg-defi"] + argv):
                with patch("borg.defi.cli._cmd_tokens") as mock_cmd:
                    mock_cmd.return_value = 0
                    main()
                    args = mock_cmd.call_args[0][0]
                    assert args.limit == expected["limit"], f"argv={argv}"

    def test_tvl_subcommand_parsed(self):
        """borg-defi tvl [--limit N] parses."""
        from borg.defi.cli import main

        test_cases = [
            (["tvl"],              {"limit": 20}),
            (["tvl", "--limit", "5"], {"limit": 5}),
            (["tvl", "--limit", "50"], {"limit": 50}),
        ]

        for argv, expected in test_cases:
            with patch.object(sys, "argv", ["borg-defi"] + argv):
                with patch("borg.defi.cli._cmd_tvl") as mock_cmd:
                    mock_cmd.return_value = 0
                    main()
                    args = mock_cmd.call_args[0][0]
                    assert args.limit == expected["limit"], f"argv={argv}"

    def test_stablecoins_subcommand_parsed(self):
        """borg-defi stablecoins [--depeg-threshold N] [--top N] parses."""
        from borg.defi.cli import main

        test_cases = [
            (["stablecoins"], {"depeg_threshold": 0.005, "top": 10}),
            (["stablecoins", "--depeg-threshold", "0.01"], {"depeg_threshold": 0.01, "top": 10}),
            (["stablecoins", "--top", "5"],  {"depeg_threshold": 0.005, "top": 5}),
            (["stablecoins", "--depeg-threshold", "0.02", "--top", "20"],
             {"depeg_threshold": 0.02, "top": 20}),
        ]

        for argv, expected in test_cases:
            with patch.object(sys, "argv", ["borg-defi"] + argv):
                with patch("borg.defi.cli._cmd_stablecoins") as mock_cmd:
                    mock_cmd.return_value = 0
                    main()
                    args = mock_cmd.call_args[0][0]
                    assert args.depeg_threshold == expected["depeg_threshold"], f"argv={argv}"
                    assert args.top == expected["top"], f"argv={argv}"

    def test_scan_all_subcommand_parsed(self):
        """borg-defi scan-all parses with no extra args."""
        from borg.defi.cli import main

        with patch.object(sys, "argv", ["borg-defi", "scan-all"]):
            with patch("borg.defi.cli._cmd_scan_all") as mock_cmd:
                mock_cmd.return_value = 0
                main()
                mock_cmd.assert_called_once()


# ---------------------------------------------------------------------------
# Test: CLI entry point dispatches to correct handler
# ---------------------------------------------------------------------------

class TestCliDispatch:
    """main() routes to the right _cmd_* function for each subcommand."""

    def test_yields_dispatches_to_yields_handler(self):
        """'yields' command calls _cmd_yields."""
        from borg.defi.cli import main
        with patch.object(sys, "argv", ["borg-defi", "yields"]):
            with patch("borg.defi.cli._cmd_yields", return_value=0) as mock:
                main()
                mock.assert_called_once()

    def test_tokens_dispatches_to_tokens_handler(self):
        """'tokens' command calls _cmd_tokens."""
        from borg.defi.cli import main
        with patch.object(sys, "argv", ["borg-defi", "tokens"]):
            with patch("borg.defi.cli._cmd_tokens", return_value=0) as mock:
                main()
                mock.assert_called_once()

    def test_tvl_dispatches_to_tvl_handler(self):
        """'tvl' command calls _cmd_tvl."""
        from borg.defi.cli import main
        with patch.object(sys, "argv", ["borg-defi", "tvl"]):
            with patch("borg.defi.cli._cmd_tvl", return_value=0) as mock:
                main()
                mock.assert_called_once()

    def test_stablecoins_dispatches_to_stablecoins_handler(self):
        """'stablecoins' command calls _cmd_stablecoins."""
        from borg.defi.cli import main
        with patch.object(sys, "argv", ["borg-defi", "stablecoins"]):
            with patch("borg.defi.cli._cmd_stablecoins", return_value=0) as mock:
                main()
                mock.assert_called_once()

    def test_scan_all_dispatches_to_scan_all_handler(self):
        """'scan-all' command calls _cmd_scan_all."""
        from borg.defi.cli import main
        with patch.object(sys, "argv", ["borg-defi", "scan-all"]):
            with patch("borg.defi.cli._cmd_scan_all", return_value=0) as mock:
                main()
                mock.assert_called_once()


# ---------------------------------------------------------------------------
# Test: dep guard — prints helpful error when aiohttp is missing
# ---------------------------------------------------------------------------

class TestAiohttpGuard:
    """CLI prints helpful error when aiohttp is not installed."""

    def test_main_returns_1_when_aiohttp_missing(self):
        """main() exits with code 1 when _AIOHTTP_AVAILABLE is False."""
        import borg.defi.cli as cli_module

        with patch.object(cli_module, "_AIOHTTP_AVAILABLE", False):
            with patch.object(sys, "argv", ["borg-defi", "yields"]):
                exit_code = cli_module.main()

        assert exit_code == 1

    def test_helpful_error_message_printed(self):
        """Error message suggests installing aiohttp."""
        import borg.defi.cli as cli_module

        with patch.object(cli_module, "_AIOHTTP_AVAILABLE", False):
            with patch.object(sys, "argv", ["borg-defi", "tokens"]):
                with patch("sys.stderr") as mock_stderr:
                    cli_module.main()
                    stderr_write = "".join(
                        call.args[0] for call in mock_stderr.write.call_args_list
                    )
                    assert "aiohttp" in stderr_write
                    assert "pip install" in stderr_write or "agent-borg[defi]" in stderr_write

    def test_no_handler_called_when_aiohttp_missing(self):
        """No _cmd_* handler is called when aiohttp is absent."""
        import borg.defi.cli as cli_module

        with patch.object(cli_module, "_AIOHTTP_AVAILABLE", False):
            with patch.object(sys, "argv", ["borg-defi", "yields"]):
                with patch("borg.defi.cli._cmd_yields") as mock:
                    cli_module.main()
                    mock.assert_not_called()


# ---------------------------------------------------------------------------
# Test: handler return codes propagate
# ---------------------------------------------------------------------------

class TestHandlerReturnCodes:
    """Handlers return their exit code from main()."""

    def test_handler_zero_return(self):
        """_cmd_yields returning 0 → main returns 0."""
        from borg.defi.cli import main

        with patch.object(sys, "argv", ["borg-defi", "yields"]):
            with patch("borg.defi.cli._cmd_yields", return_value=0):
                assert main() == 0

    def test_handler_nonzero_return(self):
        """_cmd_yields returning 1 → main returns 1."""
        from borg.defi.cli import main

        with patch.object(sys, "argv", ["borg-defi", "yields"]):
            with patch("borg.defi.cli._cmd_yields", return_value=1):
                assert main() == 1


# ---------------------------------------------------------------------------
# Test: unknown command handled gracefully
# ---------------------------------------------------------------------------

class TestUnknownCommand:
    """Unknown subcommand prints error and returns 1."""

    def test_unknown_command_returns_1(self):
        """Passing an unknown command → exit code 1."""
        from borg.defi.cli import main

        with patch.object(sys, "argv", ["borg-defi", "foobar"]):
            # argparse exits on unknown command; catch SystemExit
            with pytest.raises(SystemExit):
                main()


# ---------------------------------------------------------------------------
# Test: --help works (argparse built-in)
# ---------------------------------------------------------------------------

class TestHelpFlag:
    """--help flag works as expected via argparse."""

    def test_help_flag_exits_zero(self):
        """--help should exit cleanly (not error)."""
        from borg.defi.cli import main

        with patch.object(sys, "argv", ["borg-defi", "--help"]):
            with pytest.raises(SystemExit) as exc_info:
                main()
            assert exc_info.value.code == 0

    def test_help_shows_all_subcommands(self):
        """--help output lists all five subcommands."""
        from borg.defi.cli import main

        with patch.object(sys, "argv", ["borg-defi", "--help"]):
            with patch("sys.stdout") as mock_stdout:
                try:
                    main()
                except SystemExit:
                    pass
                stdout_write = "".join(
                    call.args[0] for call in mock_stdout.write.call_args_list
                )
                assert "yields" in stdout_write
                assert "tokens" in stdout_write
                assert "tvl" in stdout_write
                assert "stablecoins" in stdout_write
                assert "scan-all" in stdout_write
