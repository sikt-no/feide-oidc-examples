"""Configuration loading for the data source API example.

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
    datasource_audience: str
    required_scope: str
    token_exchange_audience: str
    token_exchange_scope: str
    extended_userinfo_url: str
    groupinfo_url: str
    http_timeout_s: float = 5.0


def load_settings() -> Settings:
    issuer = getenv("FEIDE_ISSUER", "https://auth.dataporten.no")
    client_id = getenv("DATASOURCE_CLIENT_ID", "")
    client_secret = getenv("DATASOURCE_CLIENT_SECRET", "")
    datasource_audience = getenv("DATASOURCE_AUDIENCE", "")
    required_scope = getenv("DATASOURCE_REQUIRED_SCOPE", "")
    token_exchange_audience = getenv("DATASOURCE_TOKEN_EXCHANGE_AUDIENCE", "")
    token_exchange_scope = getenv("DATASOURCE_TOKEN_EXCHANGE_SCOPE", "")

    extended_userinfo_url = getenv(
        "FEIDE_EXTENDED_USERINFO_URL", "https://api.dataporten.no/userinfo/v1/userinfo"
    )
    groupinfo_url = getenv(
        "FEIDE_GROUPINFO_URL", "https://groups-api.dataporten.no/groups/me/groups"
    )

    # Fail early with clear errors. These are required to run the sample.
    missing: list[str] = []
    if not client_id:
        missing.append("OIDC_CLIENT_ID")
    if not client_secret:
        missing.append("OIDC_CLIENT_SECRET")
    if not datasource_audience:
        missing.append("DATASOURCE_AUDIENCE")
    if not required_scope:
        missing.append("DATASOURCE_REQUIRED_SCOPE")
    if not token_exchange_audience:
        missing.append("DATASOURCE_TOKEN_EXCHANGE_AUDIENCE")

    if missing:
        joined = ", ".join(missing)
        raise RuntimeError(f"Missing required environment variables: {joined}")

    return Settings(
        issuer=issuer,
        client_id=client_id,
        client_secret=client_secret,
        datasource_audience=datasource_audience,
        required_scope=required_scope,
        token_exchange_audience=token_exchange_audience,
        token_exchange_scope=token_exchange_scope,
        extended_userinfo_url=extended_userinfo_url,
        groupinfo_url=groupinfo_url,
    )
