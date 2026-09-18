from pathlib import Path

from eval.run_pypi_fresh_install_canary import artifact_module_isolation


REQUIRED_MODULES = {
    "borg",
    "borg.core.confidence_gate",
    "borg.core.runtime_fingerprint",
    "borg.integrations.mcp_server",
}


def _fingerprint(paths: dict[str, Path]) -> dict:
    return {"modules": {name: {"path": str(path)} for name, path in paths.items()}}


def test_artifact_module_isolation_accepts_only_modules_under_fresh_venv(tmp_path):
    borg_mcp = tmp_path / "venv" / "bin" / "borg-mcp"
    site_packages = tmp_path / "venv" / "lib" / "python3.12" / "site-packages"
    paths = {
        name: site_packages / Path(*name.split(".")).with_suffix(".py")
        for name in REQUIRED_MODULES
    }

    result = artifact_module_isolation(_fingerprint(paths), borg_mcp)

    assert result["passed"] is True
    assert result["missing_modules"] == []
    assert result["outside_install_root"] == {}


def test_artifact_module_isolation_rejects_source_checkout_shadowing(tmp_path):
    borg_mcp = tmp_path / "venv" / "bin" / "borg-mcp"
    site_packages = tmp_path / "venv" / "lib" / "python3.12" / "site-packages"
    paths = {
        name: site_packages / Path(*name.split(".")).with_suffix(".py")
        for name in REQUIRED_MODULES
    }
    paths["borg.integrations.mcp_server"] = Path("/workspace/source/borg/integrations/mcp_server.py")

    result = artifact_module_isolation(_fingerprint(paths), borg_mcp)

    assert result["passed"] is False
    assert result["outside_install_root"] == {
        "borg.integrations.mcp_server": "/workspace/source/borg/integrations/mcp_server.py"
    }


def test_artifact_module_isolation_fails_closed_on_missing_fingerprint_module(tmp_path):
    borg_mcp = tmp_path / "venv" / "bin" / "borg-mcp"

    result = artifact_module_isolation({"modules": {}}, borg_mcp)

    assert result["passed"] is False
    assert set(result["missing_modules"]) == REQUIRED_MODULES