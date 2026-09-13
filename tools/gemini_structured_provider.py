#!/usr/bin/env python3
from __future__ import annotations

import json
import os
from typing import Any
from urllib import error, request

MODEL = os.getenv("GEMINI_MODEL", "gemini-3.5-flash")
BASE = "https://generativelanguage.googleapis.com/v1beta/models"


def call_gemini_structured(*, prompt: str, phase: str, max_tokens: int = 4200) -> tuple[dict[str, Any] | None, dict[str, Any]]:
    key = os.environ.get("GEMINI_API_KEY")
    if not key:
        return None, {"status":"KEY_UNAVAILABLE","provider":"gemini","model":MODEL,"phase":phase}
    endpoint = f"{BASE}/{MODEL}:generateContent"
    body = {
        "contents":[{"role":"user","parts":[{"text":prompt}]}],
        "generationConfig":{
            "temperature":0.05,
            "maxOutputTokens":max_tokens,
            "responseMimeType":"application/json",
        },
    }
    req = request.Request(endpoint, method="POST", data=json.dumps(body).encode("utf-8"), headers={"Content-Type":"application/json","x-goog-api-key":key})
    try:
        with request.urlopen(req, timeout=360) as response:
            data = json.loads(response.read().decode("utf-8"))
    except error.HTTPError as exc:
        detail = exc.read().decode("utf-8", errors="replace")[:1200]
        return None, {"status":f"HTTP_{exc.code}","provider":"gemini","model":MODEL,"phase":phase,"detail":detail}
    except Exception as exc:
        return None, {"status":"PROVIDER_ERROR","provider":"gemini","model":MODEL,"phase":phase,"detail":f"{type(exc).__name__}: {exc}"}
    try:
        parts = data["candidates"][0]["content"]["parts"]
        text = "".join(str(part.get("text") or "") for part in parts).strip()
        value = json.loads(text)
        if not isinstance(value, dict):
            raise ValueError("output is not object")
    except Exception as exc:
        return None, {"status":"INVALID_OUTPUT","provider":"gemini","model":MODEL,"phase":phase,"detail":str(exc),"raw_excerpt":str(data)[:1000]}
    return value, {
        "status":"CALLED",
        "provider":"gemini",
        "model":MODEL,
        "phase":phase,
        "usage":data.get("usageMetadata") or {},
        "model_version":data.get("modelVersion"),
        "cost_policy":"Configured Gemini free-tier lane; no paid fallback/search grounding. This API response does not prove dollar cost, so Gemini is not included in OpenRouter zero-cost arithmetic.",
    }
