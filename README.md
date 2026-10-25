# adobe-admin-console-mcp

Adobe Admin Console MCP server for Claude — exposes Adobe's **User Management API (UMAPI)** as MCP
tools, focused on **Acrobat / PDF license (product profile) assignment** for Enterprise organizations.

**Tech stack:** Python 3.12 + uv + FastMCP (Starlette/uvicorn)

Related requirement: [PRD-15546](https://app.clickup.com/t/86e2jyjc9) (Onboarding step 16, Acrobat / PDF license assignment). See the full research in `vendor-mcp-template/prd/AdobeAdminConsole.md`.

<div align="center">

## MSPbots Connector

**The MCP Gateway built for MSPs: visible, controlled, and your data stays where it belongs.**

[**Get started at connect.mspbots.ai →**](https://connect.mspbots.ai)

</div>

---

MSPbots Connector gives your AI clients one MCP URL to reach your entire MSP stack (RMM, PSA, documentation, security, finance), and gives you control over who can call which tool and a record of everything that was called.

**Hosted service: [connect.mspbots.ai](https://connect.mspbots.ai)** · Free to use.

### Why Connector

![MSPbots Connector](https://stgoss.mspbots.ai/files/mcp/mspbots-mcp.png)

| | |
|---|---|
| **Visible** | Every tool call is logged: who, which vendor, when. Usage dashboard, CSV export, SIEM streaming. |
| **Controlled** | Role-based, per-tool allowlist. Deny by default. |
| **Protected** | Credentials encrypted per record. AI clients never see your vendor passwords or tokens. |
| **MSP-native** | Built for the MSP stack only: RMM, PSA, documentation, security, finance. |

### Quick start

1. **Sign up** at [connect.mspbots.ai](https://connect.mspbots.ai).
2. **Connect your vendors.** Pick from 150+ connectors and authorize each one on the vendor's own page, or bring your own API keys. No extra vendor accounts needed.
3. **Set access.** Create roles and decide which tools each role may call. Nothing is allowed until you allow it.
4. **Add your MCP URL to your AI client.** Copy the URL from your Connector dashboard into Claude, ChatGPT, Cursor, VS Code, Gemini, Codex, or any MCP-capable client.
5. **Ask your AI to do real work**, and watch every call appear in the audit log.

### Features

**Unified gateway**
- One MCP URL for all your AI clients
- 150+ connectors across the MSP stack
- Custom MCP servers supported, free
- Authorization happens on each vendor's own page; the AI never sees passwords or tokens
- Bring your own credentials: use the vendor API keys you already have
- Multiple accounts per app; connect once, reuse across AI clients
- Tool search: finds the right action for the task
- One sign-in; vendor credentials are injected behind the scenes and OAuth tokens refresh automatically

**Visibility**
- Audit log for every tool call (who, which vendor, when)
- Usage dashboard: call volume, top vendors, error rate, per-user activity
- Export audit logs to CSV, or stream to Loki, Graylog, or LogScale (SIEM)
- Optional recording of tool arguments and result summaries (off by default, enabled per organization)

**Control**
- Per-role, per-tool allowlist, deny by default
- owner / admin / member roles
- SCIM provisioning with Entra ID, Okta, JumpCloud, and Google Workspace

**Security**
- Credentials encrypted one record at a time (AES-256-GCM, per-record key)
- AI clients authenticate with OAuth 2.1 + PKCE
- Vendor responses are scanned for prompt-injection patterns and returned as structured data. This is one layer of defense, not a guarantee against every attack.
- Static egress IP for customer firewall and API allowlisting

### Pricing

**Free.**

Links: [connect.mspbots.ai](https://connect.mspbots.ai) · [mspbots.ai](https://mspbots.ai)

---

## Quick Start

```bash
cd adobe-admin-console-mcp
uv sync

# stdio mode (for Claude Desktop / CLI), single shared credential set from env
ADOBE_CLIENT_ID=xxxx ADOBE_CLIENT_SECRET=xxxx ADOBE_ORG_ID=xxxx@AdobeOrg uv run adobe-mcp
```

## Authentication

This service is **stateless**: it never stores or persists Adobe credentials. Credentials are
either supplied once via environment variables (local dev, `AUTH_MODE=env`), or per-request via
HTTP headers (`AUTH_MODE=gateway`, production).

Adobe uses **OAuth Server-to-Server** (JWT/Service Account auth is deprecated). On every tool
call, this service exchanges the caller's `client_id` + `client_secret` for a short-lived Adobe
IMS `access_token` (~24h TTL) and uses it immediately — the token is **not cached** across
requests, even though Adobe's own docs suggest doing so, in order to fully comply with the
"no persisted credentials" requirement. This adds one extra IMS round trip per call.

### Gateway mode HTTP headers (`AUTH_MODE=gateway`)

| Header | Type | Required | Default | Allowed values | Description | Example |
|---|---|---|---|---|---|---|
| `x-adobe-client-id` | string | Yes | None | None | Client ID of the Adobe Developer Console Project, used to exchange for an access_token and as `x-api-key` | `1234abcd5678efgh` |
| `x-adobe-client-secret` | string | Yes | None | None | The corresponding Client Secret, used only within this request to exchange for an access_token; not persisted and not logged | `p8e-xxxxxxxxxxxx` |
| `x-adobe-org-id` | string | Yes | None | None | Adobe organization ID (Enterprise tenant identifier) | `1234567890ABCDEF@AdobeOrg` |

Missing any of the three headers on a `/mcp` request returns `401` with a `required_headers` list.

### Env mode variables (`AUTH_MODE=env`, local dev only)

| Variable | Default | Description |
|---|---|---|
| `ADOBE_CLIENT_ID` | — | Adobe Developer Console Project Client ID |
| `ADOBE_CLIENT_SECRET` | — | Adobe Developer Console Project Client Secret |
| `ADOBE_ORG_ID` | — | Adobe organization ID, e.g. `1234567890ABCDEF@AdobeOrg` |
| `ADOBE_BASE_URL` | `https://usermanagement.adobe.io/v2/usermanagement` | UMAPI base URL |
| `AUTH_MODE` | `gateway` | `env` or `gateway` |
| `MCP_TRANSPORT` | `stdio` | `stdio` or `http` |
| `MCP_HTTP_PORT` | `8080` | HTTP server port |
| `MCP_HTTP_HOST` | `0.0.0.0` | HTTP server bind address |

Get credentials: create a Project with **User Management API** enabled in the
[Adobe Developer Console](https://developer.adobe.com/console) (Enterprise organizations only —
this API is not available for Teams / Education / individual Adobe IDs).

## Claude Desktop Setup

```json
{
  "mcpServers": {
    "adobe-admin-console": {
      "command": "uv",
      "args": ["run", "--directory", "/path/to/adobe-admin-console-mcp", "adobe-mcp"],
      "env": {
        "ADOBE_CLIENT_ID": "xxxx",
        "ADOBE_CLIENT_SECRET": "xxxx",
        "ADOBE_ORG_ID": "xxxx@AdobeOrg"
      }
    }
  }
}
```

## Transport Modes

### stdio (Claude Desktop / CLI)
```bash
ADOBE_CLIENT_ID=xxxx ADOBE_CLIENT_SECRET=xxxx ADOBE_ORG_ID=xxxx@AdobeOrg uv run adobe-mcp
```

### HTTP — single-tenant (env mode)
```bash
ADOBE_CLIENT_ID=xxxx ADOBE_CLIENT_SECRET=xxxx ADOBE_ORG_ID=xxxx@AdobeOrg \
MCP_TRANSPORT=http AUTH_MODE=env uv run adobe-mcp
curl http://localhost:8080/health
```

### HTTP — gateway / multi-tenant (production)
```bash
MCP_TRANSPORT=http AUTH_MODE=gateway uv run adobe-mcp
```

## Tool List

Base URL: `https://usermanagement.adobe.io/v2/usermanagement`

| Tool | Description | Parameters |
|---|---|---|
| `adobe_list_users` | List the users of the organization (paginated) | `page` (int, optional, default 0, starting from 0) |
| `adobe_get_user` | Get details of the specified user (including current product/group membership) | `email` (string, required) |
| `adobe_list_product_profiles` | List assignable product profiles (e.g. Acrobat Pro / Standard); the client filters by `type == "PRODUCT_PROFILE"` | `page` (int, optional, default 0) |
| `adobe_assign_license` | Add the user to the specified Product Profile, completing the license assignment | `email` (string, required), `product_profile` (string, required, product profile name) |
| `adobe_remove_license` | Remove the user from the specified Product Profile, reclaiming the license | `email` (string, required), `product_profile` (string, required) |

**Rate limits** (enforced by Adobe, not this service — expect `429` + `Retry-After` if exceeded):

| Endpoint category | Per-client | Global |
|---|---|---|
| List / get users | 25 req/min | 100 req/min |
| List groups / product profiles | 5 req/min | 100 req/min |
| Assign / remove license (action) | 10 req/min | 100 req/min |

## Test Examples

### tools/list (gateway mode)
```bash
curl -X POST http://localhost:8080/mcp \
  -H "x-adobe-client-id: your_client_id" \
  -H "x-adobe-client-secret: your_client_secret" \
  -H "x-adobe-org-id: 1234567890ABCDEF@AdobeOrg" \
  -H "Content-Type: application/json" \
  -H "Accept: application/json, text/event-stream" \
  -d '{"jsonrpc":"2.0","method":"tools/list","id":1}'
```

### tools/call — assign an Acrobat license
```bash
curl -X POST http://localhost:8080/mcp \
  -H "x-adobe-client-id: your_client_id" \
  -H "x-adobe-client-secret: your_client_secret" \
  -H "x-adobe-org-id: 1234567890ABCDEF@AdobeOrg" \
  -H "Content-Type: application/json" \
  -H "Accept: application/json, text/event-stream" \
  -d '{
    "jsonrpc": "2.0",
    "method": "tools/call",
    "id": 2,
    "params": {
      "name": "adobe_assign_license",
      "arguments": {"email": "user@example.com", "product_profile": "Acrobat Pro DC - Enterprise"}
    }
  }'
```

### Missing headers → 401
```bash
curl -i -X POST http://localhost:8080/mcp \
  -H "Content-Type: application/json" \
  -H "Accept: application/json, text/event-stream" \
  -d '{"jsonrpc":"2.0","method":"tools/list","id":1}'
# HTTP/1.1 401 Unauthorized
# {"error":"Missing credentials","required_headers":["x-adobe-client-id","x-adobe-client-secret","x-adobe-org-id"]}
```

## API Reference

- [UMAPI documentation](https://adobe-apiplatform.github.io/umapi-documentation/en/)
- [OAuth Server-to-Server authentication](https://developer.adobe.com/developer-console/docs/guides/authentication/ServerToServerAuthentication/)
- [Adobe Developer Console](https://developer.adobe.com/console)

## Known Limitations

- **No dedicated "list product profiles" endpoint** — `adobe_list_product_profiles` calls the
  generic groups endpoint and filters client-side.
- **No official Adobe sandbox** for UMAPI — it requires a real Enterprise organization with at
  least one product profile to test against (Teams/Education/individual accounts cannot enable
  this API).
- Token exchange happens on every tool call (no caching), which adds latency but keeps the
  service fully stateless per the SOP requirement.
