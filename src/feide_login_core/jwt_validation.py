"""JWT validation for Feide ID tokens.

Feide ID tokens are JWTs. Access tokens from the initial login flow are opaque
and must not be decoded as JWTs.
"""

from __future__ import annotations

from collections.abc import Mapping
from dataclasses import dataclass
from typing import cast

from jose import jwt

from feide_login_core.json_utils import require_json_object


class IDTokenValidationError(RuntimeError):
    pass


class AccessTokenValidationError(RuntimeError):
    pass


@dataclass(frozen=True)
class IDTokenClaims:
    raw: Mapping[str, object]

    @property
    def sub(self) -> str:
        return str(self.raw.get("sub", ""))

    @property
    def nonce(self) -> str | None:
        val = self.raw.get("nonce")
        return str(val) if val is not None else None


def _select_jwk(jwks: Mapping[str, object], kid: str) -> Mapping[str, object]:
    keys = jwks.get("keys")
    if not isinstance(keys, list):
        raise IDTokenValidationError("JWKS 'keys' is not a list")

    keys_list = cast(list[object], keys)
    for key in keys_list:
        if isinstance(key, dict):
            key_dict = cast(Mapping[str, object], key)
            if key_dict.get("kid") == kid:
                return key_dict

    raise IDTokenValidationError(f"No matching JWK for kid={kid}")


def validate_id_token(
    *,
    id_token: str,
    jwks: Mapping[str, object],
    issuer: str,
    audience: str,
    expected_nonce: str,
) -> IDTokenClaims:
    """Validate and decode an ID token.

    - verifies signature (JWKS)
    - checks issuer, audience
    - checks expiry
    - checks nonce
    """
    try:
        header = jwt.get_unverified_header(id_token)
    except Exception as exc:
        raise IDTokenValidationError("Invalid JWT header") from exc

    header_obj = require_json_object(cast(object, header), error="JWT header is not a JSON object")
    kid_val = header_obj.get("kid")
    if not isinstance(kid_val, str) or not kid_val:
        raise IDTokenValidationError("ID token missing 'kid' header")

    jwk = _select_jwk(jwks, kid_val)

    try:
        claims = jwt.decode(
            id_token,
            jwk,
            algorithms=[str(header_obj.get("alg", "RS256"))],
            issuer=issuer,
            audience=audience,
            options={
                "verify_at_hash": False,
            },
        )
    except Exception as exc:
        raise IDTokenValidationError("ID token validation failed") from exc

    claims = require_json_object(
        cast(object, claims), error="ID token claims are not a JSON object"
    )
    nonce = claims.get("nonce")
    if nonce != expected_nonce:
        raise IDTokenValidationError("Nonce mismatch")

    return IDTokenClaims(raw=claims)


def validate_access_token(
    *,
    token: str,
    jwks: Mapping[str, object],
    issuer: str,
    audience: str,
) -> Mapping[str, object]:
    """Validate and decode a JWT access token."""
    try:
        header = jwt.get_unverified_header(token)
    except Exception as exc:
        raise AccessTokenValidationError("Invalid JWT header") from exc

    header_obj = require_json_object(cast(object, header), error="JWT header is not a JSON object")
    kid_val = header_obj.get("kid")
    if not isinstance(kid_val, str) or not kid_val:
        raise AccessTokenValidationError("Access token missing 'kid' header")

    jwk = _select_jwk(jwks, kid_val)

    try:
        claims = jwt.decode(
            token,
            jwk,
            algorithms=[str(header_obj.get("alg", "RS256"))],
            issuer=issuer,
            audience=audience,
            options={
                "verify_at_hash": False,
            },
        )
    except Exception as exc:
        raise AccessTokenValidationError("Access token validation failed") from exc

    return require_json_object(
        cast(object, claims), error="Access token claims are not a JSON object"
    )
