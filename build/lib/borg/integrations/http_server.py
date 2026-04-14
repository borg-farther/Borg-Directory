"""
Borg HTTP MCP Server — enables concurrent agent access.
Wraps the same handle_request() as the stdio server.

Usage: python -m borg.integrations.http_server --port 3001
Or via CLI: borg-http
"""
from __future__ import annotations

import argparse
import json
import logging
import sys
from typing import Any, Dict

logger = logging.getLogger(__name__)


def create_app():
    """Create FastAPI app wrapping Borg MCP."""
    try:
        from fastapi import FastAPI, Request, HTTPException
        from fastapi.responses import JSONResponse
    except ImportError:
        raise RuntimeError("FastAPI required: pip install agent-borg[http]")

    from borg.integrations.mcp_server import handle_request
    from borg.core.cold_start import run_if_needed

    app = FastAPI(
        title="Borg MCP HTTP Server",
        description="Collective memory for AI coding agents",
        version="1.0.0"
    )

    # Cold start on app creation
    try:
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
                status_code=400
            )

        response = handle_request(body)
        if response is None:
            return JSONResponse({}, status_code=204)
        return JSONResponse(response)

    @app.get("/health")
    async def health() -> Dict[str, Any]:
        """Health check endpoint."""
        import sqlite3
        import os
        from borg.core.traces import TRACE_DB_PATH

        trace_count = 0
        try:
            if os.path.exists(TRACE_DB_PATH):
                db = sqlite3.connect(TRACE_DB_PATH)
                trace_count = db.execute("SELECT COUNT(*) FROM traces").fetchone()[0]
                db.close()
        except Exception:
            pass

        from borg.core.seeds import get_seed_packs
        pack_count = len(get_seed_packs())

        return {
            "status": "ok",
            "trace_count": trace_count,
            "pack_count": pack_count,
            "version": "1.0.0"
        }

    @app.get("/")
    async def root():
        return {"message": "Borg MCP HTTP Server", "docs": "/docs", "mcp": "/mcp", "health": "/health"}

    return app


def main():
    parser = argparse.ArgumentParser(description="Borg HTTP MCP Server")
    parser.add_argument("--port", type=int, default=3001)
    parser.add_argument("--host", default="0.0.0.0")
    parser.add_argument("--reload", action="store_true")
    args = parser.parse_args()

    try:
        import uvicorn
    except ImportError:
        print("ERROR: uvicorn required. Run: pip install agent-borg[http]", file=sys.stderr)
        sys.exit(1)

    print(f"Borg HTTP MCP Server starting on http://{args.host}:{args.port}", file=sys.stderr)
    print(f"MCP endpoint: http://{args.host}:{args.port}/mcp", file=sys.stderr)
    print(f"Health check: http://{args.host}:{args.port}/health", file=sys.stderr)

    app = create_app()
    uvicorn.run(app, host=args.host, port=args.port, reload=args.reload)


if __name__ == "__main__":
    main()
