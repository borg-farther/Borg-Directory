from __future__ import annotations

import json

from fastapi.testclient import TestClient

from borg.integrations.http_server import READ_ONLY_UNAUTH_TOOLS, create_app


def _jsonrpc(method: str, *, request_id: int = 1, params: dict | None = None) -> dict:
    return {"jsonrpc": "2.0", "id": request_id, "method": method, "params": params or {}}


def test_http_mcp_requires_bearer_token_when_configured(tmp_path, monkeypatch) -> None:
    monkeypatch.setenv("HOME", str(tmp_path / "home"))
    monkeypatch.setenv("BORG_HOME", str(tmp_path / "borg-home"))
    monkeypatch.setenv("BORG_DIR", str(tmp_path / "borg-home"))
    client = TestClient(create_app(token="secret-token", allow_unauth_readonly=False))
    payload = _jsonrpc("tools/list")

    assert client.post("/mcp", json=payload).status_code == 401
    assert client.post("/mcp", json=payload, headers={"Authorization": "Bearer wrong"}).status_code == 401

    ok = client.post("/mcp", json=payload, headers={"Authorization": "Bearer secret-token"})
    assert ok.status_code == 200
    tool_names = {tool["name"] for tool in ok.json()["result"]["tools"]}
    assert "borg_pull" in tool_names
    assert "borg_publish" in tool_names


def test_http_mcp_auth_checked_before_json_parse(tmp_path, monkeypatch) -> None:
    monkeypatch.setenv("HOME", str(tmp_path / "home"))
    monkeypatch.setenv("BORG_HOME", str(tmp_path / "borg-home"))
    monkeypatch.setenv("BORG_DIR", str(tmp_path / "borg-home"))
    client = TestClient(create_app(token="secret-token", allow_unauth_readonly=False))

    no_auth = client.post("/mcp", content=b"{not json", headers={"content-type": "application/json"})
    wrong_auth = client.post(
        "/mcp",
        content=b"{not json",
        headers={"content-type": "application/json", "Authorization": "Bearer wrong"},
    )

    assert no_auth.status_code == 401
    assert wrong_auth.status_code == 401


def test_http_mcp_rejects_oversized_body_before_dispatch(tmp_path, monkeypatch) -> None:
    monkeypatch.setenv("HOME", str(tmp_path / "home"))
    monkeypatch.setenv("BORG_HOME", str(tmp_path / "borg-home"))
    monkeypatch.setenv("BORG_DIR", str(tmp_path / "borg-home"))
    client = TestClient(create_app(token="secret-token", allow_unauth_readonly=False))
    oversized = json.dumps(_jsonrpc("tools/list", params={"blob": "x" * (1024 * 1024 + 1)}))

    response = client.post(
        "/mcp",
        content=oversized.encode("utf-8"),
        headers={"content-type": "application/json", "Authorization": "Bearer secret-token"},
    )

    assert response.status_code == 413


def test_http_mcp_unauthenticated_mode_is_read_only(tmp_path, monkeypatch) -> None:
    monkeypatch.setenv("HOME", str(tmp_path / "home"))
    monkeypatch.setenv("BORG_HOME", str(tmp_path / "borg-home"))
    monkeypatch.setenv("BORG_DIR", str(tmp_path / "borg-home"))
    client = TestClient(create_app(token="", allow_unauth_readonly=True))

    tools_resp = client.post("/mcp", json=_jsonrpc("tools/list"))
    assert tools_resp.status_code == 200
    tool_names = {tool["name"] for tool in tools_resp.json()["result"]["tools"]}
    assert tool_names == READ_ONLY_UNAUTH_TOOLS
    assert "borg_pull" not in tool_names
    assert "borg_publish" not in tool_names
    assert "borg_record_failure" not in tool_names
    assert "borg_rescue" not in tool_names
    assert "error_lookup" not in tool_names
    assert "borg_observe" not in tool_names

    blocked = client.post(
        "/mcp",
        json=_jsonrpc(
            "tools/call",
            params={"name": "borg_pull", "arguments": {"uri": "https://example.com/pack.yaml"}},
        ),
    )
    assert blocked.status_code == 200
    body = blocked.json()
    assert body["error"]["code"] == -32001
    assert "requires BORG_HTTP_TOKEN" in body["error"]["message"]


def test_http_mcp_can_be_disabled_without_token(tmp_path, monkeypatch) -> None:
    monkeypatch.setenv("HOME", str(tmp_path / "home"))
    monkeypatch.setenv("BORG_HOME", str(tmp_path / "borg-home"))
    monkeypatch.setenv("BORG_DIR", str(tmp_path / "borg-home"))
    client = TestClient(create_app(token="", allow_unauth_readonly=False))

    response = client.post("/mcp", json=_jsonrpc("tools/list"))

    assert response.status_code == 503
    assert "BORG_HTTP_TOKEN" in response.json()["detail"]


def test_create_app_defaults_to_disabled_without_token(tmp_path, monkeypatch) -> None:
    monkeypatch.setenv("HOME", str(tmp_path / "home"))
    monkeypatch.setenv("BORG_HOME", str(tmp_path / "borg-home"))
    monkeypatch.setenv("BORG_DIR", str(tmp_path / "borg-home"))
    client = TestClient(create_app(token=""))

    response = client.post("/mcp", json=_jsonrpc("tools/list"))

    assert response.status_code == 503


def test_http_mcp_rejects_malformed_jsonrpc_shapes_without_500(tmp_path, monkeypatch) -> None:
    monkeypatch.setenv("HOME", str(tmp_path / "home"))
    monkeypatch.setenv("BORG_HOME", str(tmp_path / "borg-home"))
    monkeypatch.setenv("BORG_DIR", str(tmp_path / "borg-home"))
    client = TestClient(create_app(token="secret-token", allow_unauth_readonly=False))
    headers = {"Authorization": "Bearer secret-token"}
    malformed_payloads = [
        [],
        [ _jsonrpc("tools/list") ],
        "x",
        1,
        {},
        {"jsonrpc": "2.0", "method": 1, "id": 1},
        {"jsonrpc": "2.0", "method": "tools/call", "params": [], "id": 1},
        {"jsonrpc": "2.0", "method": "tools/call", "params": {"name": 123}, "id": 1},
        {"jsonrpc": "2.0", "method": "tools/call", "params": {"name": "borg_search", "arguments": []}, "id": 1},
    ]

    for payload in malformed_payloads:
        response = client.post("/mcp", json=payload, headers=headers)
        assert response.status_code == 400
        body = response.json()
        assert body["error"]["code"] in {-32600, -32602}
