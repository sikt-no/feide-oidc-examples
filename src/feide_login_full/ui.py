"""Small HTML helpers for the login flow ."""

from __future__ import annotations

import html
import json
from collections.abc import Mapping
from typing import cast

from flask import Response


def html_page(title: str, body: str, *, status: int = 200) -> Response:
    home_link = "<p><a href='/'>Return home</a></p>"
    html = (
        "<!doctype html>"
        "<html lang='en'>"
        "<head>"
        "<meta charset='utf-8'>"
        f"<title>{title}</title>"
        "</head>"
        "<body>"
        f"<h1>{title}</h1>"
        f"{home_link}{body}"
        "</body>"
        "</html>"
    )
    return Response(html, status=status, mimetype="text/html")


def render_json_page(title: str, data: Mapping[str, object], *, status: int = 200) -> Response:
    payload = json.dumps(data, indent=2, sort_keys=True)
    body = f"<pre>{html.escape(payload)}</pre>"
    return html_page(title, body, status=status)


def render_json_block(title: str, data: object) -> str:
    payload = json.dumps(data, indent=2, sort_keys=True)
    return f"<h2>{html.escape(title)}</h2><pre>{html.escape(payload)}</pre>"


def as_mapping(value: object) -> Mapping[str, object]:
    if isinstance(value, Mapping):
        return cast(Mapping[str, object], value)
    return {}


def render_index_page(
    *,
    sub: str,
    id_token_claims: Mapping[str, object],
    oidc_userinfo: Mapping[str, object],
    extended_userinfo: Mapping[str, object],
    access_token: str,
    access_expires: object,
    exchanged_access_token: str,
    exchanged_expires: object,
) -> str:
    datasource_link = (
        "<a href='/datasource'>Call datasource</a> "
        if exchanged_access_token
        else "<span>Call datasource (get access token first)</span> "
    )
    token_info = {
        "feide_access_token": access_token,
        "feide_access_token_expires_in": access_expires,
        "exchanged_jwt_access_token": exchanged_access_token,
        "exchanged_jwt_access_token_expires_in": exchanged_expires,
    }
    return (
        f"<p>Logged in as <code>{sub}</code></p>"
        "<p><a href='/exchange'>Get datasource access token</a> "
        f"{datasource_link}"
        "<a href='/logout'>Log out from Feide and app</a> </p>"
        + render_json_block("Access tokens", token_info)
        + render_json_block("ID token claims", id_token_claims)
        + render_json_block("OIDC userinfo", oidc_userinfo)
        + render_json_block("Extended userinfo", extended_userinfo)
    )
