"""
Borg HTTP MCP Server — optional HTTP access for Borg MCP.
Wraps the same handle_request() as the stdio server, with a fail-closed remote default.

Usage: python -m borg.integrations.http_server --port 3001
Or via CLI: borg-http

Remote/public HTTP requires a bearer token in BORG_HTTP_TOKEN. Without a token,
only loopback read-only rescue/search tools are exposed.
"""
from __future__ import annotations

import argparse
import json
import logging
import os
import secrets
import sys
from typing import Any, Dict, Optional

logger = logging.getLogger(__name__)

READ_ONLY_UNAUTH_TOOLS = frozenset({
    "borg_search",
    "borg_first_10",
})

BORG_HTTP_MAX_BODY_BYTES = int(os.environ.get("BORG_HTTP_MAX_BODY_BYTES", "1048576"))


def _is_loopback_host(host: str) -> bool:
    return host in {"127.0.0.1", "localhost", "::1"}


def _bearer_authorized(request: Any, token: str) -> bool:
    auth = request.headers.get("authorization", "")
    prefix = "Bearer "
    if not token or not auth.startswith(prefix):
        return False
    return secrets.compare_digest(auth[len(prefix):].strip(), token)


def _readonly_http_response(body: Dict[str, Any]) -> Dict[str, Any] | None:
    from borg.integrations.mcp_server import TOOLS, handle_request, make_error, make_response

    req_id = body.get("id")
    method = body.get("method", "")

    if method == "tools/list":
        safe_tools = [tool for tool in TOOLS if tool.get("name") in READ_ONLY_UNAUTH_TOOLS]
        return make_response(req_id, {"tools": safe_tools})

    if method == "tools/call":
        name = body.get("params", {}).get("name", "")
        if name not in READ_ONLY_UNAUTH_TOOLS:
            return make_error(
                req_id,
                -32001,
                "HTTP MCP requires BORG_HTTP_TOKEN for this tool; unauthenticated HTTP is read-only.",
            )

    return handle_request(body)


def _jsonrpc_error(req_id: Any, code: int, message: str) -> Dict[str, Any]:
    return {"jsonrpc": "2.0", "id": req_id, "error": {"code": code, "message": message}}


def _validate_jsonrpc_request(body: Any) -> Dict[str, Any] | None:
    """Return a JSON-RPC error for unsupported/malformed shapes, else None."""
    if not isinstance(body, dict):
        return _jsonrpc_error(None, -32600, "Invalid Request: top-level JSON value must be an object")
    req_id = body.get("id")
    if body.get("jsonrpc") not in (None, "2.0"):
        return _jsonrpc_error(req_id, -32600, "Invalid Request: jsonrpc must be '2.0'")
    method = body.get("method")
    if not isinstance(method, str) or not method:
        return _jsonrpc_error(req_id, -32600, "Invalid Request: method must be a string")
    params = body.get("params", {})
    if params is None:
        body["params"] = {}
        params = body["params"]
    if not isinstance(params, dict):
        return _jsonrpc_error(req_id, -32602, "Invalid params: params must be an object")
    if method == "tools/call":
        name = params.get("name")
        if not isinstance(name, str) or not name:
            return _jsonrpc_error(req_id, -32602, "Invalid params: tools/call name must be a string")
        arguments = params.get("arguments", {})
        if arguments is None:
            params["arguments"] = {}
        elif not isinstance(arguments, dict):
            return _jsonrpc_error(req_id, -32602, "Invalid params: tools/call arguments must be an object")
    return None


def _content_length_too_large(request: Any, max_body_bytes: int) -> bool:
    raw_value = request.headers.get("content-length")
    if not raw_value:
        return False
    try:
        return int(raw_value) > max_body_bytes
    except ValueError:
        return False


def create_app(token: Optional[str] = None, allow_unauth_readonly: bool = False):
    """Create FastAPI app wrapping Borg MCP."""
    try:
        from fastapi import FastAPI, Request, HTTPException
        from fastapi.responses import JSONResponse
        from starlette.concurrency import run_in_threadpool
    except ImportError:
        raise RuntimeError("FastAPI required: pip install agent-borg[http]")
    # With ``from __future__ import annotations``, FastAPI resolves endpoint
    # annotations from module globals. Request is optional until create_app(), so
    # expose it here before registering routes; otherwise FastAPI treats
    # ``request`` as a required query parameter and returns 422 before auth.
    globals()["Request"] = Request

    from borg import __version__ as borg_version

    token = os.environ.get("BORG_HTTP_TOKEN", "") if token is None else token

    app = FastAPI(
        title="Borg MCP HTTP Server",
        description="Failure memory for AI coding agents",
        version=borg_version,
    )
    app.state.borg_http_token = token
    app.state.borg_http_allow_unauth_readonly = allow_unauth_readonly

    # HTTP MCP must be safe to instantiate in remote/read-only contexts. Do not
    # perform local cold-start writes or optional embedding/model loads unless an
    # operator explicitly opts in.
    if os.environ.get("BORG_HTTP_RUN_COLD_START") == "1":
        try:
            from borg.core.cold_start import run_if_needed

            run_if_needed()
        except Exception:
            pass

    @app.post("/mcp")
    async def mcp_endpoint(request: Request) -> JSONResponse:
        """Handle MCP JSON-RPC requests over HTTP."""
        # Fail closed before reading/parsing attacker-controlled request bodies.
        if token:
            if not _bearer_authorized(request, token):
                raise HTTPException(status_code=401, detail="Missing or invalid bearer token")
        elif not allow_unauth_readonly:
            raise HTTPException(
                status_code=503,
                detail="HTTP MCP is disabled until BORG_HTTP_TOKEN is set",
            )

        if _content_length_too_large(request, BORG_HTTP_MAX_BODY_BYTES):
            return JSONResponse({"detail": "Request body too large"}, status_code=413)

        raw_body = await request.body()
        if len(raw_body) > BORG_HTTP_MAX_BODY_BYTES:
            return JSONResponse({"detail": "Request body too large"}, status_code=413)
        try:
            body = json.loads(raw_body.decode("utf-8"))
        except Exception:
            return JSONResponse(
                {"jsonrpc": "2.0", "id": None, "error": {"code": -32700, "message": "Parse error"}},
                status_code=400,
            )

        validation_error = _validate_jsonrpc_request(body)
        if validation_error is not None:
            status = 400 if validation_error["error"]["code"] in {-32600, -32602} else 200
            return JSONResponse(validation_error, status_code=status)

        if token:
            from borg.integrations.mcp_server import handle_request
            response = await run_in_threadpool(handle_request, body)
        else:
            response = await run_in_threadpool(_readonly_http_response, body)

        if response is None:
            return JSONResponse({}, status_code=204)
        return JSONResponse(response)

    @app.get("/health")
    async def health() -> Dict[str, Any]:
        """Health check endpoint."""
        from borg.core.seeds import get_seed_packs

        pack_count = len(get_seed_packs())

        return {
            "status": "ok",
            "pack_count": pack_count,
            "version": borg_version,
            "mcp_auth": "bearer" if token else "unauthenticated-readonly",
        }

    @app.get("/")
    async def root():
        return {"message": "Borg MCP HTTP Server", "docs": "/docs", "mcp": "/mcp", "health": "/health"}

    return app


def main():
    parser = argparse.ArgumentParser(description="Borg HTTP MCP Server")
    parser.add_argument("--port", type=int, default=3001)
    parser.add_argument("--host", default="127.0.0.1")
    parser.add_argument("--reload", action="store_true")
    parser.add_argument("--token-env", default="BORG_HTTP_TOKEN")
    parser.add_argument(
        "--allow-unauth-readonly",
        action="store_true",
        help="Expose only rescue/search tools without auth. Remote hosts require this explicit flag if no token is set.",
    )
    args = parser.parse_args()

    try:
        import uvicorn
    except ImportError:
        print("ERROR: uvicorn required. Run: pip install agent-borg[http]", file=sys.stderr)
        sys.exit(1)

    token = os.environ.get(args.token_env, "")
    allow_unauth_readonly = args.allow_unauth_readonly or (not token and _is_loopback_host(args.host))
    if not token and not allow_unauth_readonly:
        print(
            f"ERROR: set {args.token_env}=<secret> before binding Borg HTTP MCP to {args.host}, "
            "or pass --allow-unauth-readonly for a deliberately read-only endpoint.",
            file=sys.stderr,
        )
        sys.exit(2)

    print(f"Borg HTTP MCP Server starting on http://{args.host}:{args.port}", file=sys.stderr)
    print(f"MCP endpoint: http://{args.host}:{args.port}/mcp", file=sys.stderr)
    print(f"Health check: http://{args.host}:{args.port}/health", file=sys.stderr)
    print("MCP auth: bearer token" if token else "MCP auth: unauthenticated read-only", file=sys.stderr)

    app = create_app(token=token, allow_unauth_readonly=allow_unauth_readonly)
    uvicorn.run(app, host=args.host, port=args.port, reload=args.reload)


if __name__ == "__main__":
    main()
