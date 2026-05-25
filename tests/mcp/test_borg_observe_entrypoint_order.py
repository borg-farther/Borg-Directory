from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]


def test_borg_observe_wrapper_is_defined_before_module_entrypoint_main_call() -> None:
    source = (ROOT / "borg" / "integrations" / "mcp_server.py").read_text(encoding="utf-8")
    wrapper_index = source.index("# Short-form wrapper")
    main_index = source.index('if __name__ == "__main__":')

    assert wrapper_index < main_index, (
        "python -m borg.integrations.mcp_server must define the fail-closed "
        "borg_observe wrapper before main() starts serving stdio requests"
    )
