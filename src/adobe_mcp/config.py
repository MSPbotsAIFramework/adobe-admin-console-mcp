from typing import Literal

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore",
    )

    # Transport
    mcp_transport: Literal["stdio", "http"] = "stdio"
    mcp_http_port: int = 8080
    mcp_http_host: str = "0.0.0.0"

    # Auth mode:
    # "gateway" — production/SOP-compliant: three credentials from HTTP headers per
    #             request (no global state, no cached access_token).
    # "env"     — local dev only: shared credential set from env vars.
    auth_mode: Literal["env", "gateway"] = "gateway"

    # Adobe UMAPI credentials (only required in env mode)
    adobe_client_id: str | None = None
    adobe_client_secret: str | None = None
    adobe_org_id: str | None = None
    adobe_base_url: str = "https://usermanagement.adobe.io/v2/usermanagement"

    # Header names used to pass credentials in gateway mode.
    # The client must include all three headers on every /mcp request.
    adobe_client_id_header: str = "x-adobe-client-id"
    adobe_client_secret_header: str = "x-adobe-client-secret"
    adobe_org_id_header: str = "x-adobe-org-id"

    @property
    def has_credentials(self) -> bool:
        """Returns True if the server can serve API calls.

        Gateway mode always returns True — each request carries its own credentials.
        Env mode requires all three ADOBE_* variables to be set.
        """
        if self.auth_mode == "gateway":
            return True
        return bool(self.adobe_client_id and self.adobe_client_secret and self.adobe_org_id)


def get_settings() -> Settings:
    return Settings()
