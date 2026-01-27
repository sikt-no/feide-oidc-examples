"""Minimal Flask app showing the OIDC auth code + PKCE flow.

This example is intentionally small to show the protocol steps
THIS IS NOT PRODUCTION READY CODE. See full example for production considerations.
"""

# pyright: reportUnusedFunction=false

from __future__ import annotations

import json
import secrets

import requests
from flask import Flask, redirect, request, session, url_for
from jose import jwt

from feide_login_core.oidc_simple import discover_configuration, exchange_code_for_tokens
from feide_login_core.pkce import generate_pkce


def create_app() -> Flask:
    app = Flask(__name__)
    app.secret_key = secrets.token_urlsafe(32)

    @app.get("/")
    def index() -> str:
        if "user" in session:
            sub = session["user"].get("sub", "unknown")
            return (
                f"<p>Logged in as <code>{sub}</code></p>"
                "<p><a href='/logout'>Log out from app</a></p>"
            )
        return "<a href='/login'>Log in with Feide</a>"

    @app.get("/login")
    def login():
        # Step 1: Generate PKCE verifier/challenge and anti-CSRF state/nonce.
        verifier, challenge = generate_pkce()
        state = secrets.token_urlsafe(16)
        nonce = secrets.token_urlsafe(16)

        session["pkce_verifier"] = verifier
        session["state"] = state
        session["nonce"] = nonce

        # Step 2: Discover endpoints and redirect to the authorization endpoint in Feide.
        config = discover_configuration()
        params = {
            "response_type": "code",
            "client_id": config["client_id"],
            "redirect_uri": config["redirect_uri"],
            "scope": "openid profile email",
            "state": state,
            "nonce": nonce,
            "code_challenge": challenge,
            "code_challenge_method": "S256",
        }

        request_url = (
            requests.Request("GET", config["authorization_endpoint"], params=params).prepare().url
        )
        if not request_url:
            return "Failed to construct authorization request URL", 500
        return redirect(request_url)

    @app.get("/callback")
    def callback():
        # Step 3: Validate the state returned to the redirect URI.
        if request.args.get("state") != session.get("state"):
            return "Invalid state", 400

        code = request.args.get("code")
        if not code:
            return "Missing authorization code", 400

        verifier = session.get("pkce_verifier")
        if not isinstance(verifier, str):
            return "Missing PKCE verifier in session", 400

        # Step 4: Exchange the authorization code and verifier for tokens at the token endpoint in Feide.
        token_response = exchange_code_for_tokens(code=code, code_verifier=verifier)
        id_token = token_response.get("id_token")

        # Step 5: Decode ID token claims (DEMO ONLY - no signature verification!).
        claims = jwt.get_unverified_claims(id_token) if isinstance(id_token, str) else {}

        # Step 6: Store a small session payload for the index page.
        session["user"] = {
            "sub": claims.get("sub", "unknown"),
            "id_token_claims": claims,
        }
        claims_payload = json.dumps(claims, indent=2, sort_keys=True)
        return (
            "<p>Login complete.</p>"
            "<p>ID token claims (unverified):</p>"
            f"<pre>{claims_payload}</pre>"
            "<p><a href='/'>Go home</a></p>"
        )

    @app.get("/logout")
    def logout():
        # Note : This only logs out from the app. A full logout from Feide would require
        # redirecting the user to the Feide end session endpoint. See full example.
        session.clear()
        return redirect(url_for("index"))

    return app


def main() -> None:
    app = create_app()
    app.run(host="0.0.0.0", port=8000, debug=False)


if __name__ == "__main__":
    main()
