"""Type-safe Flask app demonstrating Feide login.

Routes:
- /              Home (shows session status)
- /login         Starts OIDC Authorization Code + PKCE
- /callback      Handles redirect, validates ID token, fetches userinfo
- /logout        Clears session and redirects to the Feide logout endpoint (if available)
- /post-logout   Landing endpoint after Feide logout
- /exchange      Demonstrates token exchange (requires env vars for audience/scope)
- /datasource    Calls the data source API with the exchanged token

This sample is intentionally explicit. No third-party OIDC libraries are used.
"""

# pyright: reportUnusedFunction=false

from __future__ import annotations

import secrets
from http import HTTPStatus
from typing import cast
from urllib.parse import urlencode

import requests
from flask import Flask, Response, redirect, request, session, url_for

from feide_login_core.jwt_validation import IDTokenValidationError, validate_id_token
from feide_login_core.oidc import OIDCClient, OIDCError
from feide_login_core.pkce import generate_pkce
from feide_login_full.config import Settings, load_settings
from feide_login_full.login_flow import (
    build_authorization_url,
    exchange_access_token_for_jwt,
    exchange_code_for_tokens,
    fetch_extended_userinfo,
    fetch_userinfo,
)
from feide_login_full.ui import as_mapping, html_page, render_index_page, render_json_page


def _require_logged_in_user() -> dict[str, object] | Response:
    user = session.get("user")
    if not isinstance(user, dict):
        return html_page(
            "Not logged in",
            "<p>You are not logged in.</p><p><a href='/'>Return home</a></p>",
            status=HTTPStatus.UNAUTHORIZED,
        )
    return cast(dict[str, object], user)


def _require_token(
    user_dict: dict[str, object],
    *,
    key: str,
    title: str,
    message: str,
    status: int = HTTPStatus.BAD_REQUEST,
) -> str | Response:
    value = user_dict.get(key)
    if not isinstance(value, str) or not value:
        return html_page(
            title,
            f"<p>{message}</p><p><a href='/'>Return home</a></p>",
            status=status,
        )
    return value


def create_app(settings: Settings) -> Flask:
    app = Flask(__name__)
    app.secret_key = settings.app_secret_key

    oidc = OIDCClient(
        issuer=settings.issuer,
        client_id=settings.client_id,
        client_secret=settings.client_secret,
        redirect_uri=settings.redirect_uri,
    )

    @app.get("/")
    def index() -> str:
        # Step 6 (post-login): landing page shows current session info and demo actions.
        user = session.get("user")
        if isinstance(user, dict):
            user_dict = cast(dict[str, object], user)
            sub_value = user_dict.get("sub")
            sub = sub_value if isinstance(sub_value, str) else "unknown"
            id_token_claims = as_mapping(user_dict.get("id_token_claims"))
            oidc_userinfo = as_mapping(user_dict.get("oidc_userinfo"))
            extended_userinfo = as_mapping(user_dict.get("extended_userinfo"))
            access_token_value = user_dict.get("feide_access_token")
            access_token = access_token_value if isinstance(access_token_value, str) else ""
            access_expires = user_dict.get("feide_access_token_expires_in")
            exchanged_access_token = user_dict.get("exchanged_access_token") or ""
            exchanged_expires = user_dict.get("exchanged_expires_in")
            return render_index_page(
                sub=sub,
                id_token_claims=id_token_claims,
                oidc_userinfo=oidc_userinfo,
                extended_userinfo=extended_userinfo,
                access_token=access_token,
                access_expires=access_expires,
                exchanged_access_token=(
                    exchanged_access_token if isinstance(exchanged_access_token, str) else ""
                ),
                exchanged_expires=exchanged_expires,
            )
        return "<a href='/login'>Log in with Feide</a>"

    @app.get("/login")
    def login():
        # Step 1: start authorization code + PKCE by redirecting to Feide.
        verifier, challenge = generate_pkce()
        state = secrets.token_urlsafe(16)
        nonce = secrets.token_urlsafe(16)

        session["pkce_verifier"] = verifier
        session["state"] = state
        session["nonce"] = nonce

        try:
            request_url = build_authorization_url(
                oidc=oidc,
                client_id=settings.client_id,
                redirect_uri=settings.redirect_uri,
                scope="openid",
                state=state,
                nonce=nonce,
                challenge=challenge,
            )
        except OIDCError as exc:
            return html_page(
                "Discovery failed",
                f"<p>{exc}</p><p><a href='/'>Return home</a></p>",
                status=HTTPStatus.INTERNAL_SERVER_ERROR,
            )

        return redirect(request_url)

    @app.get("/callback")
    def callback():
        # Step 2: handle Feide redirect, exchange code for tokens, validate ID token.
        if request.args.get("state") != session.get("state"):
            print(
                "state mismatch",
                {
                    "request_state": request.args.get("state"),
                    "session_state": session.get("state"),
                },
            )
            return html_page(
                "Invalid state",
                "<p>Invalid state in callback.</p><p><a href='/'>Return home</a></p>",
                status=HTTPStatus.BAD_REQUEST,
            )

        code = request.args.get("code")
        if not code:
            return html_page(
                "Missing authorization code",
                "<p>Missing authorization code.</p><p><a href='/'>Return home</a></p>",
                status=HTTPStatus.BAD_REQUEST,
            )

        verifier = session.get("pkce_verifier")
        if not isinstance(verifier, str) or not verifier:
            return html_page(
                "Missing PKCE verifier",
                "<p>Missing PKCE verifier in session.</p><p><a href='/'>Return home</a></p>",
                status=HTTPStatus.BAD_REQUEST,
            )

        expected_nonce = session.get("nonce")
        if not isinstance(expected_nonce, str) or not expected_nonce:
            return html_page(
                "Missing nonce",
                "<p>Missing nonce in session.</p><p><a href='/'>Return home</a></p>",
                status=HTTPStatus.BAD_REQUEST,
            )

        try:
            token_response = exchange_code_for_tokens(oidc=oidc, code=code, code_verifier=verifier)
        except OIDCError as exc:
            return html_page(
                "Token endpoint error",
                f"<p>{exc}</p><p><a href='/'>Return home</a></p>",
                status=HTTPStatus.BAD_GATEWAY,
            )

        if token_response.id_token is None:
            return html_page(
                "Missing id_token",
                "<p>Missing id_token in token response.</p><p><a href='/'>Return home</a></p>",
                status=HTTPStatus.BAD_GATEWAY,
            )

        # Validate ID token (JWT). Access token is treated as opaque.
        try:
            id_claims = validate_id_token(
                id_token=token_response.id_token,
                jwks=oidc.fetch_jwks(),
                issuer=settings.issuer,
                audience=settings.client_id,
                expected_nonce=expected_nonce,
            )
        except (OIDCError, IDTokenValidationError) as exc:
            return html_page(
                "Invalid ID token",
                f"<p>{exc}</p><p><a href='/'>Return home</a></p>",
                status=HTTPStatus.BAD_REQUEST,
            )

        # Fetch userinfo using the (opaque) access token.
        try:
            oidc_userinfo = fetch_userinfo(oidc=oidc, access_token=token_response.access_token)
        except OIDCError as exc:
            return html_page(
                "Userinfo error",
                f"<p>{exc}</p><p><a href='/'>Return home</a></p>",
                status=HTTPStatus.BAD_GATEWAY,
            )

        # Fetch extended userinfo (user directory attributes).
        extended = fetch_extended_userinfo(
            oidc=oidc,
            access_token=token_response.access_token,
            extended_userinfo_url=settings.extended_userinfo_url,
        )

        session.clear()
        session["user"] = {
            "sub": id_claims.sub,
            "id_token_claims": dict(id_claims.raw),
            "oidc_userinfo": dict(oidc_userinfo),
            "extended_userinfo": dict(extended) if extended is not None else None,
            # Keep the access token available for demo routes.
            # In a real application, store it securely.
            "feide_access_token": token_response.access_token,
            "feide_access_token_expires_in": token_response.expires_in,
        }
        session["id_token_hint"] = token_response.id_token

        return html_page(
            "Login complete",
            "<p>You are logged in.</p>",
        )

    @app.get("/exchange")
    def exchange():
        # Optional step: exchange the opaque access token for a JWT access token.
        user_dict_or_response = _require_logged_in_user()
        if isinstance(user_dict_or_response, Response):
            return user_dict_or_response
        user_dict = user_dict_or_response
        access_token_or_response = _require_token(
            user_dict,
            key="feide_access_token",
            title="Missing access token",
            message="Missing Feide access token in session.",
        )
        if isinstance(access_token_or_response, Response):
            return access_token_or_response
        access_token = access_token_or_response

        exchange_audience = settings.token_exchange_audience
        if not exchange_audience:
            return html_page(
                "Token exchange not configured",
                "<p>Set FEIDE_TOKEN_EXCHANGE_AUDIENCE.</p>" "<p><a href='/'>Return home</a></p>",
                status=HTTPStatus.BAD_REQUEST,
            )
        # If scope is empty, all available scopes will be requested.
        exchange_scope = settings.token_exchange_scope or ""

        try:
            exchanged = exchange_access_token_for_jwt(
                oidc=oidc,
                access_token=access_token,
                audience=exchange_audience,
                scope=exchange_scope,
            )
        except OIDCError as exc:
            return html_page(
                "Token exchange error",
                f"<p>{exc}</p><p><a href='/'>Return home</a></p>",
                status=HTTPStatus.BAD_GATEWAY,
            )

        session["user"] = {
            **user_dict,
            "exchanged_access_token": exchanged.access_token,
            "exchanged_token_type": exchanged.token_type,
            "exchanged_expires_in": exchanged.expires_in,
            "exchanged_scope": exchanged.scope,
        }

        return render_json_page(
            "Token exchange result",
            {
                "access_token": exchanged.access_token,
                "token_type": exchanged.token_type,
                "expires_in": exchanged.expires_in,
                "scope": exchanged.scope,
                "note": "This access token is expected to be JWT-based (after token exchange).",
            },
        )

    @app.get("/datasource")
    def datasource():
        # Optional step: call the data source API with the exchanged JWT access token.
        user_dict_or_response = _require_logged_in_user()
        if isinstance(user_dict_or_response, Response):
            return user_dict_or_response
        user_dict = user_dict_or_response
        exchanged_token_or_response = _require_token(
            user_dict,
            key="exchanged_access_token",
            title="Missing exchanged token",
            message="Missing exchanged access token. Call /exchange first.",
        )
        if isinstance(exchanged_token_or_response, Response):
            return exchanged_token_or_response
        exchanged_token = exchanged_token_or_response

        if not settings.datasource_api_url:
            return html_page(
                "Data source URL not configured",
                "<p>DATASOURCE_API_URL is not configured.</p>",
                status=HTTPStatus.INTERNAL_SERVER_ERROR,
            )

        url = settings.datasource_api_url.rstrip("/") + "/me"
        resp = requests.get(
            url,
            headers={"Authorization": f"Bearer {exchanged_token}"},
            timeout=5.0,
        )
        if resp.status_code != HTTPStatus.OK:
            return html_page(
                "Data source error",
                f"<p>Status {resp.status_code}</p><pre>{resp.text}</pre>"
                "<p><a href='/'>Return home</a></p>",
                status=HTTPStatus.BAD_GATEWAY,
            )

        try:
            payload = resp.json()
        except ValueError:
            return html_page(
                "Data source error",
                f"<pre>{resp.text}</pre><p><a href='/'>Return home</a></p>",
                status=HTTPStatus.BAD_GATEWAY,
            )

        return render_json_page("Data source response", payload)

    @app.get("/logout")
    def logout():
        # Optional step: end session locally and initiate Feide logout.
        try:
            end_session_endpoint = oidc.discover_configuration().end_session_endpoint
        except OIDCError as exc:
            return html_page(
                "Discovery failed",
                f"<p>{exc}</p><p><a href='/'>Return home</a></p>",
                status=HTTPStatus.INTERNAL_SERVER_ERROR,
            )
        id_token_hint = session.get("id_token_hint")
        session.clear()
        if not end_session_endpoint:
            return html_page(
                "Logged out",
                "<p>You have been logged out locally.</p><p><a href='/'>Return home</a></p>",
            )

        post_logout_redirect_uri = settings.post_logout_redirect_uri or url_for(
            "post_logout", _external=True
        )
        params: dict[str, str] = {
            "post_logout_redirect_uri": post_logout_redirect_uri,
        }
        if isinstance(id_token_hint, str) and id_token_hint:
            params["id_token_hint"] = id_token_hint

        logout_url = f"{end_session_endpoint}?{urlencode(params)}"
        return redirect(logout_url)

    @app.get("/post-logout")
    def post_logout():
        # Final step: user returns here after Feide logout.
        session.clear()
        return (
            "You have been logged out. " "<a href='/'>Log in again</a>.",
            HTTPStatus.OK,
        )

    return app


def main() -> None:
    settings = load_settings()
    app = create_app(settings)
    app.run(host="0.0.0.0", port=8000, debug=False)


if __name__ == "__main__":
    main()
