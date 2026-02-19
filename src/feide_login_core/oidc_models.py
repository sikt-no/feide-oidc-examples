"""Typed models for OIDC JSON responses."""

from __future__ import annotations

from collections.abc import Mapping
from dataclasses import dataclass


def _require_str(data: Mapping[str, object], key: str) -> str:
    value = data.get(key)
    if value is None:
        raise ValueError(f"Missing required key: {key}")
    if not isinstance(value, str):
        raise ValueError(f"Invalid str for {key}: {type(value).__name__}")
    return value


def _get_optional_str(data: Mapping[str, object], key: str) -> str | None:
    value = data.get(key)
    if value is None:
        return None
    if not isinstance(value, str):
        raise ValueError(f"Invalid str for {key}: {type(value).__name__}")
    return value


def _get_int(data: Mapping[str, object], key: str, default: int = 0) -> int:
    value = data.get(key)
    if value is None:
        return default
    if isinstance(value, bool):
        raise ValueError(f"Invalid int for {key}: bool")
    if isinstance(value, int):
        return value
    if isinstance(value, str):
        return int(value)
    raise ValueError(f"Invalid int for {key}: {type(value).__name__}")


@dataclass(frozen=True)
class DiscoveryDocument:
    authorization_endpoint: str
    token_endpoint: str
    jwks_uri: str
    userinfo_endpoint: str
    end_session_endpoint: str | None

    @staticmethod
    def from_json(data: Mapping[str, object]) -> "DiscoveryDocument":
        return DiscoveryDocument(
            authorization_endpoint=_require_str(data, "authorization_endpoint"),
            token_endpoint=_require_str(data, "token_endpoint"),
            jwks_uri=_require_str(data, "jwks_uri"),
            userinfo_endpoint=_require_str(data, "userinfo_endpoint"),
            end_session_endpoint=_get_optional_str(data, "end_session_endpoint"),
        )


@dataclass(frozen=True)
class TokenResponse:
    access_token: str
    id_token: str | None
    token_type: str
    expires_in: int
    scope: str | None

    @staticmethod
    def from_json(data: Mapping[str, object]) -> "TokenResponse":
        # Feide does not support refresh tokens; ignore if present and do not implement logic.
        return TokenResponse(
            access_token=_require_str(data, "access_token"),
            id_token=_get_optional_str(data, "id_token"),
            token_type=_get_optional_str(data, "token_type") or "Bearer",
            expires_in=_get_int(data, "expires_in", default=0),
            scope=_get_optional_str(data, "scope"),
        )


@dataclass(frozen=True)
class TokenExchangeResponse:
    access_token: str
    token_type: str
    expires_in: int
    scope: str | None

    @staticmethod
    def from_json(data: Mapping[str, object]) -> "TokenExchangeResponse":
        return TokenExchangeResponse(
            access_token=_require_str(data, "access_token"),
            token_type=_get_optional_str(data, "token_type") or "Bearer",
            expires_in=_get_int(data, "expires_in", default=0),
            scope=_get_optional_str(data, "scope"),
        )
