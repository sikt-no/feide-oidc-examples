"""Type-safe Flask app for a Feide data source API.

Routes / endpoints:
- /me    Returns extended userinfo and groupinfo for the authenticated subject

This sample is intentionally explicit. No OAuth2 third-party libraries are used.
"""

# pyright: reportUnusedFunction=false

from __future__ import annotations

import json
from collections.abc import Mapping
from http import HTTPStatus
from typing import Any, cast

import requests
from flask import Flask, Response, request

from feide_data_source_api.config import Settings, load_settings
from feide_login_core.json_utils import require_json_array
from feide_login_core.jwt_validation import AccessTokenValidationError, validate_access_token
from feide_login_core.oidc import OIDCClient, OIDCError


def _json_response(data: Any, *, status: int = HTTPStatus.OK) -> Response:
    return Response(
        json.dumps(data, indent=2, sort_keys=True), status=status, mimetype="application/json"
    )


def _extract_bearer_token() -> str | None:
    auth = request.headers.get("Authorization", "")
    if not auth.startswith("Bearer "):
        return None
    return auth.removeprefix("Bearer ").strip() or None


def _has_scope(claims: Mapping[str, object], required_scope: str) -> bool:
    raw = claims.get("scope")
    if isinstance(raw, str):
        return required_scope in raw.split()
    if isinstance(raw, list):
        raw_list = cast(list[object], raw)
        for item in raw_list:
            if isinstance(item, str) and item == required_scope:
                return True
        return False
    return False


def create_app(settings: Settings) -> Flask:
    app = Flask("feide_data_source_api")

    oidc = OIDCClient(
        issuer=settings.issuer,
        client_id=settings.client_id,
        client_secret=settings.client_secret,
        redirect_uri="http://unused",  # We are only using the token endpoint (client credentials).
        http_timeout_s=settings.http_timeout_s,
    )

    @app.get("/me")
    def me():
        access_token = _extract_bearer_token()
        if not access_token:
            return "Missing Bearer token", HTTPStatus.UNAUTHORIZED

        try:
            claims = validate_access_token(
                token=access_token,
                jwks=oidc.fetch_jwks(),
                issuer=settings.issuer,
                audience=settings.datasource_audience,
            )
        except (AccessTokenValidationError, OIDCError) as exc:
            return f"Invalid access token: {exc}", HTTPStatus.UNAUTHORIZED

        if not _has_scope(claims, settings.required_scope):
            return f"Missing required scope: {settings.required_scope}", HTTPStatus.FORBIDDEN

        try:
            exchanged = oidc.token_exchange(
                subject_token=access_token,
                audience=settings.token_exchange_audience,
                scope=settings.token_exchange_scope,
                subject_token_type="urn:ietf:params:oauth:token-type:jwt",
                requested_token_type="urn:ietf:params:oauth:token-type:access_token",
            )
        except OIDCError as exc:
            return f"token exchange error: {exc}", HTTPStatus.BAD_GATEWAY

        try:
            extended_userinfo = oidc.extended_userinfo(
                access_token=exchanged.access_token,
                extended_userinfo_url=settings.extended_userinfo_url,
            )
        except OIDCError as exc:
            return f"extended userinfo error: {exc}", HTTPStatus.BAD_GATEWAY

        groupinfo_resp = requests.get(
            settings.groupinfo_url,
            headers={"Authorization": f"Bearer {exchanged.access_token}"},
            timeout=settings.http_timeout_s,
        )
        if groupinfo_resp.status_code != HTTPStatus.OK:
            return (
                f"groupinfo error ({groupinfo_resp.status_code}): {groupinfo_resp.text}",
                HTTPStatus.BAD_GATEWAY,
            )
        groupinfo = require_json_array(
            groupinfo_resp.json(), error="groupinfo response is not a JSON array"
        )

        return _json_response(
            {
                "subject": claims.get("sub"),
                "extended_userinfo": dict(extended_userinfo),
                "groupinfo": groupinfo,
            }
        )

    return app


def main() -> None:
    settings = load_settings()
    app = create_app(settings)
    app.run(host="0.0.0.0", port=8001, debug=False)


if __name__ == "__main__":
    main()
