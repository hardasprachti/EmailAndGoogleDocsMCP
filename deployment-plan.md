# Deployment Plan — Google Workspace MCP Server

Goal: run the MCP server (`send_email`, `append_to_doc`) as a hosted service that remote MCP clients can reach over HTTPS, instead of a local stdio process.

**Recommendation: deploy on Railway.** Vercel is possible but a poor fit (see [Platform comparison](#platform-comparison)).

---

## 1. Why the current code can't be deployed as-is

| Gap | Today | Needed for hosting |
|-----|-------|--------------------|
| Transport | `server.py` uses `stdio_server()` — only works when a client spawns it as a subprocess | An HTTP transport (Streamable HTTP, optionally SSE) bound to `$PORT` |
| Credentials | `google_auth.py` reads `token.json` from disk | Token supplied via environment variables (hosted filesystems are ephemeral and `token.json` is git-ignored) |
| Access control | None — anyone who can reach the process can send mail as you | Auth on the HTTP endpoint (bearer token) |
| Process | Run manually with `python server.py` | Start command + health check + pinned Python version |

The installed `mcp` version (1.30.0) already ships `StreamableHTTPSessionManager`, and `uvicorn`/`starlette` are installed, so no new framework is required.

---

## 2. Code changes (do these before deploying)

### 2.1 Add an HTTP entrypoint — new file `server_http.py`

Keep `server.py` (stdio) untouched so local use and `.agents/mcp_config.json` keep working. The new file imports the existing `app` and serves it over Streamable HTTP:

- Create `StreamableHTTPSessionManager(app=app, stateless=True)` — stateless mode avoids sticky-session problems if Railway ever runs more than one replica.
- Mount it at `/mcp` in a Starlette app; run the manager's `run()` in the app lifespan.
- Add `GET /health` returning `200 {"status":"ok"}` for the platform health check.
- Add a small ASGI middleware that rejects any `/mcp` request without `Authorization: Bearer <MCP_AUTH_TOKEN>` (constant-time compare via `secrets.compare_digest`). Leave `/health` open.
- Start with `uvicorn.run(app, host="0.0.0.0", port=int(os.environ["PORT"]))`.

### 2.2 Load credentials from env — edit `google_auth.py`

Order of precedence in `get_credentials()`:

1. `GOOGLE_TOKEN_JSON` env var (the full contents of `token.json`) → `Credentials.from_authorized_user_info(json.loads(...), SCOPES)`
2. Fallback: `token.json` on disk (current behaviour, for local dev)

On refresh, only write back to disk if the file source was used; in hosted mode the refreshed access token lives in memory (the refresh token in the env var stays valid and is re-exchanged after each restart).

### 2.3 Dependencies — `requirements.txt`

Add `uvicorn>=0.30` and `starlette>=0.37` explicitly (they are only transitive today). Keep `mcp>=1.0.0,<2`.

### 2.4 Tests before shipping

- Locally: `python server_http.py`, then connect with a small client using `mcp.client.streamable_http.streamablehttp_client("http://localhost:8000/mcp", headers={"Authorization": "Bearer …"})`; confirm `list_tools` returns both tools.
- Confirm a request with a missing/wrong bearer token gets `401`.
- Confirm `GOOGLE_TOKEN_JSON` works with `token.json` temporarily moved aside.

---

## 3. Secrets and configuration

| Variable | Value | Notes |
|----------|-------|-------|
| `GOOGLE_TOKEN_JSON` | Contents of local `token.json` (single line) | Contains the refresh token — treat as a password |
| `MCP_AUTH_TOKEN` | Long random string (`python -c "import secrets; print(secrets.token_urlsafe(32))"`) | Clients send it as `Authorization: Bearer …` |
| `PORT` | Set automatically by Railway | Do not hard-code |

`GOOGLE_CLIENT_ID` / `GOOGLE_CLIENT_SECRET` are already embedded in `token.json`, so they are not needed at runtime. Do **not** commit `.env`, `token.json`, or `credentials.json` (already in `.gitignore`).

### OAuth consent screen — check before going live

The token was minted through a Google Cloud OAuth client. If the consent screen is in **Testing** status, Google expires refresh tokens after **7 days**, and the hosted server will start failing with `invalid_grant`. Fix: in Google Cloud Console → OAuth consent screen, either publish the app to **Production** (the `gmail.send` scope is sensitive, so unverified-app warnings apply, but a personal-use app with your own account works) or plan to re-run `get_auth_url.py` weekly and update `GOOGLE_TOKEN_JSON`.

---

## 4. Deploy on Railway (recommended)

1. **Prepare the repo**
   - Add `runtime.txt`/`.python-version` pinning Python 3.13 (matches local `__pycache__`).
   - Add a `Procfile` (or set the start command in Railway): `web: python server_http.py`
   - Push the project to a private GitHub repo (confirm `.env` and `token.json` are not tracked: `git ls-files | grep -E "token|\.env|credentials"` should print nothing apart from `.env.example`).
2. **Create the service** — Railway dashboard → New Project → Deploy from GitHub repo. Nixpacks auto-detects Python from `requirements.txt`.
3. **Set variables** — Service → Variables: add `GOOGLE_TOKEN_JSON` and `MCP_AUTH_TOKEN`.
4. **Networking** — Service → Settings → Networking → Generate Domain. Set the health check path to `/health`.
5. **Deploy and verify**
   - `curl https://<app>.up.railway.app/health` → `{"status":"ok"}`
   - `curl -i https://<app>.up.railway.app/mcp` without a token → `401`
   - Run the test client from §2.4 against the public URL; call `append_to_doc` on the test doc and `send_email` to the test address.
6. **Connect an agent** — remote MCP config, e.g.:
   ```json
   {
     "mcpServers": {
       "google-workspace": {
         "url": "https://<app>.up.railway.app/mcp",
         "headers": { "Authorization": "Bearer <MCP_AUTH_TOKEN>" }
       }
     }
   }
   ```
   (Clients that only support stdio can bridge with `npx mcp-remote <url> --header "Authorization: Bearer …"`.)

Cost/footprint: a single small instance is enough; the server is idle between calls. Railway's Hobby plan is sufficient.

---

## 5. Deploy on Vercel (possible, not recommended)

Vercel runs Python as serverless functions, which conflicts with this server in a few ways:

- Needs an ASGI function entry at `api/index.py` plus `vercel.json` rewrites routing `/mcp` and `/health` to it.
- Only **stateless** Streamable HTTP works (no long-lived SSE; function duration limits apply). Our `stateless=True` setting from §2.1 already covers this, but legacy SSE-only clients will not work.
- Cold starts add latency to the first call, and the MCP session lifespan must be started per invocation.
- Env vars are set via `vercel env add GOOGLE_TOKEN_JSON` / `MCP_AUTH_TOKEN`, then `vercel --prod`.

Choose Vercel only if you already host everything else there; otherwise Railway is simpler and more reliable for this workload.

---

## Platform comparison

| | Railway | Vercel |
|---|---|---|
| Execution model | Long-running container | Serverless functions |
| Streamable HTTP | ✅ | ✅ stateless only |
| SSE / long connections | ✅ | ❌ limited by function duration |
| Cold starts | None (always on) | Yes |
| Code changes beyond §2 | None | `api/index.py` + `vercel.json` |
| Fit for this project | **Best** | Workable with caveats |

---

## 6. Security checklist

- [ ] `MCP_AUTH_TOKEN` enforced on `/mcp`; unauthenticated requests return 401
- [ ] No secrets in git history (`token.json`, `.env`, `credentials.json`)
- [ ] Logging never prints tokens — note `server.py` currently logs full tool arguments (`Tool called: … | args: …`), which includes email bodies; reduce to tool name only before hosting
- [ ] Consider an allow-list of recipient domains in `send_email` — a leaked bearer token otherwise lets a caller send arbitrary mail as your Gmail account
- [ ] Rotate `MCP_AUTH_TOKEN` and revoke the Google token (myaccount.google.com → Security → Third-party access) if anything leaks

---

## 7. Rollout order

1. Implement §2 changes and test locally (stateless HTTP, bearer auth, env-var credentials).
2. Move OAuth consent screen out of Testing (or accept weekly token refresh).
3. Deploy to Railway; verify with §4 step 5.
4. Point one agent at the remote URL and run an end-to-end email + doc append.
5. Only then, if needed, add the Vercel variant.

## 8. Rollback

Railway keeps previous deployments: Service → Deployments → pick the last good one → Redeploy. Local stdio use via `server.py` is unaffected by any of this, so it remains a fallback.
