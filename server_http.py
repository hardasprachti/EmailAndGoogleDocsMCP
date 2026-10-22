"""
server_http.py — Hosted (Streamable HTTP) entrypoint for the Google Workspace MCP server.

Reuses the MCP `app` from server.py (stdio entrypoint is unchanged).

Environment:
  MCP_AUTH_TOKEN     required — clients must send  Authorization: Bearer <token>
  GOOGLE_TOKEN_JSON  contents of token.json (falls back to token.json on disk)
  PORT               listen port (default 8000)

Endpoints:
  POST /mcp          MCP Streamable HTTP (bearer-protected)
  GET  /health       liveness check (open)

Usage:
  python server_http.py
"""

import contextlib
import logging
import os
import secrets

import uvicorn
from mcp.server.streamable_http_manager import StreamableHTTPSessionManager
from starlette.applications import Starlette
from starlette.responses import JSONResponse
from starlette.routing import Route

from server import app as mcp_app

logger = logging.getLogger("mcp_google_server.http")

# Stateless: every request is self-contained, so replicas / restarts are safe.
session_manager = StreamableHTTPSessionManager(app=mcp_app, stateless=True)


class BearerAuthMiddleware:
    """Pure-ASGI middleware: reject /mcp requests without the correct bearer token."""

    def __init__(self, app, token: str):
        self.app = app
        self.token = token.encode()

    async def __call__(self, scope, receive, send):
        if scope["type"] == "http" and scope["path"].startswith("/mcp"):
            headers = dict(scope["headers"])
            supplied = headers.get(b"authorization", b"")
            expected_prefix = b"Bearer "
            ok = supplied.startswith(expected_prefix) and secrets.compare_digest(
                supplied[len(expected_prefix):], self.token
            )
            if not ok:
                response = JSONResponse(
                    {"error": "unauthorized"},
                    status_code=401,
                    headers={"WWW-Authenticate": "Bearer"},
                )
                await response(scope, receive, send)
                return
        await self.app(scope, receive, send)


async def health(_request):
    return JSONResponse({"status": "ok"})


class McpEndpoint:
    """ASGI app handing the request to the MCP session manager (Starlette treats
    non-function callables as raw ASGI apps, so no redirect or request wrapping)."""

    async def __call__(self, scope, receive, send):
        await session_manager.handle_request(scope, receive, send)


@contextlib.asynccontextmanager
async def lifespan(_app):
    async with session_manager.run():
        logger.info("Streamable HTTP session manager started.")
        yield


def build_app() -> Starlette:
    token = os.environ.get("MCP_AUTH_TOKEN", "")
    if not token:
        raise RuntimeError("MCP_AUTH_TOKEN is not set; refusing to start an unauthenticated server.")

    starlette_app = Starlette(
        routes=[
            Route("/health", health, methods=["GET"]),
            Route("/mcp", McpEndpoint()),
        ],
        lifespan=lifespan,
    )
    return BearerAuthMiddleware(starlette_app, token)


if __name__ == "__main__":
    uvicorn.run(
        build_app(),
        host="0.0.0.0",
        port=int(os.environ.get("PORT", "8000")),
        log_level="info",
    )
