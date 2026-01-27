"""PKCE helper (RFC 7636)."""

from __future__ import annotations

import base64
import hashlib
import secrets
from typing import Final

_VERIFIER_BYTES: Final[int] = 32


def _b64url(data: bytes) -> str:
    return base64.urlsafe_b64encode(data).rstrip(b"=").decode("ascii")


def generate_pkce() -> tuple[str, str]:
    """Return (code_verifier, code_challenge) using S256."""
    verifier = _b64url(secrets.token_bytes(_VERIFIER_BYTES))
    challenge = _b64url(hashlib.sha256(verifier.encode("ascii")).digest())
    return verifier, challenge
