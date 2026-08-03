"""Adobe UMAPI tools — user listing, product profile listing, license assign/remove.

Tool naming convention: adobe_<action>_<resource>
"""

import json
import uuid
from collections.abc import Callable

from mcp.server.fastmcp import FastMCP

from ..api_client import AdobeClient, AdobeError

_NO_CREDENTIALS = (
    "Error: No Adobe credentials configured. Set ADOBE_CLIENT_ID/ADOBE_CLIENT_SECRET/ADOBE_ORG_ID "
    "or use AUTH_MODE=gateway."
)


def register(mcp: FastMCP, client_factory: Callable[[], AdobeClient | None]) -> None:
    @mcp.tool()
    async def adobe_list_users(page: int = 0) -> str:
        """List users in the Adobe organization.

        Rate limit: 25 requests/min per client, 100/min globally.

        Args:
            page: Page number to fetch, zero-indexed (default: 0). Check the
                response's "lastPage" field to know whether to fetch the next page.
        """
        client = client_factory()
        if client is None:
            return _NO_CREDENTIALS
        try:
            result = await client.get(f"/users/{client.org_id}/{page}")
            return json.dumps(result, indent=2)
        except AdobeError as e:
            return f"Error: {e}"

    @mcp.tool()
    async def adobe_get_user(email: str) -> str:
        """Get a single user's details, including current group/product profile memberships.

        Rate limit: 25 requests/min per client, 100/min globally.

        Args:
            email: The user's email address (or Adobe username string).
        """
        client = client_factory()
        if client is None:
            return _NO_CREDENTIALS
        try:
            result = await client.get(f"/organizations/{client.org_id}/users/{email}")
            return json.dumps(result, indent=2)
        except AdobeError as e:
            return f"Error: {e}"

    @mcp.tool()
    async def adobe_list_product_profiles(page: int = 0) -> str:
        """List product profiles available for license assignment (e.g. Acrobat Pro/Standard).

        Adobe's API returns all groups (user groups and product profiles together);
        this tool filters the response down to entries where type == "PRODUCT_PROFILE",
        since Adobe has no dedicated "list product profiles only" endpoint.

        Rate limit: 5 requests/min per client, 100/min globally.

        Args:
            page: Page number to fetch, zero-indexed (default: 0).
        """
        client = client_factory()
        if client is None:
            return _NO_CREDENTIALS
        try:
            result = await client.get(f"/groups/{client.org_id}/{page}")
            groups = result.get("groups", []) if isinstance(result, dict) else []
            profiles = [g for g in groups if g.get("type") == "PRODUCT_PROFILE"]
            return json.dumps({**result, "groups": profiles}, indent=2)
        except AdobeError as e:
            return f"Error: {e}"

    @mcp.tool()
    async def adobe_assign_license(email: str, product_profile: str) -> str:
        """Assign a license by adding a user to a product profile (e.g. an Acrobat Pro profile).

        Rate limit: 10 requests/min per client, 100/min globally.

        Args:
            email: The user's email address to grant the license to.
            product_profile: The exact product profile name (see adobe_list_product_profiles).
        """
        client = client_factory()
        if client is None:
            return _NO_CREDENTIALS
        body = [
            {
                "user": email,
                "requestID": f"assign_{uuid.uuid4().hex[:12]}",
                "do": [{"add": {"group": [product_profile]}}],
            }
        ]
        try:
            result = await client.post(f"/action/{client.org_id}", body)
            return json.dumps(result, indent=2)
        except AdobeError as e:
            return f"Error: {e}"

    @mcp.tool()
    async def adobe_remove_license(email: str, product_profile: str) -> str:
        """Revoke a license by removing a user from a product profile.

        Rate limit: 10 requests/min per client, 100/min globally.

        Args:
            email: The user's email address to revoke the license from.
            product_profile: The exact product profile name (see adobe_list_product_profiles).
        """
        client = client_factory()
        if client is None:
            return _NO_CREDENTIALS
        body = [
            {
                "user": email,
                "requestID": f"remove_{uuid.uuid4().hex[:12]}",
                "do": [{"remove": {"group": [product_profile]}}],
            }
        ]
        try:
            result = await client.post(f"/action/{client.org_id}", body)
            return json.dumps(result, indent=2)
        except AdobeError as e:
            return f"Error: {e}"
