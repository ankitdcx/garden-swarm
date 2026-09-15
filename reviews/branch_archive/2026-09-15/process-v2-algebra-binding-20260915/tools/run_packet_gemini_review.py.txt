#!/usr/bin/env python3
"""Run direct Gemini blind review on the same validated GardenReviewPacket."""
from __future__ import annotations

import json
import os
from pathlib import Path
from urllib import error, request

from tools.packet_review_common import finding_prompt, load_valid_packet, validate_blind_finding

MODEL = os.getenv("GEMINI_MODEL", "gemini-3.5-flash")
BASE = "https://generativelanguage.googleapis.com/v1beta/models"
OUT = Path("agents/outbox/hourly/packet-blind-gemini.json")


def availability(packet: dict, status: str, reason: str, detail: str = "") -> int:
    OUT.parent.mkdir(parents=True, exist_ok=True)
    payload = {
        "schema": "GardenPacketGeminiAvailabilityReceipt/v1",
        "cycle_id": packet["cycle_id"],
        "packet_hash": packet["packet_hash"],
        "provider": "google-gemini-developer-api",
        "model": MODEL,
        "status": status,
        "reason": reason,
        "detail": detail[:1000],
        "peer_findings_consumed": False,
        "semantic_delta_admitted": False
    }
    OUT.write_text(json.dumps(payload, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    print(json.dumps(payload, ensure_ascii=False))
    return 0


def main() -> int:
    packet, completeness, canonical_text = load_valid_packet()
    key = os.environ.get("GEMINI_API_KEY")
    if not key:
        return availability(packet, "KEY_UNAVAILABLE", "GEMINI_API_KEY is not configured")
    role = "independent_long_context_reviewer"
    prompt = finding_prompt(packet=packet, canonical_packet_text=canonical_text, family="gemini", role=role)
    body = {
        "contents": [{"role": "user", "parts": [{"text": prompt}]}],
        "generationConfig": {"maxOutputTokens": 4200, "responseMimeType": "application/json"}
    }
    req = request.Request(f"{BASE}/{MODEL}:generateContent", method="POST", data=json.dumps(body).encode("utf-8"), headers={"Content-Type": "application/json", "x-goog-api-key": key})
    try:
        with request.urlopen(req, timeout=300) as response:
            data = json.loads(response.read().decode("utf-8"))
    except error.HTTPError as exc:
        detail = exc.read().decode("utf-8", errors="replace")
        status = "FREE_TIER_QUOTA_OR_PROVIDER_UNAVAILABLE" if exc.code in {403, 429} else "PROVIDER_ERROR"
        return availability(packet, status, f"Gemini HTTP {exc.code}; no paid fallback attempted", detail)
    except Exception as exc:
        return availability(packet, "PROVIDER_ERROR", f"{type(exc).__name__}: {exc}")
    try:
        parts = data["candidates"][0]["content"]["parts"]
        raw = json.loads("".join(x.get("text", "") for x in parts).strip())
        finding = validate_blind_finding(raw, packet=packet, family="gemini", model=MODEL, role=role)
    except Exception as exc:
        return availability(packet, "INVALID_OUTPUT", f"Gemini output failed validation: {exc}", json.dumps(data)[:1000])
    receipt = {
        "schema": "GardenPacketGeminiBlindReviewReceipt/v1",
        "cycle_id": packet["cycle_id"],
        "packet_hash": packet["packet_hash"],
        "packet_completeness_status": completeness["status"],
        "provider": "google-gemini-developer-api",
        "model": MODEL,
        "model_version": data.get("modelVersion"),
        "usage": data.get("usageMetadata") or {},
        "independent_finding": finding,
        "peer_findings_consumed": False,
        "cross_exam_performed": False,
        "semantic_delta_admitted": False,
        "status": "BLIND_REVIEW_COMPLETE"
    }
    OUT.parent.mkdir(parents=True, exist_ok=True)
    OUT.write_text(json.dumps(receipt, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    print(json.dumps({"cycle_id": packet["cycle_id"], "packet_hash": packet["packet_hash"], "status": receipt["status"], "disposition": finding.get("disposition")}, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
