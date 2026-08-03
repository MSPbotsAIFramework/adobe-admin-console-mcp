import contextvars
import sys
from collections.abc import Callable
from dataclasses import dataclass

from mcp.server.fastmcp import FastMCP
from mcp.server.transport_security import TransportSecuritySettings
from starlette.requests import Request
from starlette.responses import JSONResponse
from starlette.types import ASGIApp, Receive, Scope, Send

from .api_client import AdobeClient
from .config import Settings


@dataclass(frozen=True)
class AdobeCredentials:
    client_id: str
    client_secret: str
    org_id: str


# ─────────────────────────────────────────────────────────────────────────────
# Per-request credentials contextvar for gateway mode.
# GatewayCredentialsMiddleware sets this before the MCP handler runs.
# Python asyncio copies context per task, so concurrent requests are isolated.
# ─────────────────────────────────────────────────────────────────────────────
_gateway_credentials_var: contextvars.ContextVar[AdobeCredentials | None] = (
    contextvars.ContextVar("adobe_gateway_credentials", default=None)
)


def get_client_from_context(settings: Settings) -> AdobeClient | None:
    """Resolve the active AdobeClient for the current request context."""
    if settings.auth_mode == "gateway":
        creds = _gateway_credentials_var.get()
        if creds is None:
            return None
        return AdobeClient(creds.client_id, creds.client_secret, creds.org_id, settings.adobe_base_url)

    if not settings.has_credentials:
        return None
    return AdobeClient(
        settings.adobe_client_id,
        settings.adobe_client_secret,
        settings.adobe_org_id,
        settings.adobe_base_url,
    )


class GatewayCredentialsMiddleware:
    """ASGI middleware for gateway mode.

    Reads the three Adobe credential headers from each request and stores them
    in the contextvar for the duration of that request. Returns 401 if any of
    the three headers is missing on /mcp requests.
    """

    def __init__(self, app: ASGIApp, settings: Settings):
        self.app = app
        self.settings = settings

    async def __call__(self, scope: Scope, receive: Receive, send: Send) -> None:
        if scope["type"] != "http":
            await self.app(scope, receive, send)
            return

        path = scope.get("path", "")
        if not path.startswith("/mcp"):
            await self.app(scope, receive, send)
            return

        request = Request(scope)
        # Header lookup is case-insensitive in Starlette
        client_id = request.headers.get(self.settings.adobe_client_id_header.lower())
        client_secret = request.headers.get(self.settings.adobe_client_secret_header.lower())
        org_id = request.headers.get(self.settings.adobe_org_id_header.lower())

        required_headers = [
            self.settings.adobe_client_id_header,
            self.settings.adobe_client_secret_header,
            self.settings.adobe_org_id_header,
        ]

        if not client_id or not client_secret or not org_id:
            response = JSONResponse(
                {
                    "error": "Missing credentials",
                    "message": f"Gateway mode requires all of: {', '.join(required_headers)}",
                    "required_headers": required_headers,
                },
                status_code=401,
            )
            await response(scope, receive, send)
            return

        ctx_token = _gateway_credentials_var.set(
            AdobeCredentials(client_id=client_id, client_secret=client_secret, org_id=org_id)
        )
        try:
            await self.app(scope, receive, send)
        finally:
            _gateway_credentials_var.reset(ctx_token)


def create_mcp_server(settings: Settings) -> FastMCP:
    """Build the FastMCP server instance and register all tools."""
    # DNS-rebinding protection is disabled because the container runs behind
    # mcp-gateway on an internal Docker network and is never publicly exposed.
    mcp = FastMCP(
        name="adobe-admin-console-mcp",
        transport_security=TransportSecuritySettings(enable_dns_rebinding_protection=False),
    )

    client_factory: Callable[[], AdobeClient | None] = lambda: get_client_from_context(settings)

    if not settings.has_credentials:
        # Graceful degradation: register only a diagnostic tool when no credentials are available.
        @mcp.tool()
        async def adobe_test_connection() -> str:
            """Test Adobe UMAPI connection. Shows configuration requirements when credentials are missing."""
            return (
                "Error: Missing Adobe credentials.\n\n"
                "Set the required environment variables:\n"
                "  ADOBE_CLIENT_ID=...\n"
                "  ADOBE_CLIENT_SECRET=...\n"
                "  ADOBE_ORG_ID=...\n\n"
                "Or use gateway mode (per-request credentials):\n"
                "  AUTH_MODE=gateway\n"
                f"  Send headers: {settings.adobe_client_id_header}, "
                f"{settings.adobe_client_secret_header}, {settings.adobe_org_id_header}"
            )

        print(
            "Warning: No Adobe credentials found. Only the diagnostic tool is available.",
            file=sys.stderr,
        )
        return mcp

    from .tools import licenses

    licenses.register(mcp, client_factory)

    return mcp
