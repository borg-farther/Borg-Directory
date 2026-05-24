from __future__ import annotations

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
