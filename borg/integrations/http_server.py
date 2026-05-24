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
import logging
import os
import secrets
import sys
from typing import Any, Dict, Optional

logger = logging.getLogger(__name__)

READ_ONLY_UNAUTH_TOOLS = frozenset({
    "error_lookup",
    "borg_rescue",
    "borg_observe",
    "borg_search",
    "borg_first_10",
})


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


def create_app(token: Optional[str] = None, allow_unauth_readonly: bool = True):
    """Create FastAPI app wrapping Borg MCP."""
    try:
        from fastapi import FastAPI, Request, HTTPException
        from fastapi.responses import JSONResponse
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
        try:
            body = await request.json()
        except Exception:
            return JSONResponse(
                {"jsonrpc": "2.0", "id": None, "error": {"code": -32700, "message": "Parse error"}},
                status_code=400,
            )

        if token:
            if not _bearer_authorized(request, token):
                raise HTTPException(status_code=401, detail="Missing or invalid bearer token")
            from borg.integrations.mcp_server import handle_request
            response = handle_request(body)
        elif allow_unauth_readonly:
            response = _readonly_http_response(body)
        else:
            raise HTTPException(
                status_code=503,
                detail="HTTP MCP is disabled until BORG_HTTP_TOKEN is set",
            )

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
