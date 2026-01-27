"""Small service helpers for the Feide login example."""

from __future__ import annotations

from collections.abc import Mapping

import requests

from feide_login_core.oidc import OIDCClient, OIDCError
from feide_login_core.oidc_models import TokenExchangeResponse, TokenResponse


def build_authorization_url(
    *,
    oidc: OIDCClient,
    client_id: str,
    redirect_uri: str,
    scope: str,
    state: str,
    nonce: str,
    challenge: str,
) -> str:
    authz_endpoint = oidc.discover_configuration().authorization_endpoint
    params = {
        "response_type": "code",
        "client_id": client_id,
        "redirect_uri": redirect_uri,
        "scope": scope,
        "state": state,
        "nonce": nonce,
        "code_challenge": challenge,
        "code_challenge_method": "S256",
    }
    request_url = requests.Request("GET", authz_endpoint, params=params).prepare().url
    if not request_url:
        raise OIDCError("Failed to construct authorization request URL")
    return request_url


def exchange_code_for_tokens(*, oidc: OIDCClient, code: str, code_verifier: str) -> TokenResponse:
    return oidc.exchange_code_for_tokens(code=code, code_verifier=code_verifier)


def fetch_userinfo(*, oidc: OIDCClient, access_token: str) -> Mapping[str, object]:
    return oidc.userinfo(access_token=access_token)


def fetch_extended_userinfo(
    *, oidc: OIDCClient, access_token: str, extended_userinfo_url: str
) -> Mapping[str, object] | None:
    try:
        return oidc.extended_userinfo(
            access_token=access_token,
            extended_userinfo_url=extended_userinfo_url,
        )
    except OIDCError:
        return None


def exchange_access_token_for_jwt(
    *, oidc: OIDCClient, access_token: str, audience: str, scope: str
) -> TokenExchangeResponse:
    return oidc.token_exchange(
        subject_token=access_token,
        audience=audience,
        scope=scope,
    )
