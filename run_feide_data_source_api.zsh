#!/usr/bin/env zsh
set -euo pipefail

if [[ -f ".venv/bin/activate" ]]; then
  source .venv/bin/activate
else
  echo "Missing .venv. Run: python -m venv .venv && source .venv/bin/activate && pip install -e \".[dev]\""
  exit 1
fi

# Load secrets from .env (not committed).
if [[ -f ".env" ]]; then
  set -a
  source .env
  set +a
fi

export FEIDE_ISSUER="${FEIDE_ISSUER:-https://auth.dataporten.no}"
export DATASOURCE_TOKEN_EXCHANGE_AUDIENCE="${DATASOURCE_TOKEN_EXCHANGE_AUDIENCE:-https://auth.dataporten.no}"

if [[ "${1:-}" == "--docker" ]]; then
  docker build --target datasource -t feide-oidc-datasource .
  docker run --rm -p 8001:8001 \
    -e DATASOURCE_CLIENT_ID \
    -e DATASOURCE_CLIENT_SECRET \
    -e FEIDE_ISSUER \
    -e DATASOURCE_AUDIENCE \
    -e DATASOURCE_REQUIRED_SCOPE \
    -e DATASOURCE_TOKEN_EXCHANGE_AUDIENCE \
    -e DATASOURCE_TOKEN_EXCHANGE_SCOPE \
    feide-oidc-datasource
else
  python -m feide_data_source_api.app
fi
