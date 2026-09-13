#!/usr/bin/env python3
"""Independent Gemini free-tier Garden reviewer.

Uses the Gemini Developer API directly. No search grounding, no paid fallback,
no repository write authority. Output is proposal-only evidence for later
whole-source cross-reference.
"""
from __future__ import annotations

import hashlib
import json
import os
import re
import time
from pathlib import Path
from urllib import error, request

MODEL = os.getenv("GEMINI_MODEL", "gemini-3.5-flash")
BASE = "https://generativelanguage.googleapis.com/v1beta/models"
OUT = Path("agents/outbox/hourly/gemini-review.json")
FILES = [
    "Garden_User_v15.5_FULL_2026-09-12.txt",
    "Garden_System_v15.5_FULL_2026-09-12.txt",
    "Garden_Technical_v15.5_FULL_2026-09-12.txt",
    "Garden_Annexure_v15.5_FULL_2026-09-12.txt",
    "Garden_Theories_v15.5_FULL_2026-09-12.txt",
]
PACKAGES = [
    ("authority-gate", ["prototype/actiongate.py", "prototype/authority.py", "prototype/tests/test_actiongate.py", "tests/adversarial/test_known_attacks.py"]),
    ("design-epoch", ["prototype/design_epoch.py", "prototype/tests/test_design_epoch.py", "tests/adversarial/test_known_attacks.py"]),
    ("receipts", ["prototype/tokens.py", "prototype/tests/test_tokens.py", "ATTACK_SURFACE.md"]),
    ("discovery-mcp", ["server/app.py", "server/mcp_service.py", "server/tests/test_mcp.py", "DISCOVERY.json", "SKILLS.json"]),
    ("swarm", ["swarm/orchestrator.py", "swarm/synthesize.py", "swarm/roles-free.json", "swarm/tests/test_synthesize.py"]),
    ("evaluation-release", ["AGENTS.md", "ATTACK_SURFACE.md", "EVALUATION_LOG.md", "EVALUATE_IN_10_MINUTES.md", "scripts/verify_public_release.py"]),
]

SCHEMA = {
    "type": "object",
    "properties": {
        "status": {"type": "string", "enum": ["NO_CHANGE", "PROPOSED", "BLOCKER", "NEEDS_CROSS_REFERENCE"]},
        "claim": {"type": "string"},
        "evidence_or_failure": {"type": "string"},
        "severity": {"type": "string", "enum": ["INFO", "LOW", "MEDIUM", "HIGH", "CRITICAL"]},
        "affected_invariant": {"type": "string"},
        "proposed_fix": {"type": "string"},
        "test": {"type": "string"},
        "uncertainty": {"type": "string"},
        "what_would_overturn": {"type": "string"},
        "search_trace": {
            "type": "array",
            "items": {
                "type": "object",
                "properties": {
                    "source": {"type": "string"},
                    "query_or_scope": {"type": "string"},
                    "coverage": {"type": "string"},
                },
                "required": ["source", "query_or_scope", "coverage"],
            },
            "minItems": 1,
        },
    },
    "required": ["status", "claim", "evidence_or_failure", "severity", "affected_invariant", "proposed_fix", "test", "uncertainty", "what_would_overturn", "search_trace"],
}


def chunks(text: str, size: int = 18000) -> list[str]:
    parts = []
    for start in range(0, len(text), size):
        parts.append(text[start:start + size])
    return parts or [""]


def current_slot() -> int:
    return int(time.time() // 3600)


def build_design(root: Path, slot: int) -> tuple[str, str, list[dict]]:
    items = []
    for filename in FILES:
        raw = (root / filename).read_bytes()
        sha = hashlib.sha256(raw).hexdigest()
        sections = chunks(raw.decode("utf-8"))
        for i, text in enumerate(sections, 1):
            items.append((filename, sha, i, len(sections), text))
    filename, sha, index, total, text = items[slot % len(items)]
    task = f"GEMINI-DESIGN:{filename}:chunk-{index:03d}:{slot}"
    trace = [{"source": filename, "query_or_scope": f"chunk {index}/{total}; sha256={sha}", "coverage": "BOUNDED"}]
    prompt = f"""Independently falsify or strengthen this bounded Garden v15.5 canonical source. Distinguish design defect, implementation gap, missing evidence, optional enhancement, and coverage limitation. Never claim a mechanism is absent from Garden merely because it is absent from this chunk; use NEEDS_CROSS_REFERENCE. Return only the requested structured JSON. Task: {task}.\n\n--- BEGIN SOURCE ---\n{text}\n--- END SOURCE ---"""
    return task, prompt, trace


def build_repo(root: Path, slot: int) -> tuple[str, str, list[dict]]:
    package, files = PACKAGES[slot % len(PACKAGES)]
    sections, trace = [], []
    for rel in files:
        path = root / rel
        if not path.is_file():
            continue
        text = path.read_text(encoding="utf-8")
        coverage = "FULL"
        if len(text) > 18000:
            text, coverage = text[:18000] + "\n...[bounded]", "PARTIAL"
        sections.append(f"\n--- {rel} ---\n{text}")
        trace.append({"source": rel, "query_or_scope": "supplied repository file content", "coverage": coverage})
    task = f"GEMINI-REPO:{package}:{slot}"
    prompt = f"""Independently attack this bounded executable Garden package. Distinguish implementation defect, specification gap, missing evidence, and coverage limitation. Do not infer anything about files not supplied. Return only the requested structured JSON. Task: {task}.\n{''.join(sections)}"""
    return task, prompt, trace


def write_availability(slot: int, lane: str, status: str, reason: str, detail: str = "") -> int:
    OUT.parent.mkdir(parents=True, exist_ok=True)
    payload = {
        "schema": "GardenGeminiAvailabilityReceipt/v1",
        "provider": "google-gemini-developer-api",
        "model": MODEL,
        "hour_slot": slot,
        "lane": lane,
        "status": status,
        "reason": reason,
        "detail": detail[:1000],
        "admission_status": "NO_MODEL_FINDING",
        "cost_policy": "Free-tier project required; no search grounding and no paid fallback are used by this workflow.",
    }
    OUT.write_text(json.dumps(payload, indent=2) + "\n", encoding="utf-8")
    print(json.dumps(payload))
    return 0


def main() -> int:
    key = os.environ.get("GEMINI_API_KEY")
    slot = current_slot()
    # Opposite lane from the OpenRouter hourly reviewer: together they cover both design and repo.
    lane = "repo" if slot % 2 == 0 else "design"
    if not key:
        return write_availability(slot, lane, "KEY_UNAVAILABLE", "GEMINI_API_KEY is not configured")

    root = Path(".").resolve()
    task, prompt, supplied_trace = build_repo(root, slot) if lane == "repo" else build_design(root, slot)
    endpoint = f"{BASE}/{MODEL}:generateContent"
    body = {
        "contents": [{"role": "user", "parts": [{"text": prompt}]}],
        "generationConfig": {
            "temperature": 0.15,
            "maxOutputTokens": 3000,
            "responseMimeType": "application/json",
            "responseJsonSchema": SCHEMA,
        },
    }
    req = request.Request(
        endpoint,
        method="POST",
        data=json.dumps(body).encode("utf-8"),
        headers={"Content-Type": "application/json", "x-goog-api-key": key},
    )
    try:
        with request.urlopen(req, timeout=300) as response:
            data = json.loads(response.read().decode("utf-8"))
    except error.HTTPError as exc:
        detail = exc.read().decode("utf-8", errors="replace")
        status = "FREE_TIER_QUOTA_OR_PROVIDER_UNAVAILABLE" if exc.code in {429, 403} else "PROVIDER_ERROR"
        return write_availability(slot, lane, status, f"Gemini HTTP {exc.code}; no retry and no paid fallback", detail)
    except Exception as exc:
        return write_availability(slot, lane, "PROVIDER_ERROR", f"{type(exc).__name__}: {exc}")

    try:
        parts = data["candidates"][0]["content"]["parts"]
        text = "".join(part.get("text", "") for part in parts).strip()
        handoff = json.loads(text)
        if not isinstance(handoff, dict) or not handoff.get("search_trace"):
            raise ValueError("missing structured search_trace")
    except Exception as exc:
        return write_availability(slot, lane, "INVALID_OUTPUT", f"Gemini response was not usable structured output: {exc}", json.dumps(data)[:1000])

    # Preserve model trace but ensure the receipt records the actual supplied coverage too.
    handoff.update({
        "schema": "GardenAgentHandoff/v1",
        "agent": MODEL,
        "agent_family": "gemini",
        "role": "independent_long_context_reviewer",
        "task_id": task,
        "supplied_search_trace": supplied_trace,
    })
    usage = data.get("usageMetadata") or {}
    receipt = {
        "schema": "GardenGeminiFreeReviewReceipt/v1",
        "provider": "google-gemini-developer-api",
        "model": MODEL,
        "model_version": data.get("modelVersion"),
        "hour_slot": slot,
        "lane": lane,
        "usage": usage,
        "handoff": handoff,
        "admission_status": "PROPOSALS_ONLY_NEEDS_CHATGPT_AND_WHOLE_SOURCE_CROSS_REFERENCE",
        "cost_policy": "Expected zero inference charge only while the associated Google AI Studio project remains on Gemini Free Tier. Workflow uses no search grounding and no paid fallback.",
    }
    OUT.parent.mkdir(parents=True, exist_ok=True)
    OUT.write_text(json.dumps(receipt, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    print(json.dumps({"model": MODEL, "lane": lane, "status": handoff.get("status"), "usage": usage}, ensure_ascii=False))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
