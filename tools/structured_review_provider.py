#!/usr/bin/env python3
from __future__ import annotations

import json
import os
import re
from typing import Any
from urllib import error, request

CHAT = "https://openrouter.ai/api/v1/chat/completions"


def _clean_json(text: str) -> dict[str, Any] | None:
    raw = (text or "").strip()
    if raw.startswith("```"):
        lines = raw.splitlines()[1:]
        if lines and lines[-1].strip() == "```":
            lines = lines[:-1]
        raw = "\n".join(lines).strip()
    if not raw:
        return None
    try:
        value = json.loads(raw)
        return value if isinstance(value, dict) else None
    except json.JSONDecodeError:
        match = re.search(r"\{.*\}", raw, re.S)
        if not match:
            return None
        try:
            value = json.loads(match.group(0))
            return value if isinstance(value, dict) else None
        except json.JSONDecodeError:
            return None


def call_openrouter_structured(*, model: dict[str, Any], prompt: str, max_tokens: int = 6400) -> tuple[dict[str, Any] | None, dict[str, Any]]:
    """Call one OpenRouter :free reviewer with fail-closed structured-output handling.

    JSON mode is requested first. If a provider rejects JSON mode with HTTP 400,
    one format-compatibility retry is allowed without changing the evidence pack.
    A retry is the same reviewer family, never an additional independent reviewer.
    """
    model_id = str(model["model"])
    if not model_id.endswith(":free"):
        raise RuntimeError(f"paid route refused: {model_id}")
    key = os.environ.get("OPENROUTER_API_KEY")
    if not key:
        return None, {"status": "KEY_UNAVAILABLE", "model": model_id, "cost": None}

    base = {
        "model": model_id,
        "messages": [{"role": "user", "content": prompt}],
        "temperature": 0.05,
        "max_tokens": max_tokens,
        "provider": {"allow_fallbacks": False},
    }

    last_detail = ""
    for mode in ("JSON_MODE", "PLAIN_JSON_FALLBACK"):
        body = dict(base)
        if mode == "JSON_MODE":
            body["response_format"] = {"type": "json_object"}
        req = request.Request(
            CHAT,
            method="POST",
            data=json.dumps(body).encode("utf-8"),
            headers={
                "Authorization": f"Bearer {key}",
                "Content-Type": "application/json",
                "HTTP-Referer": "https://github.com/ankitdcx/garden-swarm",
                "X-Title": "Garden Structured Review Quorum",
            },
        )
        try:
            with request.urlopen(req, timeout=360) as response:
                data = json.loads(response.read().decode("utf-8"))
        except error.HTTPError as exc:
            detail = exc.read().decode("utf-8", errors="replace")
            last_detail = detail[:1200]
            if exc.code == 400 and mode == "JSON_MODE":
                continue
            return None, {
                "status": f"HTTP_{exc.code}",
                "model": model_id,
                "cost": None,
                "format_mode": mode,
                "detail": last_detail,
            }
        except Exception as exc:
            return None, {
                "status": "PROVIDER_ERROR",
                "model": model_id,
                "cost": None,
                "format_mode": mode,
                "detail": f"{type(exc).__name__}: {exc}",
            }

        usage = data.get("usage") or {}
        cost = usage.get("cost")
        if cost not in (None, 0, 0.0):
            raise RuntimeError(f"non-zero inference cost refused: {model_id} cost={cost}")
        choice = (data.get("choices") or [{}])[0]
        message = choice.get("message") or {}
        content = str(message.get("content") or "")
        value = _clean_json(content)
        attempt = {
            "status": "CALLED" if value is not None else "INVALID_OUTPUT",
            "model": model_id,
            "cost": 0 if cost is None else cost,
            "usage": usage,
            "format_mode": mode,
            "finish_reason": choice.get("finish_reason"),
            "raw_output_excerpt": content[:1000],
        }
        if value is not None:
            return value, attempt
        last_detail = content[:1000]
        if mode == "JSON_MODE":
            # A second call is permitted only as format recovery for the same reviewer family.
            continue
        return None, attempt

    return None, {"status": "INVALID_OUTPUT", "model": model_id, "cost": 0, "detail": last_detail}
