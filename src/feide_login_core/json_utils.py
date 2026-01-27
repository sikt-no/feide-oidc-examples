"""Small helpers for validating JSON payload shapes."""

from __future__ import annotations

from collections.abc import Mapping
from typing import cast

from requests import Response


def require_json_object(value: object, *, error: str) -> Mapping[str, object]:
    if not isinstance(value, dict):
        raise ValueError(error)
    return cast(Mapping[str, object], value)


def require_json_array(value: object, *, error: str) -> list[object]:
    if not isinstance(value, list):
        raise ValueError(error)
    return cast(list[object], value)


def json_object_from_response(response: Response, *, error: str) -> Mapping[str, object]:
    data = cast(object, response.json())
    if not isinstance(data, dict):
        # Keep JSON shape errors explicit for callers.
        raise ValueError(error)
    return cast(Mapping[str, object], data)
