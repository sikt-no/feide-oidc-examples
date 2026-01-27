from __future__ import annotations

from collections.abc import Mapping

import pytest
import requests

from feide_login_core.oidc import OIDCClient, OIDCError


class _FakeResponse:
    status_code: int
    _payload: object
    text: str

    def __init__(self, status_code: int, payload: object) -> None:
        self.status_code = status_code
        self._payload = payload
        self.text = str(payload)

    def json(self) -> object:
        return self._payload


def test_discover_configuration_non_200_raises_oidc_error(monkeypatch: pytest.MonkeyPatch) -> None:
    def fake_get(url: str, timeout: float) -> _FakeResponse:
        _ = url
        _ = timeout
        return _FakeResponse(500, {"error": "boom"})

    monkeypatch.setattr(requests, "get", fake_get)

    client = OIDCClient(
        issuer="https://issuer",
        client_id="cid",
        client_secret="csec",
        redirect_uri="http://localhost/callback",
    )

    with pytest.raises(OIDCError):
        _ = client.discover_configuration()


def test_userinfo_non_object_json_raises_value_error(monkeypatch: pytest.MonkeyPatch) -> None:
    def fake_get(
        url: str, headers: Mapping[str, str] | None = None, timeout: float | None = None
    ) -> _FakeResponse:
        _ = headers
        _ = timeout
        if url.endswith("/.well-known/openid-configuration"):
            return _FakeResponse(
                200,
                {
                    "authorization_endpoint": "https://issuer/auth",
                    "token_endpoint": "https://issuer/token",
                    "jwks_uri": "https://issuer/jwks",
                    "userinfo_endpoint": "https://issuer/userinfo",
                },
            )
        if url.endswith("/userinfo"):
            return _FakeResponse(200, ["not", "a", "dict"])
        if url.endswith("/jwks"):
            return _FakeResponse(200, {"keys": []})
        raise AssertionError(f"unexpected GET: {url}")

    monkeypatch.setattr(requests, "get", fake_get)

    client = OIDCClient(
        issuer="https://issuer",
        client_id="cid",
        client_secret="csec",
        redirect_uri="http://localhost/callback",
    )

    with pytest.raises(ValueError):
        _ = client.userinfo(access_token="opaque-token")
