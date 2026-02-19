from __future__ import annotations

import os

import pytest
import requests

from feide_login_simple.app import create_app


class _FakeResponse:
    def __init__(self, payload: object, status_code: int = 200) -> None:
        self._payload = payload
        self.status_code = status_code

    def json(self) -> object:
        return self._payload

    def raise_for_status(self) -> None:
        if self.status_code >= 400:
            raise RuntimeError("bad response")


def test_login_redirects_to_authorization_endpoint(monkeypatch: pytest.MonkeyPatch) -> None:
    os.environ["OIDC_CLIENT_ID"] = "cid"
    os.environ["OIDC_CLIENT_SECRET"] = "csec"
    os.environ["OIDC_REDIRECT_URI"] = "http://localhost/callback"

    def fake_get(url: str, timeout: float) -> _FakeResponse:
        _ = url
        _ = timeout
        return _FakeResponse(
            {
                "authorization_endpoint": "https://issuer/auth",
                "token_endpoint": "https://issuer/token",
            }
        )

    monkeypatch.setattr(requests, "get", fake_get)

    app = create_app()
    client = app.test_client()

    resp = client.get("/login")
    assert resp.status_code == 302
    assert "https://issuer/auth" in resp.location
