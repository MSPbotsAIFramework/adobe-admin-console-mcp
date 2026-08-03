from typing import Any

import httpx

DEFAULT_BASE_URL = "https://usermanagement.adobe.io/v2/usermanagement"

# Adobe IMS token endpoint for OAuth Server-to-Server (replaces deprecated JWT auth).
# https://developer.adobe.com/developer-console/docs/guides/authentication/ServerToServerAuthentication/ims
IMS_TOKEN_URL = "https://ims-na1.adobelogin.com/ims/token/v3"
IMS_SCOPE = "openid,AdobeID,user_management_sdk"


class AdobeError(Exception):
    def __init__(self, status_code: int, message: str):
        self.status_code = status_code
        super().__init__(f"Adobe API error {status_code}: {message}")


class AdobeClient:
    """Async httpx client wrapping Adobe's User Management API (UMAPI).

    Per request, exchanges client_id/client_secret for a short-lived IMS
    access_token (~24h TTL) and uses it immediately — the token is never cached
    or reused across requests, in line with the "no persisted credentials"
    requirement. Adobe's own docs recommend caching the token for its full
    lifetime; that tradeoff is intentionally not taken here.
    """

    def __init__(
        self,
        client_id: str,
        client_secret: str,
        org_id: str,
        base_url: str = DEFAULT_BASE_URL,
    ):
        self._client_id = client_id
        self._client_secret = client_secret
        self.org_id = org_id
        self._base_url = base_url.rstrip("/")

    async def _fetch_access_token(self) -> str:
        async with httpx.AsyncClient() as client:
            resp = await client.post(
                IMS_TOKEN_URL,
                data={
                    "grant_type": "client_credentials",
                    "client_id": self._client_id,
                    "client_secret": self._client_secret,
                    "scope": IMS_SCOPE,
                },
            )
            if resp.status_code >= 400:
                try:
                    detail = resp.json()
                except Exception:
                    detail = resp.text
                raise AdobeError(resp.status_code, f"IMS token exchange failed: {detail}")
            return resp.json()["access_token"]

    async def _headers(self) -> dict[str, str]:
        token = await self._fetch_access_token()
        return {
            "Authorization": f"Bearer {token}",
            "x-api-key": self._client_id,
            "Content-Type": "application/json",
        }

    def _clean_params(self, params: dict | None) -> dict:
        if not params:
            return {}
        return {k: v for k, v in params.items() if v is not None}

    async def get(self, path: str, params: dict | None = None) -> Any:
        headers = await self._headers()
        async with httpx.AsyncClient() as client:
            resp = await client.get(
                f"{self._base_url}{path}",
                headers=headers,
                params=self._clean_params(params),
            )
            self._raise_for_status(resp)
            return resp.json() if resp.status_code != 204 else None

    async def post(self, path: str, body: Any = None) -> Any:
        headers = await self._headers()
        async with httpx.AsyncClient() as client:
            resp = await client.post(
                f"{self._base_url}{path}",
                headers=headers,
                json=body,
            )
            self._raise_for_status(resp)
            return resp.json() if resp.status_code != 204 else None

    def _raise_for_status(self, resp: httpx.Response) -> None:
        if resp.status_code >= 400:
            try:
                detail = resp.json()
            except Exception:
                detail = resp.text
            raise AdobeError(resp.status_code, str(detail))
