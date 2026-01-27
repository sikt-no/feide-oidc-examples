from __future__ import annotations

import pytest

from feide_login_core.oidc_models import DiscoveryDocument, TokenResponse


def test_discovery_document_requires_fields() -> None:
    with pytest.raises(ValueError):
        _ = DiscoveryDocument.from_json({"token_endpoint": "https://issuer/token"})


def test_token_response_requires_access_token() -> None:
    with pytest.raises(ValueError):
        _ = TokenResponse.from_json({"token_type": "Bearer"})


def test_token_response_rejects_non_string_id_token() -> None:
    with pytest.raises(ValueError):
        _ = TokenResponse.from_json({"access_token": "token", "id_token": 123})
