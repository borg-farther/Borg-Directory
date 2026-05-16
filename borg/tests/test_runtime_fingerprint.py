import json

from borg.core.runtime_fingerprint import runtime_fingerprint, runtime_fingerprint_json
from borg.integrations import mcp_server


def test_runtime_fingerprint_has_loaded_paths_and_hashes():
    fp = runtime_fingerprint()
    assert fp["success"] is True
    assert fp["tool"] == "borg_runtime_fingerprint"
    assert fp["pid"] > 0
    assert fp["modules"]["borg.integrations.mcp_server"]["path"]
    assert fp["modules"]["borg.integrations.mcp_server"]["sha256"]
    assert fp["modules"]["borg.core.confidence_gate"]["path"]
    assert fp["modules"]["borg.core.confidence_gate"]["sha256"]


def test_runtime_fingerprint_confidence_gate_canary_passes():
    fp = runtime_fingerprint()
    canary = fp["confidence_gate_canary"]
    assert canary["passed"] is True
    assert canary["stale_guidance_stripped"] is True
    assert canary["stale_permission_match"] is False
    assert canary["stale_permission_safe"] is False
    assert canary["synthetic_pack_safe"] is False
    assert canary["real_permission_positive_control_safe"] is True
    assert fp["reload_status"] == "loaded_code_has_confidence_gate"


def test_runtime_fingerprint_json_round_trips():
    parsed = json.loads(runtime_fingerprint_json())
    assert parsed["success"] is True
    assert parsed["schema_version"] == 1


def test_mcp_tool_schema_and_dispatch_include_runtime_fingerprint():
    names = {tool["name"] for tool in mcp_server.TOOLS}
    assert "borg_runtime_fingerprint" in names

    parsed = json.loads(mcp_server.call_tool("borg_runtime_fingerprint", {}))
    assert parsed["success"] is True
    assert parsed["confidence_gate_canary"]["passed"] is True
    assert parsed["modules"]["borg.integrations.mcp_server"]["path"]
