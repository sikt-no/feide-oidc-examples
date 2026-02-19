from __future__ import annotations

from collections.abc import Mapping

import pytest
import requests

import feide_data_source_api.app as app_module
from feide_data_source_api.app import create_app
from feide_data_source_api.config import Settings


class _FakeOIDCClient:
    def __init__(self) -> None:
        self._jwks = {"keys": [{"kid": "k", "kty": "oct", "k": "x"}]}

    def fetch_jwks(self) -> Mapping[str, object]:
        return self._jwks

    def token_exchange(
        self,
        *,
        subject_token: str,
        audience: str,
        scope: str,
        subject_token_type: str = "urn:ietf:params:oauth:token-type:access_token",
        requested_token_type: str | None = None,
    ):
        class _Token:
            def __init__(self, scope_value: str) -> None:
                self.access_token = "exchanged"
                self.token_type = "Bearer"
                self.expires_in = 3600
                self.scope = scope_value

        return _Token(scope)

    def extended_userinfo(
        self, *, access_token: str, extended_userinfo_url: str
    ) -> Mapping[str, object]:
        return {"sub": "user-1"}


def test_me_requires_bearer_token(monkeypatch: pytest.MonkeyPatch) -> None:
    settings = Settings(
        issuer="https://issuer",
        client_id="c_id",
        client_secret="c_sec",
        datasource_audience="aud",
        required_scope="readUser",
        token_exchange_audience="ex-aud",
        token_exchange_scope="readUser",
        extended_userinfo_url="https://example/userinfo",
        groupinfo_url="https://example/groups",
    )

    app = create_app(settings)
    client = app.test_client()
    resp = client.get("/me")
    assert resp.status_code == 401


def test_me_returns_userinfo_and_groupinfo(monkeypatch: pytest.MonkeyPatch) -> None:
    settings = Settings(
        issuer="https://issuer",
        client_id="cid",
        client_secret="c_sec",
        datasource_audience="aud",
        required_scope="readUser",
        token_exchange_audience="ex-aud",
        token_exchange_scope="readUser",
        extended_userinfo_url="https://example/userinfo",
        groupinfo_url="https://example/groups",
    )

    monkeypatch.setattr(app_module, "OIDCClient", lambda **kwargs: _FakeOIDCClient())
    monkeypatch.setattr(
        app_module,
        "validate_access_token",
        lambda **kwargs: {"sub": "user-1", "scope": "readUser"},
    )

    def fake_get(url: str, headers: Mapping[str, str], timeout: float):
        class _Resp:
            status_code = 200
            text = "ok"

            def json(self):
                return [{"id": "g1"}, {"id": "g2"}]

        return _Resp()

    monkeypatch.setattr(requests, "get", fake_get)

    app = create_app(settings)
    client = app.test_client()
    resp = client.get("/me", headers={"Authorization": "Bearer token"})
    assert resp.status_code == 200
    data = resp.get_json()
    assert data["subject"] == "user-1"
    assert "extended_userinfo" in data
    assert "groupinfo" in data


def test_me_requires_scope(monkeypatch: pytest.MonkeyPatch) -> None:
    settings = Settings(
        issuer="https://issuer",
        client_id="cid",
        client_secret="c_sec",
        datasource_audience="aud",
        required_scope="readUser",
        token_exchange_audience="ex-aud",
        token_exchange_scope="readUser",
        extended_userinfo_url="https://example/userinfo",
        groupinfo_url="https://example/groups",
    )

    monkeypatch.setattr(app_module, "OIDCClient", lambda **kwargs: _FakeOIDCClient())
    monkeypatch.setattr(app_module, "validate_access_token", lambda **kwargs: {"sub": "user-1"})

    app = create_app(settings)
    client = app.test_client()
    resp = client.get("/me", headers={"Authorization": "Bearer token"})
    assert resp.status_code == 403
