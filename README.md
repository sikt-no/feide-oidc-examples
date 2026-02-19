# Feide OIDC Examples (Python)

This folder contains **three** runnable examples that demonstrate the Feide OIDC Authorization Code + PKCE flow:

- `feide_login_full`: production-minded, explicit, and security-reviewable.
- `feide_login_simple`: minimal and instructional (NOT production code).
- `feide_data_source_api`: OAuth2-protected data source API (production-minded).

All examples are intentionally explicit and do **not** hide protocol steps behind a library.

Together, `feide_login_full` and `feide_data_source_api` model a common integration scenario: a web app that signs users in with Feide, fetches userinfo, and (optionally) exchanges the access token to call a protected downstream API. The `feide_data_source_api` example represents that downstream service and shows how it validates JWT access tokens and performs its own token exchange to call Feide APIs on behalf of the user.

## OIDC flow reference

These examples implement the OAuth 2.0 Authorization Code flow with PKCE. If you want a concise
reference for why the redirect happens and how the steps fit together, see:

- OAuth 2.0 Authorization Code Grant (RFC 6749), Section 4.1: https://www.rfc-editor.org/rfc/rfc6749#section-4.1
- PKCE (RFC 7636): https://www.rfc-editor.org/rfc/rfc7636

A quick search on the net can be useful, e.g. "OAuth 2.0 authorization code flow", "OIDC authorization code flow" or "OAuth PKCE".

## Project layout

- `src/feide_login_core/` – Shared, production-ready helpers used by both examples
- `src/feide_login_full/` – Production-minded login example (routes + session handling)
- `src/feide_login_simple/` – Minimal, instructional example (not production code)
- `src/feide_data_source_api/` – OAuth2-protected API (data source)
- `tests/` – pytest unit tests (network calls are mocked)

## Requirements (all examples)

- Python **3.13**
- A registered Feide OIDC client (client id / secret)
- Redirect URI registered in Feide

### Using .env and run scripts

The `run_feide_*.zsh` scripts load a local `.env` file (not committed). Use `.env.example` as a
template, copy it to `.env`, and fill in your secrets:

```bash
cp .env.example .env
```

Then run the examples with `./run_feide_login_full.zsh`, `./run_feide_login_simple.zsh`, or
`./run_feide_data_source_api.zsh`.

## Configuration (all examples)

These environment variables should be configured in .env.

For all examples

- `FEIDE_ISSUER` (default: `https://auth.dataporten.no`)

For both login examples

- `OIDC_CLIENT_ID` (client id configured for the login examples)
- `OIDC_CLIENT_SECRET` (client secret configured for the login examples)
- `OIDC_REDIRECT_URI` (example: `http://localhost:8000/callback`)

Only for `feide_login_full`:

- `APP_SECRET_KEY` (random, long; used to protect the Flask session cookie)
- `POST_LOGOUT_REDIRECT_URI` (optional; overrides `/post-logout` as the IdP logout return URL)
- `DATASOURCE_API_URL` (optional; base URL for `feide_data_source_api` when calling `/datasource`)

Only for `feide_data_source_api`:

- `DATASOURCE_AUDIENCE` (audience expected in incoming JWT access tokens)
- `DATASOURCE_REQUIRED_SCOPE` (required scope in incoming access tokens, e.g. `readUser`)
- `DATASOURCE_CLIENT_ID` (client id configured for the data source)
- `DATASOURCE_CLIENT_SECRET` (client secret configured for the data source)
- `DATASOURCE_TOKEN_EXCHANGE_AUDIENCE` (audience to request via token exchange for Feide APIs)
- `DATASOURCE_TOKEN_EXCHANGE_SCOPE` (optional; scope to request via token exchange, e.g. `readUser`)

Optional (used by `feide_login_full` and `feide_data_source_api`):

- `FEIDE_EXTENDED_USERINFO_URL` (default: `https://api.dataporten.no/userinfo/v1/userinfo`)
- `FEIDE_TOKEN_EXCHANGE_AUDIENCE` (example: `https://n.feide.no/datasources/<uuid>`)
- `FEIDE_TOKEN_EXCHANGE_SCOPE` (space-separated, depends on the datasource. Empty value will request all allowed scopes)

Optional (only used by `feide_data_source_api`):

- `FEIDE_GROUPINFO_URL` (default: `https://groups-api.dataporten.no/groups/me/groups`)



## Initial install

```bash
python -m venv .venv
source .venv/bin/activate
pip install -U pip
pip install -e ".[dev]"
```

## Example: feide_login_full (production-minded)

Note that the example does not use a third party OIDC library. In general it is recommended to use certified libraries for production code. 

This example includes:

- **JWT validation for the ID token**
- **Opaque access token handling** (treat the initial access token as opaque)
- **Feide userinfo** and **Feide extended userinfo** (directory attributes)
- **OAuth 2.0 Token Exchange (RFC 8693)** to obtain a **JWT access token** for downstream APIs
- **No refresh tokens** (not supported by Feide; re-authenticate instead)
- **Data source API call** (optional `/datasource` route)

Run (local):

```bash
python -m feide_login_full.app
```

Then open: `http://localhost:8000`

## Example: feide_login_simple (not suitable for production)

The `feide_login_simple` package is a minimal, instructional version of the auth code + PKCE flow.
It intentionally omits production safeguards and **does not verify ID token signatures**. It reuses
the shared core helpers (which are more verbose) to keep the example code as small as possible.
Use it only as a readable reference to understand the protocol steps.

Run (local):

```bash
python -m feide_login_simple.app
```

## Example: feide_data_source_api (production-minded)

This example exposes a single OAuth2-protected endpoint configured as a data source in Feide kundeportal. The endpoint is secured by a single scope. The endpoint returns:

- extended userinfo for the subject
- groupinfo for the subject (using token exchange from the data source)

Run (local):

```bash
python -m feide_data_source_api.app
```

## Run tests

```bash
pytest
```

## Core package

`feide_login_core` holds the shared (production-ready) pieces (OIDC discovery, token calls, JWT validation,
PKCE helpers, and JSON parsing). The full example imports these helpers directly, and the
simple example uses the same core to keep its code minimal while still showing the protocol steps.

## Token exchange variants

Feide uses two related token exchange patterns:

- **Data consumer (login client)**: exchanges an opaque access token for a JWT access token.
  This uses `subject_token_type=urn:ietf:params:oauth:token-type:access_token` and does not set
  `requested_token_type`.
- **Data source (API)**: exchanges a JWT access token for a new access token with Feide API scopes.
  This uses `subject_token_type=urn:ietf:params:oauth:token-type:jwt` and sets
  `requested_token_type=urn:ietf:params:oauth:token-type:access_token`.

## Production considerations (feide_login_full, feide_data_source_api)

This repository is a **reference implementation** that keeps protocol steps explicit for learning and review. It is not a drop-in production system. In production you should typically use a certified OIDC client library and add operational hardening such as:

- Structured logging and metrics
- Safer token storage (avoid keeping access tokens in client-side session cookies)
- Retry/backoff and timeouts tuned per request
- Error handling that avoids leaking details to clients
- Centralized configuration validation at startup

If you need a production integration, prefer a certified OIDC client library for your runtime and framework and keep this code as a readable, security-reviewable baseline.

## Notes on security and correctness (feide_login_full)

- **State** is used to mitigate CSRF.
- **Nonce** is used to mitigate replay and must match the ID token claim.
- The initial **access token is treated as opaque** (do not decode it as JWT).
- The **ID token is JWT** and is validated (issuer, audience, signature, expiry).
- For downstream APIs requiring JWT access tokens, use **token exchange**.

## License

MIT (see `LICENSE`).
