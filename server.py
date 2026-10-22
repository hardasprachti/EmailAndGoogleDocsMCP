"""
server.py — Generic MCP server exposing Gmail and Google Docs tools.

Transports:
  • stdio (default)  — works with Claude Desktop, Cursor, Antigravity, etc.

Usage:
  python server.py
"""

import logging
import sys
from typing import Any

import mcp.types as types
from mcp.server import Server
from mcp.server.stdio import stdio_server

from gmail_tool import send_email
from gdocs_tool import append_to_doc

# ── Logging ──────────────────────────────────────────────────────────────────
# MCP uses stdout for JSON-RPC, so log only to stderr.
logging.basicConfig(
    stream=sys.stderr,
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
)
logger = logging.getLogger("mcp_google_server")

# ── Server setup ──────────────────────────────────────────────────────────────
app = Server("google-workspace-mcp")

# ── Tool definitions ──────────────────────────────────────────────────────────

SEND_EMAIL_SCHEMA = {
    "type": "object",
    "properties": {
        "to": {
            "oneOf": [
                {"type": "string", "format": "email"},
                {"type": "array", "items": {"type": "string", "format": "email"}},
            ],
            "description": "Recipient email address or list of addresses.",
        },
        "subject": {
            "type": "string",
            "description": "Email subject line.",
        },
        "body": {
            "type": "string",
            "description": "Email body (plain text or HTML).",
        },
        "cc": {
            "oneOf": [
                {"type": "string"},
                {"type": "array", "items": {"type": "string"}},
            ],
            "description": "Optional CC recipient(s).",
        },
        "bcc": {
            "oneOf": [
                {"type": "string"},
                {"type": "array", "items": {"type": "string"}},
            ],
            "description": "Optional BCC recipient(s).",
        },
        "is_html": {
            "type": "boolean",
            "description": "Set to true to send body as HTML. Default: false.",
            "default": False,
        },
    },
    "required": ["to", "subject", "body"],
    "additionalProperties": False,
}

APPEND_TO_DOC_SCHEMA = {
    "type": "object",
    "properties": {
        "document_id": {
            "type": "string",
            "description": (
                "The Google Doc ID. Find it in the URL: "
                "https://docs.google.com/document/d/<DOCUMENT_ID>/edit"
            ),
        },
        "text": {
            "type": "string",
            "description": "The text content to append to the end of the document.",
        },
        "add_newline": {
            "type": "boolean",
            "description": "Prepend a newline before the appended text. Default: true.",
            "default": True,
        },
    },
    "required": ["document_id", "text"],
    "additionalProperties": False,
}


# ── Handlers ──────────────────────────────────────────────────────────────────

@app.list_tools()
async def list_tools() -> list[types.Tool]:
    """Return all available tools to the MCP client."""
    return [
        types.Tool(
            name="send_email",
            description=(
                "Send an email via Gmail. "
                "Supports plain text and HTML bodies, CC, and BCC recipients."
            ),
            inputSchema=SEND_EMAIL_SCHEMA,
        ),
        types.Tool(
            name="append_to_doc",
            description=(
                "Append text to the end of an existing Google Doc. "
                "Provide the document ID (from the doc's URL) and the text to add."
            ),
            inputSchema=APPEND_TO_DOC_SCHEMA,
        ),
    ]


@app.call_tool()
async def call_tool(
    name: str, arguments: dict[str, Any]
) -> list[types.TextContent]:
    """Dispatch a tool call and return the result as MCP TextContent."""
    logger.info("Tool called: %s", name)  # args omitted: may contain email content

    try:
        if name == "send_email":
            result = send_email(
                to=arguments["to"],
                subject=arguments["subject"],
                body=arguments["body"],
                cc=arguments.get("cc"),
                bcc=arguments.get("bcc"),
                is_html=arguments.get("is_html", False),
            )
            text = (
                f"✅ Email sent successfully!\n"
                f"  Message ID : {result['messageId']}\n"
                f"  Thread ID  : {result['threadId']}\n"
            )

        elif name == "append_to_doc":
            result = append_to_doc(
                document_id=arguments["document_id"],
                text=arguments["text"],
                add_newline=arguments.get("add_newline", True),
            )
            text = (
                f"✅ Text appended to Google Doc successfully!\n"
                f"  Document ID  : {result['documentId']}\n"
                f"  Revision ID  : {result['revisionsId']}\n"
            )

        else:
            raise ValueError(f"Unknown tool: '{name}'")

    except Exception as exc:
        logger.error("Tool '%s' failed: %s", name, exc, exc_info=True)
        text = f"❌ Error running '{name}': {exc}"

    return [types.TextContent(type="text", text=text)]


# ── Entry point ───────────────────────────────────────────────────────────────

async def main() -> None:
    logger.info("Starting Google Workspace MCP server (stdio transport)...")
    async with stdio_server() as (read_stream, write_stream):
        await app.run(
            read_stream,
            write_stream,
            app.create_initialization_options(),
        )


if __name__ == "__main__":
    import asyncio
    asyncio.run(main())
