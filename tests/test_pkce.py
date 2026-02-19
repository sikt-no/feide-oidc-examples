from __future__ import annotations

import base64
import hashlib

from feide_login_core.pkce import generate_pkce


def _b64url_decode(s: str) -> bytes:
    # Add back padding for decoding
    pad = "=" * (-len(s) % 4)
    return base64.urlsafe_b64decode(s + pad)


def test_generate_pkce_returns_verifier_and_challenge() -> None:
    verifier, challenge = generate_pkce()
    assert verifier
    assert challenge
    assert "=" not in verifier
    assert "=" not in challenge

    expected = base64.urlsafe_b64encode(hashlib.sha256(verifier.encode("ascii")).digest()).rstrip(
        b"="
    )
    assert challenge == expected.decode("ascii")

    # verifier should be valid base64url
    _ = _b64url_decode(verifier)
