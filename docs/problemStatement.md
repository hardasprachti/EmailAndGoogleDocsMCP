# Problem Statement: Generic MCP Server for Gmail & Google Docs

## Overview

Build a **Model Context Protocol (MCP) server** that exposes Gmail and Google Docs capabilities as tools, allowing any AI agent (ChatGPT, Claude, Gemini, Cursor, Antigravity, etc.) to send emails via Gmail and append content to existing Google Docs—without requiring agent-specific integrations.

---

## Background

### What is MCP?
The [Model Context Protocol](https://modelcontextprotocol.io/) is an open standard that defines how AI agents communicate with external tools and data sources. An MCP server exposes "tools" (callable functions) over a standard JSON-RPC 2.0 transport (stdio or HTTP+SSE). Any MCP-compatible agent can connect and invoke these tools without custom integration code.

### Problem
AI agents frequently need to:
- **Send emails** as part of automation workflows (notifications, summaries, reports)
- **Append/update documents** collaboratively, especially Google Docs used by teams

Today, each agent platform requires bespoke API integrations. Developers must re-implement Gmail/Google Docs auth and logic for every agent. There is no reusable, protocol-standard solution.

---

## Goals

1. **Gmail Tool** — Allow agents to compose and send emails via the Gmail API using OAuth 2.0.
2. **Google Docs Tool** — Allow agents to append text (plain or formatted) to an existing Google Doc using the Google Docs API.
3. **Generic / Interoperable** — Conform fully to the MCP specification so any MCP-compatible agent can connect.
4. **Secure by Design** — Use OAuth 2.0 with offline refresh tokens; never expose secrets in tool responses.
5. **Minimal Setup** — Single configuration step; runnable with one command.

---

## Functional Requirements

### FR-1: MCP Server Lifecycle
- Implement MCP initialization handshake.
- Expose `tools/list` with JSON Schema input definitions.
- Handle `tools/call` and return structured results.
- Transport: **stdio** (primary).

### FR-2: Gmail — `send_email` Tool
| Field | Description |
|-------|-------------|
| `to` | Recipient email address(es) |
| `subject` | Email subject line |
| `body` | Email body content |
| `cc` (optional) | CC recipients |
| `bcc` (optional) | BCC recipients |
| `is_html` (optional) | If true, send as HTML |

### FR-3: Google Docs — `append_to_doc` Tool
| Field | Description |
|-------|-------------|
| `document_id` | The Google Doc ID (from URL) |
| `text` | Text content to append |
| `add_newline` (optional) | Prepend a newline (default: true) |

### FR-4: Authentication
- OAuth 2.0 with offline access (refresh token).
- Credentials stored in `credentials.json`.
- Token cached in `token.json` (auto-refreshed).

---

## Non-Functional Requirements

| Requirement | Target |
|-------------|--------|
| Language | Python 3.10+ |
| MCP SDK | `mcp` (official Python SDK) |
| Transport | stdio |
| Error handling | Structured MCP error responses |
| Logging | Stderr only |

---

## Architecture

```
AI Agent (Claude / ChatGPT / Gemini / Cursor / Antigravity)
        │  MCP JSON-RPC over stdio
        ▼
┌──────────────────────────────────────────┐
│            MCP Server (Python)           │
│  ┌─────────────┐   ┌──────────────────┐  │
│  │  send_email │   │  append_to_doc   │  │
│  └──────┬──────┘   └────────┬─────────┘  │
│         │   Google Auth Layer            │
└─────────┼──────────────────┼────────────┘
    Gmail API          Google Docs API
```

---

## Success Criteria

- An AI agent can call `send_email` and email is delivered.
- An AI agent can call `append_to_doc` and text appears at end of the Google Doc.
- Works with any MCP-compatible agent without modification.
- Token refresh happens automatically.
- All errors returned as structured MCP error responses.
