"""Minimal OIDC client utilities for the simple example."""

from __future__ import annotations

import os

import requests

from feide_login_core.json_utils import require_json_object


def _require_str(value: object, *, key: str) -> str:
    if not isinstance(value, str):
        raise ValueError(f"Expected str for {key}")
    return value


def discover_configuration() -> dict[str, object]:
    issuer = os.getenv("FEIDE_ISSUER", "https://auth.dataporten.no")
    client_id = os.environ["OIDC_CLIENT_ID"]
    client_secret = os.environ["OIDC_CLIENT_SECRET"]
    redirect_uri = os.environ["OIDC_REDIRECT_URI"]

    url = f"{issuer.rstrip('/')}/.well-known/openid-configuration"
    resp = requests.get(url, timeout=5.0)
    resp.raise_for_status()
    doc = require_json_object(resp.json(), error="Discovery response is not a JSON object")

    return {
        "authorization_endpoint": doc["authorization_endpoint"],
        "token_endpoint": doc["token_endpoint"],
        "client_id": client_id,
        "client_secret": client_secret,
        "redirect_uri": redirect_uri,
    }


def exchange_code_for_tokens(*, code: str, code_verifier: str) -> dict[str, object]:
    config = discover_configuration()
    token_endpoint = _require_str(config["token_endpoint"], key="token_endpoint")
    client_id = _require_str(config["client_id"], key="client_id")
    client_secret = _require_str(config["client_secret"], key="client_secret")
    redirect_uri = _require_str(config["redirect_uri"], key="redirect_uri")
    resp = requests.post(
        token_endpoint,
        data={
            "grant_type": "authorization_code",
            "code": code,
            "redirect_uri": redirect_uri,
            "code_verifier": code_verifier,
        },
        auth=(client_id, client_secret),
        timeout=5.0,
    )
    resp.raise_for_status()
    data = require_json_object(resp.json(), error="Token response is not a JSON object")
    return dict(data)
