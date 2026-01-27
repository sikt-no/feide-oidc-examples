"""Feide OIDC endpoint interactions.

This module intentionally keeps the HTTP calls explicit and typed.
"""

from __future__ import annotations

from collections.abc import Mapping
from dataclasses import dataclass

import requests

from feide_login_core.json_utils import json_object_from_response
from feide_login_core.oidc_models import DiscoveryDocument, TokenExchangeResponse, TokenResponse


class OIDCError(RuntimeError):
    pass


@dataclass(frozen=True)
class OIDCClient:
    issuer: str
    client_id: str
    client_secret: str
    redirect_uri: str
    http_timeout_s: float = 5.0

    _discovery_cache: DiscoveryDocument | None = None
    _jwks_cache: Mapping[str, object] | None = None

    def discover_configuration(self) -> DiscoveryDocument:
        if self._discovery_cache is not None:
            return self._discovery_cache

        url = f"{self.issuer.rstrip('/')}/.well-known/openid-configuration"
        resp = requests.get(url, timeout=self.http_timeout_s)
        if resp.status_code != 200:
            raise OIDCError(f"Discovery failed ({resp.status_code}): {resp.text}")
        doc = DiscoveryDocument.from_json(
            json_object_from_response(resp, error="Discovery response is not a JSON object")
        )
        object.__setattr__(self, "_discovery_cache", doc)
        return doc

    def fetch_jwks(self) -> Mapping[str, object]:
        if self._jwks_cache is not None:
            return self._jwks_cache

        jwks_uri = self.discover_configuration().jwks_uri
        resp = requests.get(jwks_uri, timeout=self.http_timeout_s)
        if resp.status_code != 200:
            raise OIDCError(f"JWKS fetch failed ({resp.status_code}): {resp.text}")
        jwks = json_object_from_response(resp, error="JWKS response is not a JSON object")
        if "keys" not in jwks:
            raise OIDCError("JWKS response missing 'keys'")
        object.__setattr__(self, "_jwks_cache", jwks)
        return jwks

    def exchange_code_for_tokens(self, *, code: str, code_verifier: str) -> TokenResponse:
        doc = self.discover_configuration()
        resp = requests.post(
            doc.token_endpoint,
            data={
                "grant_type": "authorization_code",
                "code": code,
                "redirect_uri": self.redirect_uri,
                "code_verifier": code_verifier,
            },
            auth=(self.client_id, self.client_secret),
            timeout=self.http_timeout_s,
        )
        if resp.status_code != 200:
            raise OIDCError(f"Token call failed ({resp.status_code}): {resp.text}")
        return TokenResponse.from_json(
            json_object_from_response(resp, error="Token response is not a JSON object")
        )

    def userinfo(self, *, access_token: str) -> Mapping[str, object]:
        """OIDC userinfo endpoint from discovery."""
        url = self.discover_configuration().userinfo_endpoint
        resp = requests.get(
            url,
            headers={"Authorization": f"Bearer {access_token}"},
            timeout=self.http_timeout_s,
        )
        if resp.status_code != 200:
            raise OIDCError(f"userinfo failed ({resp.status_code}): {resp.text}")
        return json_object_from_response(resp, error="userinfo response is not a JSON object")

    def extended_userinfo(
        self, *, access_token: str, extended_userinfo_url: str
    ) -> Mapping[str, object]:
        """Feide extended userinfo endpoint (directory attributes)."""
        resp = requests.get(
            extended_userinfo_url,
            headers={"Authorization": f"Bearer {access_token}"},
            timeout=self.http_timeout_s,
        )
        if resp.status_code != 200:
            raise OIDCError(f"extended userinfo failed ({resp.status_code}): {resp.text}")
        return json_object_from_response(
            resp, error="extended userinfo response is not a JSON object"
        )

    def token_exchange(
        self,
        *,
        subject_token: str,
        audience: str,
        scope: str,
        subject_token_type: str = "urn:ietf:params:oauth:token-type:access_token",
        requested_token_type: str | None = None,
    ) -> TokenExchangeResponse:
        """RFC 8693 token exchange for a JWT-based access token.

        The initial access token from Feide should be treated as opaque.
        This function exchanges it for an access token intended for a specific audience.
        """
        doc = self.discover_configuration()
        data = {
            "grant_type": "urn:ietf:params:oauth:grant-type:token-exchange",
            "subject_token_type": subject_token_type,
            "subject_token": subject_token,
            "audience": audience,
            "scope": scope,
            **(
                {"requested_token_type": requested_token_type}
                if requested_token_type is not None
                else {}
            ),
        }
        resp = requests.post(
            doc.token_endpoint,
            data=data,
            auth=(self.client_id, self.client_secret),
            timeout=self.http_timeout_s,
        )
        if resp.status_code != 200:
            raise OIDCError(
                "token exchange failed " f"({resp.status_code}): {resp.text}. " f"params={data}"
            )
        return TokenExchangeResponse.from_json(
            json_object_from_response(resp, error="Token exchange response is not a JSON object")
        )
