from __future__ import annotations

from collections.abc import Mapping

import pytest
import requests

from feide_login_core.oidc import OIDCClient


class _FakeResponse:
    status_code: int
    _payload: Mapping[str, object]
    text: str

    def __init__(self, status_code: int, payload: Mapping[str, object]) -> None:
        self.status_code = status_code
        self._payload = payload
        self.text = str(payload)

    def json(self) -> Mapping[str, object]:
        return self._payload


def test_token_exchange_sends_expected_request(monkeypatch: pytest.MonkeyPatch) -> None:
    captured: dict[str, object] = {}

    def fake_get(url: str, timeout: float) -> _FakeResponse:
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
        if url.endswith("/jwks"):
            return _FakeResponse(200, {"keys": []})
        raise AssertionError(f"unexpected GET: {url}")

    def fake_post(
        url: str, data: Mapping[str, object], auth: tuple[str, str], timeout: float
    ) -> _FakeResponse:
        _ = timeout
        captured["url"] = url
        captured["data"] = dict(data)
        captured["auth"] = auth
        return _FakeResponse(
            200, {"access_token": "jwt-ish", "token_type": "Bearer", "expires_in": 3600}
        )

    monkeypatch.setattr(requests, "get", fake_get)
    monkeypatch.setattr(requests, "post", fake_post)

    client = OIDCClient(
        issuer="https://issuer",
        client_id="cid",
        client_secret="csec",
        redirect_uri="http://localhost/callback",
    )

    _ = client.token_exchange(subject_token="opaque", audience="aud", scope="scope1 scope2")

    assert captured["url"] == "https://issuer/token"
    assert captured["auth"] == ("cid", "csec")
    data = captured.get("data")
    assert isinstance(data, dict)
    assert data["grant_type"] == "urn:ietf:params:oauth:grant-type:token-exchange"
    assert data["subject_token"] == "opaque"
    assert data["audience"] == "aud"
    assert data["scope"] == "scope1 scope2"


def test_userinfo_uses_bearer_token(monkeypatch: pytest.MonkeyPatch) -> None:
    captured: dict[str, object] = {}

    def fake_get(
        url: str, headers: Mapping[str, str] | None = None, timeout: float | None = None
    ) -> _FakeResponse:
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
            assert headers is not None
            captured["authz"] = headers.get("Authorization")
            return _FakeResponse(200, {"sub": "u"})
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

    _ = client.userinfo(access_token="opaque-token")
    assert captured["authz"] == "Bearer opaque-token"
