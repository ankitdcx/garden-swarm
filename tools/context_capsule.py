from __future__ import annotations

import hashlib
import json
from typing import Any

CAPSULE_SCHEMA = "GardenArchitectureContextCapsule/v1"
LEVELS = ("L0_CAPSULE", "L1_DEPENDENCY_EXPANDED", "L2_CROSS_LAYER_EXPANDED", "L3_AFFECTED_DOCUMENTS_FULL", "L4_FULL_GARDEN")
CONTEXT_VERDICTS = ("SUFFICIENT", "EXPAND_REQUIRED", "FULL_CONTEXT_REQUIRED")


def canonical_json(value: Any) -> str:
    return json.dumps(value, sort_keys=True, separators=(",", ":"), ensure_ascii=False, allow_nan=False)


def sha256_value(value: Any) -> str:
    return hashlib.sha256(canonical_json(value).encode("utf-8")).hexdigest()


def _hex64(value: Any, field: str) -> str:
    text = str(value or "").strip().lower()
    if len(text) != 64 or any(c not in "0123456789abcdef" for c in text):
        raise ValueError(f"{field} must be lowercase sha256 hex")
    return text


def validate_capsule(value: dict[str, Any], *, target_id: str, trace: dict[str, Any]) -> dict[str, Any]:
    if value.get("schema") != CAPSULE_SCHEMA:
        raise ValueError("unsupported Garden architecture context capsule schema")
    if value.get("public_only") is not True:
        raise ValueError("OpenRouter context capsule must remain public-only")
    if value.get("target_id") != target_id:
        raise ValueError("context capsule target mismatch")
    level = str(value.get("context_expansion_level") or "")
    if level not in LEVELS:
        raise ValueError("invalid context expansion level")
    source_identity = value.get("source_identity") or {}
    if source_identity.get("target_source") != trace.get("source"):
        raise ValueError("context capsule target source mismatch")
    if source_identity.get("target_source_sha256") != trace.get("source_sha256"):
        raise ValueError("context capsule target source hash mismatch")
    _hex64(source_identity.get("canonical_source_root_sha256"), "canonical_source_root_sha256")
    candidate_root = source_identity.get("candidate_source_root_sha256")
    if candidate_root not in (None, ""):
        _hex64(candidate_root, "candidate_source_root_sha256")
    for field in (
        "whole_garden_orientation",
        "dependency_closure",
        "cross_cutting_obligations",
        "relevant_history",
        "omission_and_uncertainty_ledger",
    ):
        payload = value.get(field)
        if payload in (None, "", [], {}):
            raise ValueError(f"context capsule missing non-empty {field}")
    encoded = canonical_json(value)
    if len(encoded) > 48000:
        raise ValueError("context capsule exceeds bounded size; use a higher expansion lane/full-context path")
    return value


def require_directive_capsule(directive: dict[str, Any], *, target_id: str, trace: dict[str, Any]) -> tuple[dict[str, Any], str]:
    capsule = validate_capsule(directive.get("architecture_context_capsule") or {}, target_id=target_id, trace=trace)
    expected = _hex64(directive.get("architecture_context_capsule_sha256"), "architecture_context_capsule_sha256")
    actual = sha256_value(capsule)
    if actual != expected:
        raise ValueError("architecture context capsule hash mismatch")
    return capsule, actual


def validate_context_verdict(value: dict[str, Any]) -> dict[str, Any]:
    verdict = str(value.get("context_sufficiency") or "")
    if verdict not in CONTEXT_VERDICTS:
        raise ValueError("review missing valid context_sufficiency")
    refs = value.get("requested_dependency_or_source_refs")
    if not isinstance(refs, list):
        raise ValueError("requested_dependency_or_source_refs must be a list")
    reason = str(value.get("missing_context_reason") or "")
    if verdict == "SUFFICIENT" and (reason.strip() or refs or value.get("requested_context")):
        raise ValueError("SUFFICIENT cannot accompany missing context or expansion requests")
    if verdict != "SUFFICIENT" and not reason.strip():
        raise ValueError("insufficient-context review must explain the missing context")
    if verdict != "SUFFICIENT" and not refs:
        raise ValueError("insufficient-context review must request dependency/source refs")
    return value
