"""Small HTTP input boundary shared by the console broker and its tests."""
from __future__ import annotations

import json
import math
from typing import Any
from urllib.parse import urlsplit

MAX_BODY = 32768


def _unique_object(pairs):
    answer = {}
    for key, value in pairs:
        if key in answer:
            raise ValueError("duplicate JSON object key")
        answer[key] = value
    return answer


def strict_object(raw: bytes) -> dict[str, Any]:
    if len(raw) > MAX_BODY:
        raise ValueError("request body exceeds limit")
    def bad_constant(value):
        raise ValueError("nonfinite JSON number")
    try:
        value = json.loads(raw, object_pairs_hook=_unique_object,
                           parse_constant=bad_constant)
    except (RecursionError, UnicodeError, json.JSONDecodeError) as error:
        raise ValueError("invalid JSON body") from error
    if not isinstance(value, dict):
        raise ValueError("request body must be an object")
    stack = [(value, 0)]
    count = 0
    while stack:
        item, depth = stack.pop()
        count += 1
        if depth > 12 or count > 2048:
            raise ValueError("request structure exceeds limit")
        if isinstance(item, dict):
            stack.extend((v, depth + 1) for v in item.values())
        elif isinstance(item, list):
            stack.extend((v, depth + 1) for v in item)
        elif isinstance(item, float) and not math.isfinite(item):
            raise ValueError("nonfinite JSON number")
    return value


def validate_fields(value: dict, allowed: set[str], required: set[str] | None = None):
    unexpected = set(value) - allowed
    missing = (required or set()) - set(value)
    if unexpected or missing:
        raise ValueError("request fields are invalid")


def check_origin(origin: str | None, host: str, allowed_origin: str | None = None):
    if not origin:
        return
    source = urlsplit(origin)
    if source.scheme not in {"http", "https"} or source.username or source.password:
        raise ValueError("origin not permitted")
    if allowed_origin and origin.rstrip("/") == allowed_origin.rstrip("/"):
        return
    if source.netloc.lower() != host.lower():
        raise ValueError("origin not permitted")
