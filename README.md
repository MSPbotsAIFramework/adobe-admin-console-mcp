# adobe-admin-console-mcp

English | [中文](./README.zh-CN.md)

Adobe Admin Console MCP server for Claude — exposes Adobe's **User Management API (UMAPI)** as MCP
tools, focused on **Acrobat / PDF license (product profile) assignment** for Enterprise organizations.

**Tech stack:** Python 3.12 + uv + FastMCP (Starlette/uvicorn)

关联需求：[PRD-15546](https://app.clickup.com/t/86e2jyjc9)（Onboarding step 16，Acrobat / PDF license assignment）。完整调研见 `vendor-mcp-template/prd/AdobeAdminConsole.md`。

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

| Header | 类型 | 是否必填 | 默认值 | 枚举值 | 字段描述 | Example |
|---|---|---|---|---|---|---|
| `x-adobe-client-id` | string | 必填 | 无 | 无 | Adobe Developer Console Project 的 Client ID，用于换取 access_token 及作为 `x-api-key` | `1234abcd5678efgh` |
| `x-adobe-client-secret` | string | 必填 | 无 | 无 | 对应的 Client Secret，仅用于本次请求内换取 access_token，不持久化、不写日志 | `p8e-xxxxxxxxxxxx` |
| `x-adobe-org-id` | string | 必填 | 无 | 无 | Adobe 组织 ID（Enterprise 租户标识） | `1234567890ABCDEF@AdobeOrg` |

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
| `adobe_list_users` | 列出组织下的用户（分页） | `page` (int, 可选，默认 0，从 0 开始) |
| `adobe_get_user` | 获取指定用户详情（含当前产品/群组归属） | `email` (string, 必填) |
| `adobe_list_product_profiles` | 列出可分配的产品档案（如 Acrobat Pro / Standard），客户端按 `type == "PRODUCT_PROFILE"` 过滤 | `page` (int, 可选，默认 0) |
| `adobe_assign_license` | 将用户加入指定 Product Profile，完成许可证分配 | `email` (string, 必填), `product_profile` (string, 必填，产品档案名称) |
| `adobe_remove_license` | 将用户从指定 Product Profile 移除，回收许可证 | `email` (string, 必填), `product_profile` (string, 必填) |

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
