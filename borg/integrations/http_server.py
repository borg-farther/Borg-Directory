"""
FastAPI HTTP wrapper for agent-borg MCP server (Smithery.ai compatible).

Implements Streamable HTTP transport for MCP protocol (JSON-RPC 2.0 over HTTP).
Smithery.ai requires this for listing agent-borg as an MCP server.

Endpoints:
  GET  /health           Health check
  GET  /mcp              Server card / well-known MCP info
  GET  /mcp/tools        List all available tools
  POST /mcp              Handle MCP JSON-RPC requests (tools/call, tools/list, ping, etc.)
  GET  /                 Root info endpoint

Streamable HTTP transport uses text/event-stream for streaming responses.
"""

from __future__ import annotations

import json
import logging
import os
import signal
import sys
from contextlib import asynccontextmanager
from typing import Any, AsyncIterator, Dict, List, Optional, Union

from fastapi import FastAPI, HTTPException, Request, Response
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from sse_starlette.sse import EventSourceResponse

# ---------------------------------------------------------------------------
# Logging setup
# ---------------------------------------------------------------------------

logging.basicConfig(stream=sys.stderr, level=logging.INFO)
logger = logging.getLogger("borg.http_server")

# ---------------------------------------------------------------------------
# Import MCP server components (lazy to avoid circular imports)
# ---------------------------------------------------------------------------

TOOL_TIMEOUT_SEC = 30


def _timeout_handler(signum, frame):
    raise TimeoutError(f"Tool call exceeded {TOOL_TIMEOUT_SEC}s timeout")


def _get_mcp_components():
    """Lazily import MCP server components."""
    from borg.integrations.mcp_server import (
        TOOLS,
        SERVER_INFO,
        CAPABILITIES,
        call_tool,
        make_response,
        make_error,
        handle_request,
    )
    return TOOLS, SERVER_INFO, CAPABILITIES, call_tool, make_response, make_error, handle_request


# ---------------------------------------------------------------------------
# FastAPI app lifespan
# ---------------------------------------------------------------------------

@asynccontextmanager
async def lifespan(app: FastAPI):
    """Initialize on startup, cleanup on shutdown."""
    logger.info("agent-borg HTTP server starting...")
    yield
    logger.info("agent-borg HTTP server shutting down...")


# ---------------------------------------------------------------------------
# FastAPI app creation
# ---------------------------------------------------------------------------

app = FastAPI(
    title="agent-borg MCP Server",
    description="Proven workflows for AI agents — execution-proven, safety-scanned, feedback-improving. "
                "This is the HTTP wrapper for the MCP server, compatible with Smithery.ai Streamable HTTP transport.",
    version="2.4.0",
    lifespan=lifespan,
    docs_url="/docs",
    redoc_url="/redoc",
)

# CORS middleware for cross-origin requests (Smithery scans require this)
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _json_rpc_error(code: int, message: str, req_id: Any = None) -> JSONResponse:
    """Build a JSON-RPC 2.0 error response."""
    return JSONResponse(
        content={"jsonrpc": "2.0", "id": req_id, "error": {"code": code, "message": message}},
        status_code=200 if req_id is not None else 204,
    )


async def _stream_json_rpc_response(
    req_id: Any,
    data: Dict[str, Any],
    event_type: str = "message",
) -> AsyncIterator[Dict[str, Any]]:
    """Yield a JSON-RPC response as an SSE event."""
    yield {"event": event_type, "data": json.dumps({"jsonrpc": "2.0", "id": req_id, "result": data})}


async def _stream_json_rpc_error(
    req_id: Any,
    code: int,
    message: str,
) -> AsyncIterator[Dict[str, Any]]:
    """Yield a JSON-RPC error as an SSE event."""
    yield {"event": "message", "data": json.dumps({"jsonrpc": "2.0", "id": req_id, "error": {"code": code, "message": message}})}


# ---------------------------------------------------------------------------
# Health check endpoint
# ---------------------------------------------------------------------------

@app.get("/health", tags=["health"])
async def health_check():
    """
    Health check endpoint for Smithery and load balancers.
    Returns 200 if the server is running.
    """
    return {"status": "healthy", "server": "agent-borg-mcp-server", "version": "2.4.0"}


# ---------------------------------------------------------------------------
# Root info endpoint
# ---------------------------------------------------------------------------

@app.get("/", tags=["info"])
async def root_info():
    """Root endpoint returning server metadata."""
    _, server_info, capabilities, _, _, _, _ = _get_mcp_components()
    return {
        "server": server_info,
        "capabilities": capabilities,
        "description": "agent-borg MCP server — Proven workflows for AI agents",
        "smithery_url": "https://smithery.ai",
    }


# ---------------------------------------------------------------------------
# Server card (static metadata for Smithery)
# ---------------------------------------------------------------------------

@app.get("/.well-known/mcp/server-card.json", tags=["smithery"])
async def server_card():
    """
    Static server card for Smithery discovery.
    Serves as the fallback static listing when auto-scan fails.
    See SMITHERY_LISTING_GUIDE.md Section: Method 3 - Static Server Card.
    """
    from borg.integrations.mcp_server import TOOLS as mcp_tools, SERVER_INFO as mcp_server_info

    return {
        "serverInfo": {
            "name": mcp_server_info["name"],
            "version": mcp_server_info["version"],
        },
        "authentication": {
            "required": False,
            "schemes": [],
        },
        "tools": mcp_tools,
        "resources": [],
        "prompts": [],
    }


# ---------------------------------------------------------------------------
# MCP tools listing (non-streaming)
# ---------------------------------------------------------------------------

@app.get("/mcp/tools", tags=["mcp"])
async def list_tools():
    """
    List all available MCP tools.
    Returns the same data as tools/list in the MCP protocol.
    """
    tools, server_info, capabilities, _, _, _, _ = _get_mcp_components()
    return {
        "tools": tools,
        "server": server_info,
        "capabilities": capabilities,
    }


# ---------------------------------------------------------------------------
# MCP POST endpoint (Streamable HTTP transport)
# ---------------------------------------------------------------------------

@app.post("/mcp", tags=["mcp"])
async def handle_mcp_request(request: Request):
    """
    Main MCP endpoint for JSON-RPC 2.0 requests via Streamable HTTP transport.

    Supports:
      - initialize
      - notifications/initialized
      - tools/list
      - tools/call
      - ping

    Returns streaming text/event-stream for Smithery compatibility.
    """
    # Parse JSON-RPC request
    try:
        body = await request.json()
    except Exception as e:
        return _json_rpc_error(-32700, f"Parse error: {e}", req_id=None)

    method = body.get("method", "")
    req_id = body.get("id")
    params = body.get("params", {})

    # Handle methods that don't need tool execution
    if method == "ping":
        async def ping_gen():
            async for event in _stream_json_rpc_response(req_id, {}):
                yield event
        return EventSourceResponse(ping_gen())

    if method == "initialize":
        _, server_info, capabilities, _, _, _, _ = _get_mcp_components()
        async def init_gen():
            async for event in _stream_json_rpc_response(
                req_id,
                {
                    "protocolVersion": "2024-11-05",
                    "serverInfo": server_info,
                    "capabilities": capabilities,
                },
            ):
                yield event
        return EventSourceResponse(init_gen())

    if method == "notifications/initialized":
        # Notifications don't get responses
        return Response(status_code=204)

    if method == "tools/list":
        tools, _, _, _, _, _, _ = _get_mcp_components()
        async def tools_list_gen():
            async for event in _stream_json_rpc_response(req_id, {"tools": tools}):
                yield event
        return EventSourceResponse(tools_list_gen())

    if method == "tools/call":
        tool_name = params.get("name", "")
        arguments = params.get("arguments", {})

        if not tool_name:
            async def err_gen():
                async for event in _stream_json_rpc_error(req_id, -32602, "Missing tool name"):
                    yield event
            return EventSourceResponse(err_gen())

        # Execute tool with timeout
        import asyncio

        def _execute_tool():
            from borg.integrations.mcp_server import call_tool
            return call_tool(tool_name, arguments)

        try:
            # Run CPU-bound tool in thread pool to avoid blocking
            loop = asyncio.get_event_loop()
            result_text = await loop.run_in_executor(None, _execute_tool)
        except TimeoutError as e:
            async def timeout_gen():
                async for event in _stream_json_rpc_error(req_id, -32000, str(e)):
                    yield event
            return EventSourceResponse(timeout_gen())
        except Exception as e:
            async def err_gen():
                async for event in _stream_json_rpc_error(req_id, -32000, str(e)):
                    yield event
            return EventSourceResponse(err_gen())

        # Parse result
        try:
            parsed = json.loads(result_text)
            is_error = parsed.get("success") is False
            content = [{"type": "text", "text": result_text}]
            async def result_gen():
                async for event in _stream_json_rpc_response(
                    req_id,
                    {"content": content, "isError": is_error},
                ):
                    yield event
            return EventSourceResponse(result_gen())
        except (json.JSONDecodeError, TypeError):
            async def result_gen():
                async for event in _stream_json_rpc_response(
                    req_id,
                    {"content": [{"type": "text", "text": result_text}], "isError": False},
                ):
                    yield event
            return EventSourceResponse(result_gen())

    # Unknown method
    if req_id is not None:
        async def unknown_gen():
            async for event in _stream_json_rpc_error(req_id, -32601, f"Method not found: {method}"):
                yield event
        return EventSourceResponse(unknown_gen())

    return Response(status_code=204)


# ---------------------------------------------------------------------------
# CLI entry point
# ---------------------------------------------------------------------------

def run_server(host: str = "0.0.0.0", port: int = 8080, workers: int = 1):
    """Run the HTTP server with uvicorn."""
    import uvicorn

    uvicorn.run(
        "borg.integrations.http_server:app",
        host=host,
        port=port,
        workers=workers,
        reload=False,
        log_level="info",
    )


def main():
    """CLI entry point: borg-http"""
    import argparse

    parser = argparse.ArgumentParser(description="agent-borg MCP HTTP Server (Smithery compatible)")
    parser.add_argument("--host", default=os.getenv("HOST", "0.0.0.0"), help="Host to bind to")
    parser.add_argument("--port", type=int, default=int(os.getenv("PORT", "8080")), help="Port to bind to")
    parser.add_argument("--workers", type=int, default=1, help="Number of workers")
    args = parser.parse_args()

    run_server(host=args.host, port=args.port, workers=args.workers)


if __name__ == "__main__":
    main()
