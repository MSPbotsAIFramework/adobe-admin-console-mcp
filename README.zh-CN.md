# adobe-admin-console-mcp

[English](./README.md) | 中文

面向 Claude 的 Adobe Admin Console MCP 服务——将 Adobe **User Management API (UMAPI)** 封装为 MCP
工具，聚焦 Enterprise 组织下的 **Acrobat / PDF 许可证（Product Profile）分配**场景。

**技术栈：** Python 3.12 + uv + FastMCP（Starlette/uvicorn）

关联需求：[PRD-15546](https://app.clickup.com/t/86e2jyjc9)（Onboarding step 16，Acrobat / PDF license assignment）。完整调研见 `vendor-mcp-template/prd/AdobeAdminConsole.md`。

## 快速开始

```bash
cd adobe-admin-console-mcp
uv sync

# stdio 模式（供 Claude Desktop / CLI 使用），单一共享凭据从环境变量读取
ADOBE_CLIENT_ID=xxxx ADOBE_CLIENT_SECRET=xxxx ADOBE_ORG_ID=xxxx@AdobeOrg uv run adobe-mcp
```

## 认证

本服务**无状态**：不保存、不持久化任何 Adobe 凭据。凭据要么通过环境变量一次性配置（本地调试，
`AUTH_MODE=env`），要么按请求通过 HTTP Header 传入（生产环境，`AUTH_MODE=gateway`）。

Adobe 使用 **OAuth Server-to-Server**（JWT / Service Account 认证已弃用）。每次工具调用，本服务都会用
调用方传入的 `client_id` + `client_secret` 换取一个短期 Adobe IMS `access_token`（有效期约 24 小时）并
立即使用——**不做跨请求缓存**，尽管 Adobe 官方文档建议缓存复用，但为了完全遵循"不持久化凭据"的
硬性要求，本服务选择了这个取舍。代价是每次调用会多一次 IMS 往返请求。

### Gateway 模式 HTTP Header（`AUTH_MODE=gateway`）

| Header | 类型 | 是否必填 | 默认值 | 枚举值 | 字段描述 | Example |
|---|---|---|---|---|---|---|
| `x-adobe-client-id` | string | 必填 | 无 | 无 | Adobe Developer Console Project 的 Client ID，用于换取 access_token 及作为 `x-api-key` | `1234abcd5678efgh` |
| `x-adobe-client-secret` | string | 必填 | 无 | 无 | 对应的 Client Secret，仅用于本次请求内换取 access_token，不持久化、不写日志 | `p8e-xxxxxxxxxxxx` |
| `x-adobe-org-id` | string | 必填 | 无 | 无 | Adobe 组织 ID（Enterprise 租户标识） | `1234567890ABCDEF@AdobeOrg` |

`/mcp` 请求缺少上述任一 Header，都会返回 `401`，并在 `required_headers` 字段中列出三个必填 Header。

### Env 模式变量（`AUTH_MODE=env`，仅限本地调试）

| 变量 | 默认值 | 说明 |
|---|---|---|
| `ADOBE_CLIENT_ID` | — | Adobe Developer Console Project 的 Client ID |
| `ADOBE_CLIENT_SECRET` | — | Adobe Developer Console Project 的 Client Secret |
| `ADOBE_ORG_ID` | — | Adobe 组织 ID，例如 `1234567890ABCDEF@AdobeOrg` |
| `ADOBE_BASE_URL` | `https://usermanagement.adobe.io/v2/usermanagement` | UMAPI Base URL |
| `AUTH_MODE` | `gateway` | `env` 或 `gateway` |
| `MCP_TRANSPORT` | `stdio` | `stdio` 或 `http` |
| `MCP_HTTP_PORT` | `8080` | HTTP 服务端口 |
| `MCP_HTTP_HOST` | `0.0.0.0` | HTTP 服务监听地址 |

获取凭据：在 [Adobe Developer Console](https://developer.adobe.com/console) 中创建一个启用了
**User Management API** 的 Project（仅 Enterprise 类型组织可用——Teams / 教育版 / 个人版 Adobe ID
无法启用此 API）。

## Claude Desktop 配置

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

## 传输模式

### stdio（Claude Desktop / CLI）
```bash
ADOBE_CLIENT_ID=xxxx ADOBE_CLIENT_SECRET=xxxx ADOBE_ORG_ID=xxxx@AdobeOrg uv run adobe-mcp
```

### HTTP —— 单租户（env 模式）
```bash
ADOBE_CLIENT_ID=xxxx ADOBE_CLIENT_SECRET=xxxx ADOBE_ORG_ID=xxxx@AdobeOrg \
MCP_TRANSPORT=http AUTH_MODE=env uv run adobe-mcp
curl http://localhost:8080/health
```

### HTTP —— gateway / 多租户（生产环境）
```bash
MCP_TRANSPORT=http AUTH_MODE=gateway uv run adobe-mcp
```

## Tool List

Base URL：`https://usermanagement.adobe.io/v2/usermanagement`

| Tool | 说明 | 参数 |
|---|---|---|
| `adobe_list_users` | 列出组织下的用户（分页） | `page`（int，可选，默认 0，从 0 开始） |
| `adobe_get_user` | 获取指定用户详情（含当前产品/群组归属） | `email`（string，必填） |
| `adobe_list_product_profiles` | 列出可分配的产品档案（如 Acrobat Pro / Standard），客户端按 `type == "PRODUCT_PROFILE"` 过滤 | `page`（int，可选，默认 0） |
| `adobe_assign_license` | 将用户加入指定 Product Profile，完成许可证分配 | `email`（string，必填）、`product_profile`（string，必填，产品档案名称） |
| `adobe_remove_license` | 将用户从指定 Product Profile 移除，回收许可证 | `email`（string，必填）、`product_profile`（string，必填） |

**限流**（由 Adobe 侧强制执行，非本服务限制——超限会收到 `429` + `Retry-After`）：

| Endpoint 类别 | Per-client | 全局 |
|---|---|---|
| 列出用户 / 获取单个用户 | 25 次/分钟 | 100 次/分钟 |
| 列出群组 / 产品档案 | 5 次/分钟 | 100 次/分钟 |
| 分配 / 回收许可证（action） | 10 次/分钟 | 100 次/分钟 |

## 测试示例

### tools/list（gateway 模式）
```bash
curl -X POST http://localhost:8080/mcp \
  -H "x-adobe-client-id: your_client_id" \
  -H "x-adobe-client-secret: your_client_secret" \
  -H "x-adobe-org-id: 1234567890ABCDEF@AdobeOrg" \
  -H "Content-Type: application/json" \
  -H "Accept: application/json, text/event-stream" \
  -d '{"jsonrpc":"2.0","method":"tools/list","id":1}'
```

### tools/call —— 分配一个 Acrobat 许可证
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

### 缺 Header → 401
```bash
curl -i -X POST http://localhost:8080/mcp \
  -H "Content-Type: application/json" \
  -H "Accept: application/json, text/event-stream" \
  -d '{"jsonrpc":"2.0","method":"tools/list","id":1}'
# HTTP/1.1 401 Unauthorized
# {"error":"Missing credentials","required_headers":["x-adobe-client-id","x-adobe-client-secret","x-adobe-org-id"]}
```

## API 参考

- [UMAPI 官方文档](https://adobe-apiplatform.github.io/umapi-documentation/en/)
- [OAuth Server-to-Server 认证](https://developer.adobe.com/developer-console/docs/guides/authentication/ServerToServerAuthentication/)
- [Adobe Developer Console](https://developer.adobe.com/console)

## 已知限制

- **没有专门的"列出产品档案"接口**——`adobe_list_product_profiles` 调用的是通用的群组接口，再
  由客户端过滤。
- **UMAPI 没有官方沙箱**——必须使用一个真实的、至少配置了一个产品档案的 Enterprise 组织才能测试
  （Teams / 教育版 / 个人账号都无法启用此 API）。
- 每次工具调用都会重新做一次 token 交换（不缓存），会增加一点延迟，但换来完全符合 SOP 的无状态
  要求。
