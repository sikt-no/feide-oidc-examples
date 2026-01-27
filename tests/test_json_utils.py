from __future__ import annotations

from typing import cast

import pytest
from requests import Response

from feide_login_core.json_utils import json_object_from_response, require_json_object


class _FakeResponse:
    _payload: object

    def __init__(self, payload: object) -> None:
        self._payload = payload

    def json(self) -> object:
        return self._payload


def test_require_json_object_rejects_non_object() -> None:
    with pytest.raises(ValueError):
        _ = require_json_object(["not", "a", "dict"], error="nope")


def test_json_object_from_response_rejects_non_object() -> None:
    response = _FakeResponse(["not", "a", "dict"])
    with pytest.raises(ValueError):
        _ = json_object_from_response(cast(Response, cast(object, response)), error="nope")
