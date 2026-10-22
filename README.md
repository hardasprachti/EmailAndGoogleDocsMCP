# Google Workspace MCP Server

A **generic MCP (Model Context Protocol) server** that gives any AI agent the ability to:

- 📧 **Send emails** via Gmail
- 📄 **Append text** to existing Google Docs

Works with Claude Desktop, Cursor, Antigravity, ChatGPT (via MCP bridge), Gemini, and any other MCP-compatible agent.

---

## Project Structure

```
.
├── server.py          # MCP server entrypoint (run this)
├── auth.py            # One-time OAuth2 consent helper
├── google_auth.py     # Shared credential management (auto-refresh)
├── gmail_tool.py      # send_email implementation
├── gdocs_tool.py      # append_to_doc implementation
├── requirements.txt   # Python dependencies
├── credentials.json   # ← You provide this (from Google Cloud Console)
├── token.json         # ← Auto-generated after running auth.py
└── docs/
    ├── prd.md
    └── problemStatement.md
```

---

## Prerequisites

- Python 3.10 or newer
- A Google Cloud project with:
  - **Gmail API** enabled
  - **Google Docs API** enabled
  - An **OAuth 2.0 Desktop** credential (`credentials.json`)

---

## Setup

### 1. Clone / open the project

```bash
cd "MCP for Sending email and Google doc"
```

### 2. Install dependencies

```bash
pip install -r requirements.txt
```

### 3. Get Google credentials

1. Go to [Google Cloud Console](https://console.cloud.google.com/)
2. Create a project (or use an existing one)
3. Enable **Gmail API** and **Google Docs API**
4. Go to **APIs & Services → Credentials**
5. Create **OAuth 2.0 Client ID** → Application type: **Desktop app**
6. Download the JSON and save it as `credentials.json` in the project root

### 4. Run the one-time OAuth consent

```bash
python auth.py
```

This opens your browser for Google's consent screen. After approval, `token.json` is saved automatically. You only need to do this once.

---

## Running the MCP Server

```bash
python server.py
```

The server communicates over **stdio** (JSON-RPC 2.0). Connect your agent to it using the MCP configuration below.

---

## Agent Configuration

### Claude Desktop (`~/Library/Application Support/Claude/claude_desktop_config.json`)

```json
{
  "mcpServers": {
    "google-workspace": {
      "command": "python",
      "args": ["path/to/server.py"]
    }
  }
}
```

### Cursor / Antigravity (`.cursor/mcp.json` or `.agents/mcp_config.json`)

```json
{
  "mcpServers": {
    "google-workspace": {
      "command": "python",
      "args": ["d:/NextLeap Projects/MCP for Sending email and Google doc/server.py"]
    }
  }
}
```

---

## Available Tools

### `send_email`

Send an email from your Gmail account.

| Parameter | Type | Required | Description |
|-----------|------|----------|-------------|
| `to` | string \| string[] | ✅ | Recipient address(es) |
| `subject` | string | ✅ | Email subject |
| `body` | string | ✅ | Email body |
| `cc` | string \| string[] | ❌ | CC recipients |
| `bcc` | string \| string[] | ❌ | BCC recipients |
| `is_html` | boolean | ❌ | Send body as HTML (default: false) |

**Example agent prompt:**
> "Send an email to alice@example.com with subject 'Meeting Notes' and body 'Here are the notes from today's call...'"

---

### `append_to_doc`

Append text to the end of an existing Google Doc.

| Parameter | Type | Required | Description |
|-----------|------|----------|-------------|
| `document_id` | string | ✅ | Doc ID from URL |
| `text` | string | ✅ | Text to append |
| `add_newline` | boolean | ❌ | Prepend a newline (default: true) |

**Finding the Document ID:** In a Google Doc URL like  
`https://docs.google.com/document/d/1BxiMVs0XRA5nFMdKvBdBZjgmUUqptlbs74OgVE2upms/edit`  
the Document ID is `1BxiMVs0XRA5nFMdKvBdBZjgmUUqptlbs74OgVE2upms`.

**Example agent prompt:**
> "Append 'Action items: 1. Review PR 2. Deploy to staging' to the Google Doc with ID 1BxiMVs0XRA5..."

---

## Security Notes

- `credentials.json` and `token.json` contain sensitive OAuth data. **Never commit them to version control.**
- Add them to `.gitignore` (already included).
- Tokens are auto-refreshed — you only need to run `auth.py` once.

---

## Troubleshooting

| Problem | Solution |
|---------|----------|
| `credentials.json not found` | Download OAuth credentials from Google Cloud Console |
| `token.json not found` | Run `python auth.py` |
| `Token expired / invalid` | Delete `token.json` and re-run `python auth.py` |
| `HttpError 403` | Ensure the Gmail API and Google Docs API are enabled in your project |
| `HttpError 404` on doc | Check the document ID and that your account has edit access |
