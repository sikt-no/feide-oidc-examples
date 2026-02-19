"""Configuration loading.

We intentionally use environment variables only. In production deployments,
these should be supplied by your runtime (Kubernetes secrets, vault, etc.).
"""

from __future__ import annotations

from dataclasses import dataclass
from os import getenv


@dataclass(frozen=True)
class Settings:
    issuer: str
    client_id: str
    client_secret: str
    redirect_uri: str
    app_secret_key: str
    extended_userinfo_url: str
    token_exchange_audience: str | None
    token_exchange_scope: str | None
    post_logout_redirect_uri: str | None
    datasource_api_url: str | None


def load_settings() -> Settings:
    issuer = getenv("FEIDE_ISSUER", "https://auth.dataporten.no")
    client_id = getenv("OIDC_CLIENT_ID", "")
    client_secret = getenv("OIDC_CLIENT_SECRET", "")
    redirect_uri = getenv("OIDC_REDIRECT_URI", "")
    app_secret_key = getenv("APP_SECRET_KEY", "")

    extended_userinfo_url = getenv(
        "FEIDE_EXTENDED_USERINFO_URL", "https://api.dataporten.no/userinfo/v1/userinfo"
    )

    token_exchange_audience = getenv("FEIDE_TOKEN_EXCHANGE_AUDIENCE") or None
    token_exchange_scope = getenv("FEIDE_TOKEN_EXCHANGE_SCOPE") or None
    post_logout_redirect_uri = getenv("POST_LOGOUT_REDIRECT_URI") or None
    datasource_api_url = getenv("DATASOURCE_API_URL") or None

    # Fail early with clear errors. These are required to run the sample.
    missing: list[str] = []
    if not client_id:
        missing.append("OIDC_CLIENT_ID")
    if not client_secret:
        missing.append("OIDC_CLIENT_SECRET")
    if not redirect_uri:
        missing.append("OIDC_REDIRECT_URI")
    if not app_secret_key:
        missing.append("APP_SECRET_KEY")

    if missing:
        joined = ", ".join(missing)
        raise RuntimeError(f"Missing required environment variables: {joined}")

    return Settings(
        issuer=issuer,
        client_id=client_id,
        client_secret=client_secret,
        redirect_uri=redirect_uri,
        app_secret_key=app_secret_key,
        extended_userinfo_url=extended_userinfo_url,
        token_exchange_audience=token_exchange_audience,
        token_exchange_scope=token_exchange_scope,
        post_logout_redirect_uri=post_logout_redirect_uri,
        datasource_api_url=datasource_api_url,
    )
