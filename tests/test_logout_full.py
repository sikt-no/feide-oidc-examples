from __future__ import annotations

from urllib.parse import parse_qs, urlparse

import pytest

import feide_login_full.app as app_module
from feide_login_core.oidc_models import DiscoveryDocument
from feide_login_full.config import Settings


class _FakeOIDCClient:
    def __init__(self, end_session_endpoint: str | None) -> None:
        self._doc = DiscoveryDocument(
            authorization_endpoint="https://issuer/auth",
            token_endpoint="https://issuer/token",
            jwks_uri="https://issuer/jwks",
            userinfo_endpoint="https://issuer/userinfo",
            end_session_endpoint=end_session_endpoint,
        )

    def discover_configuration(self) -> DiscoveryDocument:
        return self._doc


def _settings() -> Settings:
    return Settings(
        issuer="https://issuer",
        client_id="cid",
        client_secret="csec",
        redirect_uri="http://localhost/callback",
        app_secret_key="secret",
        extended_userinfo_url="https://example/userinfo",
        token_exchange_audience=None,
        token_exchange_scope=None,
        post_logout_redirect_uri=None,
        datasource_api_url=None,
    )


def test_logout_redirects_to_end_session(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(
        app_module, "OIDCClient", lambda **kwargs: _FakeOIDCClient("https://issuer/logout")
    )
    app = app_module.create_app(_settings())
    client = app.test_client()

    with client.session_transaction() as session:
        session["id_token_hint"] = "id-token"

    resp = client.get("/logout")
    assert resp.status_code == 302
    assert resp.location.startswith("https://issuer/logout?")
    parsed = urlparse(resp.location)
    params = parse_qs(parsed.query)
    assert params["id_token_hint"] == ["id-token"]
    assert params["post_logout_redirect_uri"][0].endswith("/post-logout")


def test_logout_falls_back_to_index_when_no_endpoint(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(app_module, "OIDCClient", lambda **kwargs: _FakeOIDCClient(None))
    app = app_module.create_app(_settings())
    client = app.test_client()

    resp = client.get("/logout")
    assert resp.status_code == 200
    assert b"logged out locally" in resp.data


def test_logout_uses_configured_post_logout_redirect(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(
        app_module, "OIDCClient", lambda **kwargs: _FakeOIDCClient("https://issuer/logout")
    )
    settings = _settings()
    settings = Settings(
        issuer=settings.issuer,
        client_id=settings.client_id,
        client_secret=settings.client_secret,
        redirect_uri=settings.redirect_uri,
        app_secret_key=settings.app_secret_key,
        extended_userinfo_url=settings.extended_userinfo_url,
        token_exchange_audience=settings.token_exchange_audience,
        token_exchange_scope=settings.token_exchange_scope,
        post_logout_redirect_uri="http://localhost/custom-logout",
        datasource_api_url=settings.datasource_api_url,
    )
    app = app_module.create_app(settings)
    client = app.test_client()

    resp = client.get("/logout")
    assert resp.status_code == 302
    parsed = urlparse(resp.location)
    params = parse_qs(parsed.query)
    assert params["post_logout_redirect_uri"] == ["http://localhost/custom-logout"]
