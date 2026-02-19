#!/usr/bin/env sh
set -eu

if [ -f ".venv/bin/activate" ]; then
  . .venv/bin/activate
else
  echo "Missing .venv. Run: python -m venv .venv && source .venv/bin/activate && pip install -e \".[dev]\""
  exit 1
fi

# Load secrets from .env (not committed).
if [ -f ".env" ]; then
  set -a
  . .env
  set +a
fi

export FEIDE_ISSUER="${FEIDE_ISSUER:-https://auth.dataporten.no}"

if [ "${1:-}" = "--docker" ]; then
  docker build --target example -t feide-oidc-examples .
  docker run --rm -p 8000:8000 \
    -e OIDC_CLIENT_ID \
    -e OIDC_CLIENT_SECRET \
    -e OIDC_REDIRECT_URI \
    -e APP_SECRET_KEY \
    -e FEIDE_ISSUER \
    -e POST_LOGOUT_REDIRECT_URI \
    -e DATASOURCE_API_URL \
    -e FEIDE_TOKEN_EXCHANGE_AUDIENCE \
    -e FEIDE_TOKEN_EXCHANGE_SCOPE \
    feide-oidc-examples
else
  python -m feide_login_full.app
fi
