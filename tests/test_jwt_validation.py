from __future__ import annotations

import base64

import pytest
from jose import jwt

from feide_login_core.jwt_validation import IDTokenValidationError, validate_id_token


def _b64url(data: bytes) -> str:
    return base64.urlsafe_b64encode(data).rstrip(b"=").decode("ascii")


def test_validate_id_token_with_oct_jwk() -> None:
    secret = b"super-secret-for-tests"
    jwk = {"kty": "oct", "kid": "test-kid", "k": _b64url(secret)}
    jwks = {"keys": [jwk]}

    token = jwt.encode(
        {"sub": "user-123", "iss": "https://issuer.example", "aud": "client-1", "nonce": "n1"},
        secret,
        algorithm="HS256",
        headers={"kid": "test-kid"},
    )

    claims = validate_id_token(
        id_token=token,
        jwks=jwks,
        issuer="https://issuer.example",
        audience="client-1",
        expected_nonce="n1",
    )
    assert claims.sub == "user-123"


def test_validate_id_token_nonce_mismatch_fails() -> None:
    secret = b"super-secret-for-tests"
    jwk = {"kty": "oct", "kid": "test-kid", "k": _b64url(secret)}
    jwks = {"keys": [jwk]}

    token = jwt.encode(
        {"sub": "user-123", "iss": "https://issuer.example", "aud": "client-1", "nonce": "n1"},
        secret,
        algorithm="HS256",
        headers={"kid": "test-kid"},
    )

    with pytest.raises(IDTokenValidationError):
        _ = validate_id_token(
            id_token=token,
            jwks=jwks,
            issuer="https://issuer.example",
            audience="client-1",
            expected_nonce="wrong",
        )
